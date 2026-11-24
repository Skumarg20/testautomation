"""Healer log helper and CI check (F08 R7, R19, R28, R32, R33). Pure: no app, no browser, no git."""

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from scripts import check_healer_log as check
from scripts import healer_log as hl

pytestmark = pytest.mark.framework

TEXT_EDIT = (
    '-    expect(toast).to_have_text("Quantity must be positive")\n'
    '+    expect(toast).to_have_text("Quantity must be greater than zero")'
)


def make_diff(path: str, removed: list[str], added: list[str]) -> str:
    body = "\n".join([f"-{r}" for r in removed] + [f"+{a}" for a in added])
    return (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        f"@@ -10,{len(removed)} +10,{len(added)} @@\n{body}\n"
    )


T = "tests/journeys/sales/test_creation.py"

ASSERTION_CASES = [
    ("matcher argument", ['    expect(t).to_have_text("A")'], ['    expect(t).to_have_text("B")']),
    ("deleted expect", ["    expect(t).to_be_visible()", "    x = 1"], ["    x = 1"]),
    ("weakened matcher", ['    expect(t).to_have_text("A")'], ['    expect(t).to_contain_text("A")']),
    ("assert operand", ["    assert total == 118"], ["    assert total == 119"]),
    ("assert deleted", ["    assert total == 118"], []),
    ("approx", ["    assert x == pytest.approx(1.5)"], ["    assert x == pytest.approx(1.6)"]),
    ("count argument", ["    expect(rows).to_have_count(3)"], ["    expect(rows).to_have_count(4)"]),
    ("matcher and subject", ["    expect(a).to_be_visible()"], ["    expect(b).to_be_hidden()"]),
    ("expected constant", ["    expected_total = 100"], ["    expected_total = 101"]),
    ("expected removed", ["    expected_tax = 18"], []),
    ("dict expected", ['        "expected": 5,'], ['        "expected": 6,']),
    (
        "nested parens",
        ['    expect(p.locator("a(b)")).to_have_text("x")'],
        ['    expect(p.locator("a(b)")).to_have_text("y")'],
    ),
]

NOT_ASSERTION_CASES = [
    (
        "locator subject only",
        ['    expect(page.get_by_role("a")).to_be_visible()'],
        ['    expect(page.get_by_test_id("a")).to_be_visible()'],
    ),
    ("timeout only", ["    expect(t).to_be_visible()"], ["    expect(t).to_be_visible(timeout=10000)"]),
    ("soft only", ['    expect(t).to_have_text("A")'], ['    expect(t).to_have_text("A", timeout=5000)']),
    ("wait added", ["    x = 1"], ["    x = 1", '    page.wait_for_response("**/api/x")']),
    ("assert added", [], ["    assert total == 118"]),
    ("comment edited", ["    # old note"], ["    # new note"]),
    (
        "moved expect",
        ["    expect(t).to_be_visible()", "    y = 2"],
        ["    y = 2", "    expect(t).to_be_visible()"],
    ),
    ("quote style", ["    expect(t).to_have_text('A')"], ['    expect(t).to_have_text("A")']),
    ("plain code", ["    x = 1"], ["    x = 2"]),
]


@pytest.mark.parametrize(("name", "removed", "added"), ASSERTION_CASES, ids=[c[0] for c in ASSERTION_CASES])
def test_f08_r7_diffs_that_change_an_expectation_are_assertions(
    name: str, removed: list[str], added: list[str]
) -> None:
    result = hl.classify_diff(make_diff(T, removed, added))
    assert result.assertion, name
    assert result.findings[0].file == T
    assert result.reason


@pytest.mark.parametrize(
    ("name", "removed", "added"), NOT_ASSERTION_CASES, ids=[c[0] for c in NOT_ASSERTION_CASES]
)
def test_f08_r7_timing_locator_and_neutral_diffs_are_not_assertions(
    name: str, removed: list[str], added: list[str]
) -> None:
    assert not hl.classify_diff(make_diff(T, removed, added)).assertion, name


def test_f08_r7_headerless_sample_diff_is_detected_and_reason_names_a_line() -> None:
    result = hl.classify_diff(TEXT_EDIT)
    assert result.assertion
    assert "matcher argument changed" in (result.reason or "")


def test_f08_r7_new_file_and_out_of_scope_files_are_not_classified() -> None:
    new_file = (
        "diff --git a/tests/new.py b/tests/new.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/new.py\n"
        '@@ -0,0 +1,2 @@\n+    expect(t).to_have_text("A")\n+    assert x == 1\n'
    )
    assert not hl.classify_diff(new_file).assertion
    assert not hl.classify_diff(
        make_diff("scripts/x.py", ["    assert a == 1"], ["    assert a == 2"])
    ).assertion


def test_f08_r7_test_data_constant_and_rounding_helper_changes_are_assertions() -> None:
    const = make_diff("test_data/totals.py", ["TOTAL_TAX = 18"], ["TOTAL_TAX = 19"])
    helper = make_diff("test_data/gst_calc.py", ["    return round(v, 2)"], ["    return round(v, 1)"])
    harmless = make_diff("test_data/factory.py", ["    name = 'a'"], ["    name = 'b'"])
    assert hl.classify_diff(const).assertion
    assert hl.classify_diff(helper).assertion
    assert not hl.classify_diff(harmless).assertion


def test_f08_r7_parametrize_expected_row_change_is_an_assertion() -> None:
    diff = (
        f"--- a/{T}\n+++ b/{T}\n@@ -5,5 +5,5 @@\n"
        ' @pytest.mark.parametrize("qty,expected", [\n-    (1, 100),\n+    (1, 101),\n     (2, 200),\n ])\n'
    )
    assert hl.classify_diff(diff).assertion


def test_f08_r7_raise_never_lowers() -> None:
    assert hl.raise_verdict("locator_timing", TEXT_EDIT)[0] == "assertion"
    assert hl.raise_verdict("app_defect", "+    x = 1")[0] == "app_defect"
    assert hl.raise_verdict("assertion", "+    x = 1")[0] == "assertion"


# --- R32: add ---------------------------------------------------------------------------------------------


def args(**overrides: object) -> hl.AddArgs:
    base = {"verdict": "locator_timing", "summary": "Wait for switch", "test": "Header", "nodeid": f"{T}::t",
            "diff": "+    x = 1", "branch": "main"}  # fmt: skip
    return hl.AddArgs(**{**base, **overrides})  # type: ignore[arg-type]


def test_f08_r32_healer_log_add_assigns_ids_and_validates(tmp_path: Path) -> None:
    log = tmp_path / "healer" / "log.jsonl"
    first = hl.add_change(args(), log, tmp_path)
    second = hl.add_change(args(request_id="HR-012"), log, tmp_path)
    assert (first["id"], second["id"]) == ("HC-001", "HC-002")
    lines = log.read_text().splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["HC-001", "HC-002"]
    assert json.loads(lines[1])["request_id"] == "HR-012"


def test_f08_r32_unknown_verdict_exits_2_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "log.jsonl"
    code = hl.main(["add", "--verdict", "nonsense", "--summary", "s", "--test", "t", "--nodeid", "n",
                    "--diff", "x", "--branch", "main", "--log", str(log)])  # fmt: skip
    assert code == 2
    assert not log.exists()
    assert "unknown verdict" in capsys.readouterr().err


BAD_FIELDS = [
    {"summary": "x" * 141},
    {"request_id": "HR-1; rm -rf /"},
    {"evidence": ["../.env"]},
    {"agent": "robot"},
    {"test": ""},
]


@pytest.mark.parametrize("bad", BAD_FIELDS)
def test_f08_r32_invalid_fields_are_rejected(tmp_path: Path, bad: dict[str, object]) -> None:
    with pytest.raises(hl.InvalidInputError):
        hl.add_change(args(**bad), tmp_path / "log.jsonl", tmp_path)
    assert not (tmp_path / "log.jsonl").exists()


def test_f08_r32_cli_success_prints_id_and_redacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "log.jsonl"
    code = hl.main(["add", "--verdict", "app_defect", "--summary", "s", "--test", "t", "--nodeid", "n",
                    "--diff", "password=Secret1! Authorization: Bearer abc.defghi", "--branch", "main",
                    "--log", str(log)])  # fmt: skip
    assert code == 0
    assert capsys.readouterr().out.strip() == "HC-001"
    stored = json.loads(log.read_text())
    assert "Secret1" not in stored["diff"]
    assert "abc.def" not in stored["diff"]
    assert "[redacted]" in stored["diff"]
    assert stored["applied"] is False  # app_defect never changes disk


def test_f08_r28_concurrent_appends_both_land(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    threads = [
        threading.Thread(target=hl.add_change, args=(args(summary=f"s{n}"), log, tmp_path)) for n in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    read = hl.read_log(log)
    assert read is not None
    assert not read.skipped
    assert sorted(e.obj["id"] for e in read.changes) == [f"HC-{n:03d}" for n in range(1, 9)]


def test_f08_r28_partial_tail_is_ignored_and_next_append_starts_a_new_line(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    hl.add_change(args(), log, tmp_path)
    with log.open("ab") as handle:
        handle.write(b'{"v":1,"type":"cha')
    read = hl.read_log(log)
    assert read is not None
    assert read.partial_tail
    assert len(read.changes) == 1
    assert not read.skipped
    hl.add_change(args(), log, tmp_path)
    after = hl.read_log(log)
    assert after is not None
    assert [e.obj["id"] for e in after.changes] == ["HC-001", "HC-002"]
    assert [s["reason"] for s in after.skipped] == ["invalid JSON"]


def test_f08_r8_bad_lines_are_skipped_with_reasons() -> None:
    good = hl.build_change(args(), "HC-001", Path("."))
    bad_verdict = {**good, "id": "HC-002", "verdict": "oops"}
    dup = {**good}
    orphan = {"v": 1, "type": "review", "change_id": "HC-099", "ts": "2026-10-06T10:00:00Z",
              "decision": "approved", "by": "A", "role": "reviewer", "note": ""}  # fmt: skip
    rows = [good, bad_verdict, dup, orphan]
    data = ("\n".join(json.dumps(r) for r in rows) + "\nnot json\n").encode()
    read = hl.read_log_bytes(data)
    assert [e.obj["id"] for e in read.changes] == ["HC-001"]
    assert read.skipped == [
        {"line": 2, "reason": "unknown verdict"}, {"line": 3, "reason": "duplicate id"},
        {"line": 4, "reason": "unknown change_id"}, {"line": 5, "reason": "invalid JSON"},
    ]  # fmt: skip


# --- R19 / R33: the CI check -------------------------------------------------------------


def log_with(decision: str | None, **fields: Any) -> bytes:
    change = {
        "v": 1, "type": "change", "id": "HC-001", "ts": "2026-10-06T10:00:00Z", "test": "t", "nodeid": "n",
        "verdict": "assertion", "summary": "s", "files": [], "diff": "", "applied": True, **fields,
    }  # fmt: skip
    rows = [change]
    if decision:
        rows.append({"v": 1, "type": "review", "change_id": "HC-001", "ts": "2026-10-06T11:00:00Z",
                     "decision": decision, "by": "Sanjeev", "role": "reviewer", "note": ""})  # fmt: skip
    return ("\n".join(json.dumps(r) for r in rows) + "\n").encode()


ASSERT_DIFF = (
    make_diff(T, ['    expect(t).to_have_text("A")'], ['    expect(t).to_have_text("B")'])
    .replace("@@ -10,", "@@ -42,")
    .replace("+10,", "+42,")
)


def test_f08_r19_check_fails_on_unlogged_assertion_diff_and_passes_on_reviewed() -> None:
    problems = check.run_checks(check.CheckInput(diff=ASSERT_DIFF, log=b""))
    assert len(problems) == 1
    assert problems[0].startswith(f"{T}:42:")
    reviewed = log_with("approved", verdict="assertion", files=[T], diff=ASSERT_DIFF)
    assert check.run_checks(check.CheckInput(diff=ASSERT_DIFF, log=reviewed)) == []


@pytest.mark.parametrize("decision", [None, "rejected"])
def test_f08_r19_pending_or_rejected_entry_does_not_cover(decision: str | None) -> None:
    log = log_with(decision, verdict="assertion", files=[T], diff=ASSERT_DIFF)
    assert check.run_checks(check.CheckInput(diff=ASSERT_DIFF, log=log))


def test_f08_r19_entry_for_another_file_or_other_lines_does_not_cover() -> None:
    other_file = log_with("approved", verdict="assertion", files=["tests/other.py"], diff=ASSERT_DIFF)
    far = make_diff(T, ["    a"], ["    b"]).replace("@@ -10,", "@@ -900,").replace("+10,", "+900,")
    other_lines = log_with("approved", verdict="assertion", files=[T], diff=far)
    for log in (other_file, other_lines):
        assert check.run_checks(check.CheckInput(diff=ASSERT_DIFF, log=log))


def test_f08_r19_locator_only_diff_needs_no_entry() -> None:
    diff = make_diff("pages/x.py", ['    self.page.locator("a")'], ['    self.page.get_by_test_id("a")'])
    assert check.run_checks(check.CheckInput(diff=diff, log=b"")) == []


def test_f08_r33_check_flags_duplicate_ids_modified_lines_and_unreasoned_skips() -> None:
    one = log_with(None, verdict="locator_timing")
    dup = check.CheckInput(diff="", log=one + one)
    assert any("duplicate id" in p for p in check.run_checks(dup))

    edited = one.replace(b'"summary": "s"', b'"summary": "changed"')
    problems = check.run_checks(check.CheckInput(diff="", log=edited, base_log=one))
    assert problems == ["healer/log.jsonl:1: line modified or deleted versus the base branch"]
    assert check.run_checks(check.CheckInput(diff="", log=one + one[:0], base_log=one)) == []
    assert check.run_checks(check.CheckInput(diff="", log=b"", base_log=one))  # deleted line

    skip = make_diff(T, [], ['@pytest.mark.skip(reason="flaky")'])
    assert any("cites no defect id" in p for p in check.run_checks(check.CheckInput(diff=skip, log=b"")))
    cited = make_diff(T, [], ['@pytest.mark.skip(reason="D-001 zero qty saves")'])
    defects = (
        "| ID | J | S | E | A | Ev | Sev | Status |\n|---|---|---|---|---|---|---|---|\n"
        "| D-001 | J04 | s | e | a | x | major | agreed |\n"
    )
    assert check.run_checks(check.CheckInput(diff=cited, log=b"", defects=defects)) == []
    open_defects = defects.replace("agreed", "open")
    assert any(
        "none agreed" in p
        for p in check.run_checks(check.CheckInput(diff=cited, log=b"", defects=open_defects))
    )
    xfail = make_diff(T, [], ["@pytest.mark.xfail(strict=True)"])
    assert check.run_checks(check.CheckInput(diff=xfail, log=b""))
