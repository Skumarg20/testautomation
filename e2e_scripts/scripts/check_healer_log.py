"""CI check for the healer log (F08 R19, R33). Exit 0 when clean, 1 with one `file:line: reason` per finding.

    python scripts/check_healer_log.py --base origin/main

Fails the PR when:
  1. a diff changes an assertion with no approved `assertion` log entry covering it: the change and its
     review are new in this branch, the reviewer's role is reviewer or admin and is not the change's author,
     and the logged diff makes the same change (same file, same old and new expectation);
  2. the log has a duplicate change id, or an earlier line was modified or deleted versus the base branch;
  3. a diff adds a skip, skipif or xfail marker, or a pytest.skip/xfail/importorskip call, citing no `D-nnn`
     that is `agreed` in docs/defects-*.md.
Exit 2 when git fails (for example a shallow clone without the base ref): the check never passes blind.
The log is a git-tracked file, so it cannot prove who wrote a review line; the console's audit log can.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from scripts import healer_log as hl
except ImportError:  # run as `python scripts/check_healer_log.py`: scripts/ is sys.path[0]
    import healer_log as hl  # type: ignore[no-redef]

E2E_DIR = Path(__file__).resolve().parents[1]
WATCHED = ("tests", "pages", "test_data", "fixtures")
REVIEWER_ROLES = ("reviewer", "admin")  # roles are cumulative: admin includes reviewer
_MARKER = re.compile(r"\bmark\.(skip|skipif|xfail)\b|\bpytest\.(skip|xfail|importorskip)\s*\(")
_STRING = re.compile(r""""([^"]*)"|'([^']*)'""")
_DEFECT_ID = re.compile(r"\bD-\d+\b")


@dataclass
class CheckInput:
    diff: str
    log: bytes
    base_log: bytes = b""
    defects: str = ""


class GitError(RuntimeError):
    pass


@dataclass
class _Coverage:
    files: set[str] = field(default_factory=set)
    keys: dict[str, set[str]] = field(default_factory=dict)  # file -> what each approved finding changed


def _strip_e2e(path: str) -> str:
    return path[4:] if path.startswith("e2e/") else path


def _new_lines(entries: list[hl.LogEntry], base: hl.LogRead) -> list[hl.LogEntry]:
    """Entries this branch added: an approval already on the base branch was for a change already merged."""
    return [e for e in entries if base.shas.get(e.line) != e.sha]


def _valid_approval(review: dict[str, object], change: dict[str, object]) -> bool:
    authors = {change.get("author"), change.get("agent")}
    return (
        review["decision"] == "approved" and review["role"] in REVIEWER_ROLES and review["by"] not in authors
    )


def _approved_assertion_coverage(read: hl.LogRead, base: hl.LogRead) -> list[_Coverage]:
    changes = {e.obj["id"]: e.obj for e in _new_lines(read.changes, base)}
    covers = []
    for review in _new_lines(read.reviews, base):
        change = changes.get(review.obj["change_id"])
        if change is None or change["verdict"] != "assertion" or not _valid_approval(review.obj, change):
            continue
        keys: dict[str, set[str]] = {}
        for f in hl.classify_diff(change["diff"]).findings:
            keys.setdefault(f.file, set()).add(f.key)
        covers.append(_Coverage({_strip_e2e(f) for f in change["files"]}, keys))
    return covers


def _covered(finding: hl.Finding, covers: list[_Coverage]) -> bool:
    for cover in covers:
        if finding.file not in cover.files:
            continue
        if finding.key in cover.keys.get(finding.file, set()) | cover.keys.get("", set()):
            return True
    return False


def check_assertions(data: CheckInput, read: hl.LogRead) -> list[str]:
    covers = _approved_assertion_coverage(read, hl.read_log_bytes(data.base_log))
    return [
        f"{f.file}:{f.line}: assertion changed without an approved log entry ({f.reason})"
        for f in hl.classify_diff(data.diff).findings
        if not _covered(f, covers)
    ]


def check_log_integrity(data: CheckInput, read: hl.LogRead) -> list[str]:
    problems = [
        f"healer/log.jsonl:{s['line']}: {s['reason']}" for s in read.skipped if s["reason"] == "duplicate id"
    ]
    base = hl.read_log_bytes(data.base_log)
    for number, sha in base.shas.items():
        if read.shas.get(number) != sha:
            problems.append(f"healer/log.jsonl:{number}: line modified or deleted versus the base branch")
    return problems


def agreed_defects(defects_text: str) -> set[str]:
    agreed: set[str] = set()
    for row in defects_text.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 8 and _DEFECT_ID.fullmatch(cells[0]) and cells[-1].lower() == "agreed":
            agreed.add(cells[0])
    return agreed


def _marker_problem(text: str, agreed: set[str]) -> str | None:
    reason = " ".join(m.group(1) or m.group(2) or "" for m in _STRING.finditer(text))
    cited = set(_DEFECT_ID.findall(reason))
    if not cited:
        return f"{text.strip()} cites no defect id in its reason"
    if not cited & agreed:
        return f"{text.strip()} cites {', '.join(sorted(cited))}, none agreed in the defects file"
    return None


def check_markers(data: CheckInput) -> list[str]:
    """Every added skip or xfail, decorator or call; the reason is read from the whole (wrapped) statement."""
    agreed = agreed_defects(data.defects)
    problems = []
    for fd in hl.parse_diff(data.diff):
        if fd.path and not fd.path.startswith(tuple(f"{w}/" for w in WATCHED)):
            continue
        for st in hl.statements(fd.lines, "+"):
            added = st.touched
            if added and _MARKER.search(st.text):
                problem = _marker_problem(st.text, agreed)
                if problem:
                    problems.append(f"{fd.path}:{added[0].new}: {problem}")
    return problems


def run_checks(data: CheckInput) -> list[str]:
    read = hl.read_log_bytes(data.log)
    return check_assertions(data, read) + check_log_integrity(data, read) + check_markers(data)


# --- git plumbing (read-only) ------------------------------------------------------------


def _git(argv: list[str]) -> bytes:
    proc = subprocess.run(  # noqa: S603 - fixed argv, shell=False, read-only git
        ["git", *argv],
        cwd=E2E_DIR,
        capture_output=True,
        check=False,
        shell=False,  # noqa: S607
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {' '.join(argv)} failed ({proc.returncode}): {detail}")
    return bytes(proc.stdout)


def _base_log(base: str) -> bytes:
    """The base branch's log, or empty only when the base exists but has no log yet."""
    ref = f"{base}:./healer/log.jsonl"
    try:
        _git(["cat-file", "-e", ref])
    except GitError:
        return b""
    return _git(["show", ref])


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def gather(base: str, log_path: Path) -> CheckInput:
    diff = _git(["diff", "--unified=3", f"{base}...HEAD", "--", *WATCHED]).decode("utf-8", "replace")
    defects = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted((E2E_DIR / "docs").glob("defects-*.md"))
    )
    return CheckInput(diff, _read(log_path), _base_log(base), defects)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--log", type=Path, default=hl.DEFAULT_LOG)
    parser.add_argument("--diff-file", type=Path, help="use this unified diff instead of git")
    ns = parser.parse_args(argv)
    try:
        data = gather(ns.base, ns.log)
    except GitError as exc:
        print(f"check_healer_log: {exc}", file=sys.stderr)
        return 2
    if ns.diff_file:
        data.diff = ns.diff_file.read_text(encoding="utf-8")
    problems = run_checks(data)
    for problem in problems:
        print(problem)
    print(f"check_healer_log: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
