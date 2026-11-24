"""Healer classifier and CI check: gaps found in review (rules 2 and 3). Pure: no app, no browser, no git."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import check_healer_log as check
from scripts import healer_log as hl

pytestmark = pytest.mark.framework

T = "tests/journeys/sales/test_creation.py"


def hunk(path: str, start: int, rows: list[str]) -> str:
    old = sum(1 for r in rows if r[0] != "+")
    new = sum(1 for r in rows if r[0] != "-")
    return (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        f"@@ -{start},{old} +{start},{new} @@\n" + "\n".join(rows) + "\n"
    )


WRAPPED_EXPECT = hunk(
    T,
    40,
    [
        "     total = page.locator('#total')",
        "     expect(total).to_have_text(",
        '-        "1,120.00"',
        '+        "1,000.00"',
        "     )",
    ],
)


# --- R003: wrapped expect / assert / constant ----------------------------------------------------


def test_wrapped_expect_whose_expected_value_changes_is_an_assertion() -> None:
    result = hl.classify_diff(WRAPPED_EXPECT)
    assert result.assertion
    assert result.findings[0].line == 42


def test_wrapped_expect_whose_subject_line_changes_is_not_an_assertion() -> None:
    diff = hunk(
        T,
        40,
        [
            "-    expect(page.get_by_role('a')).to_have_text(",
            "+    expect(page.get_by_test_id('a')).to_have_text(",
            '         "1,120.00",',
            "         timeout=5000,",
            "     )",
        ],
    )
    assert not hl.classify_diff(diff).assertion


def test_wrapped_timeout_only_change_is_not_an_assertion() -> None:
    diff = hunk(
        T,
        40,
        [
            "     expect(total).to_have_text(",
            '         "1,120.00",',
            "-        timeout=5000,",
            "+        timeout=10000,",
            "     )",
        ],
    )
    assert not hl.classify_diff(diff).assertion


def test_wrapped_assert_and_expected_constant_changes_are_assertions() -> None:
    wrapped_assert = hunk(T, 10, ["     assert total == (", "-        118", "+        119", "     )"])
    wrapped_const = hunk(
        T, 10, ["     expected_total = Decimal(", '-        "118.00"', '+        "119.00"', "     )"]
    )
    assert hl.classify_diff(wrapped_assert).assertion
    assert hl.classify_diff(wrapped_const).assertion


def test_change_inside_a_statement_opened_outside_the_hunk_fails_closed() -> None:
    diff = hunk(T, 50, ['-        "1,120.00",', '+        "1,000.00",', "     )", "     x = 1"])
    result = hl.classify_diff(diff)
    assert result.assertion
    assert "fail closed" in (result.reason or "")


def test_changed_item_deep_in_a_list_whose_brackets_are_outside_the_hunk_fails_closed() -> None:
    rows = ['     "b",', '     "c",', '     "d",', '-    "1,120.00",', '+    "1,000.00",']
    diff = hunk(T, 24, [*rows, '     "e",', '     "f",', '     "g",'])
    result = hl.classify_diff(diff)
    assert result.assertion
    assert "fail closed" in (result.reason or "")


def test_wrapped_page_object_wait_change_with_opener_outside_the_hunk_is_not_an_assertion() -> None:
    rows = [
        "         first,",
        "         second,",
        "         third,",
        "-        timeout=5000,",
        "+        timeout=9000,",
    ]
    diff = hunk("pages/x.py", 30, [*rows, "     )", "     return self"])
    assert not hl.classify_diff(diff).assertion


def test_wrapped_page_object_locator_change_with_opener_outside_the_hunk_is_not_an_assertion() -> None:
    rows = [
        "         first,",
        "-        name='Save',",
        "+        name='Save invoice',",
        "         exact=True,",
    ]
    diff = hunk("pages/x.py", 30, [*rows, "     )"])
    assert not hl.classify_diff(diff).assertion


def test_page_object_change_inside_a_visibly_open_expect_fails_closed() -> None:
    rows = ["     expect(self.total).to_have_text(", '-        "1,120.00",', '+        "1,000.00",']
    diff = hunk("pages/x.py", 30, [*rows, '         "x",', '         "y",', '         "z",'])
    assert hl.classify_diff(diff).assertion


def test_escaped_quote_in_a_string_does_not_open_a_bracket() -> None:
    rows = [
        '     a = "say \\"(hi\\""',
        "-    page.get_by_role('a').click()",
        "+    page.get_by_test_id('a').click()",
    ]
    diff = hunk(T, 30, rows)
    assert not hl.classify_diff(diff).assertion


# --- R037: approvals must be new, by a reviewer, and match the change's content ----------------------


def _log(*rows: dict[str, Any]) -> bytes:
    return ("\n".join(json.dumps(r) for r in rows) + "\n").encode()


def _change(cid: str, diff: str, **extra: Any) -> dict[str, Any]:
    return {
        "v": 1, "type": "change", "id": cid, "ts": "2026-10-06T10:00:00Z", "test": "t", "nodeid": "n",
        "verdict": "assertion", "summary": "s", "files": [T], "diff": diff, "applied": True,
        "agent": "test-healer", **extra,
    }  # fmt: skip


def _review(cid: str, role: str = "reviewer", by: str = "Sanjeev") -> dict[str, Any]:
    return {"v": 1, "type": "review", "change_id": cid, "ts": "2026-10-06T11:00:00Z",
            "decision": "approved", "by": by, "role": role, "note": ""}  # fmt: skip


A_TO_B = hunk(T, 42, ['-    expect(t).to_have_text("A")', '+    expect(t).to_have_text("B")'])
A_TO_C = hunk(T, 42, ['-    expect(t).to_have_text("A")', '+    expect(t).to_have_text("C")'])


def test_approval_for_one_value_does_not_cover_a_different_value_on_the_same_lines() -> None:
    log = _log(_change("HC-001", A_TO_B), _review("HC-001"))
    assert check.run_checks(check.CheckInput(diff=A_TO_B, log=log)) == []
    assert check.run_checks(check.CheckInput(diff=A_TO_C, log=log))


def test_approval_already_on_the_base_branch_does_not_cover_a_new_change() -> None:
    old = _log(_change("HC-001", A_TO_B), _review("HC-001"))
    assert check.run_checks(check.CheckInput(diff=A_TO_B, log=old, base_log=old))


@pytest.mark.parametrize("role", ["qa", "x", "viewer"])
def test_approval_by_a_non_reviewer_role_does_not_cover(role: str) -> None:
    log = _log(_change("HC-001", A_TO_B), _review("HC-001", role=role))
    assert check.run_checks(check.CheckInput(diff=A_TO_B, log=log))


def test_approval_by_the_change_author_does_not_cover() -> None:
    log = _log(_change("HC-001", A_TO_B, author="Sanjeev"), _review("HC-001", by="Sanjeev"))
    assert check.run_checks(check.CheckInput(diff=A_TO_B, log=log))
    agent = _log(_change("HC-002", A_TO_B), _review("HC-002", by="test-healer"))
    assert check.run_checks(check.CheckInput(diff=A_TO_B, log=agent))


def test_removed_constant_needs_an_approval_of_that_removal() -> None:
    removed = hunk(T, 10, ["-    expected_tax = 18", "     x = 1"])
    other = hunk(T, 10, ["-    expected_total = 100", "     x = 1"])
    log = _log(_change("HC-001", other), _review("HC-001"))
    assert check.run_checks(check.CheckInput(diff=removed, log=log))


# --- R038: git failures fail the check -----------------------------------------------------------


def _proc(code: int, out: bytes = b"", err: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["git"], code, out, err)


def test_git_failure_raises_and_main_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _proc(128, err=b"bad revision"))
    with pytest.raises(check.GitError, match="bad revision"):
        check.gather("origin/main", tmp_path / "log.jsonl")
    assert check.main(["--base", "origin/main", "--log", str(tmp_path / "log.jsonl")]) == 2


def test_missing_base_log_is_empty_but_other_failures_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake(argv: list[str], **_: Any) -> subprocess.CompletedProcess[bytes]:
        if argv[1] == "cat-file":
            return _proc(1)  # base exists (diff worked) but has no healer log
        return _proc(0, b"")

    monkeypatch.setattr(subprocess, "run", fake)
    assert check.gather("origin/main", tmp_path / "log.jsonl").base_log == b""


# --- R039: imperative skips, other folders and bare `mark` ---------------------------------------


@pytest.mark.parametrize(
    ("path", "line"),
    [
        (T, '    pytest.skip("flaky, skip for now")'),
        (T, '    pytest.xfail("known bug")'),
        (T, '    pytest.importorskip("numpy")'),
        (T, '@mark.skip(reason="later")'),
        ("test_data/outstanding_params.py", '    marks = pytest.mark.xfail(reason="OA-065 known")'),
        ("pages/x.py", '        pytest.skip("not ready")'),
        ("fixtures/x.py", '    pytest.skip("no data")'),
    ],
)
def test_skip_without_agreed_defect_is_flagged_anywhere(path: str, line: str) -> None:
    diff = hunk(path, 1, [f"+{line}"])
    assert check.check_markers(check.CheckInput(diff=diff, log=b""))


def test_wrapped_marker_reason_on_the_next_line_is_read() -> None:
    defects = "| D-001 | J04 | s | e | a | x | major | agreed |\n"
    diff = hunk(T, 1, ["+@pytest.mark.skip(", '+    reason="D-001 zero qty saves",', "+)"])
    assert check.check_markers(check.CheckInput(diff=diff, log=b"", defects=defects)) == []
    bad = hunk(T, 1, ["+@pytest.mark.skip(", '+    reason="flaky",', "+)"])
    assert check.check_markers(check.CheckInput(diff=bad, log=b"", defects=defects))
