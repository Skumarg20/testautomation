"""Healer change log: schema, reader, assertion-diff classifier and the `add` command (F08 6.1, 6.2).

Standard library only, so the QA Console (which loads this file by path) and CI use one implementation.

    .venv/bin/python scripts/healer_log.py add --verdict locator_timing --summary "..." \
        --test "..." --nodeid "tests/...::test_x" [--files pages/x.py] [--request-id HR-012]

The log is `healer/log.jsonl` (append-only, one JSON object per line). A change line is written here by
the healer; a `review` line is written by the console only. Exit codes: 0 ok, 2 invalid input.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    import fcntl
except ImportError:  # Windows has no fcntl; msvcrt locks a byte of the lock file instead
    fcntl = None  # type: ignore[assignment]
    import msvcrt


def _lock_exclusive(fileno: int) -> None:
    if fcntl:
        fcntl.flock(fileno, fcntl.LOCK_EX)
    else:
        msvcrt.locking(fileno, msvcrt.LK_LOCK, 1)


def _unlock(fileno: int) -> None:
    if fcntl:
        fcntl.flock(fileno, fcntl.LOCK_UN)
    else:
        msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)


SCHEMA_VERSION = 1
VERDICTS = ("locator_timing", "assertion", "test_data_env", "app_defect")
AGENTS = ("test-healer", "human")
DECISIONS = ("approved", "rejected")
MAX_LINE_BYTES = 128 * 1024
MAX_DIFF_BYTES = 64 * 1024
E2E_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG = E2E_DIR / "healer" / "log.jsonl"
LOCK_NAME = ".log.lock"

CHANGE_ID = re.compile(r"^HC-\d{3,}$")
REQUEST_ID = re.compile(r"^HR-\d+$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_ARTIFACT_ID = re.compile(r"^a_[A-Za-z0-9_-]+$")


# --- redaction (stdlib copy of the rule in F08 6.7; the console applies its own on top) ------------

_SECRET_KEYS = r"password|passwd|token|secret|api[_-]?key|authorization|set-cookie|cookie"
_PAIR = re.compile(
    rf"""(?i)(["']?[\w.-]*(?:{_SECRET_KEYS})[\w.-]*["']?\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,;&]+)"""
)
_BEARER = re.compile(r"(?i)\b(Bearer|Basic)(\s+)[A-Za-z0-9._~+/=-]{6,}")


def redact(text: str) -> str:
    text = _BEARER.sub(r"\1\2[redacted]", text)
    return _PAIR.sub(lambda m: f"{m.group(1)}[redacted]", text)


def truncate_diff(diff: str) -> str:
    raw = diff.encode("utf-8")
    if len(raw) <= MAX_DIFF_BYTES:
        return diff
    cut = raw[:MAX_DIFF_BYTES].decode("utf-8", errors="ignore")
    return cut.rstrip("\n") + "\n[truncated]"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017 (venv runs Python 3.10)


# --- schema validation -----------------------------------------------------------------------------


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def evidence_ok(item: str) -> bool:
    """A relative path under results/ (no `..`, not absolute, no scheme) or an artifact id."""
    if _ARTIFACT_ID.match(item):
        return True
    if item.startswith("/") or "\\" in item or "://" in item:
        return False
    parts = item.split("/")
    return parts[0] == "results" and len(parts) > 1 and ".." not in parts and all(parts)


def _optional_str(obj: dict[str, Any], key: str, pattern: re.Pattern[str] | None = None) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or (pattern is not None and not pattern.match(value)):
        return f"invalid {key}"
    return None


def _check_text_limits(obj: dict[str, Any]) -> str | None:
    for key, limit in (("test", 200), ("summary", 140)):
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            return f"invalid {key}"
        if len(value) > limit:
            return f"{key} too long"
    if not isinstance(obj.get("nodeid"), str) or not obj["nodeid"]:
        return "invalid nodeid"
    if not isinstance(obj.get("diff"), str):
        return "invalid diff"
    return None


def _check_lists(obj: dict[str, Any]) -> str | None:
    if not _is_str_list(obj.get("files")):
        return "invalid files"
    evidence = obj.get("evidence", [])
    if not _is_str_list(evidence) or not all(evidence_ok(e) for e in evidence):
        return "invalid evidence"
    if not isinstance(obj.get("applied"), bool):
        return "invalid applied"
    return None


def _check_identity(obj: dict[str, Any]) -> str | None:
    if obj["verdict"] not in VERDICTS:
        return "unknown verdict"
    if not isinstance(obj["id"], str) or not CHANGE_ID.match(obj["id"]):
        return "invalid id"
    if not isinstance(obj["ts"], str) or not _TS.match(obj["ts"]):
        return "invalid ts"
    if obj.get("agent", "test-healer") not in AGENTS:
        return "invalid agent"
    return None


def _check_optionals(obj: dict[str, Any]) -> str | None:
    for key, pattern in (("request_id", REQUEST_ID), ("run_id", None), ("branch", None)):
        problem = _optional_str(obj, key, pattern)
        if problem:
            return problem
    return None


def validate_change(obj: dict[str, Any]) -> str | None:
    """None when the change line is valid, else a short reason (used in the skipped-lines report)."""
    for key in ("id", "ts", "test", "nodeid", "verdict", "summary", "files", "diff", "applied"):
        if key not in obj:
            return f"missing field {key}"
    return _check_identity(obj) or _check_text_limits(obj) or _check_lists(obj) or _check_optionals(obj)


def validate_review(obj: dict[str, Any]) -> str | None:
    if not isinstance(obj.get("change_id"), str) or not CHANGE_ID.match(obj["change_id"]):
        return "invalid change_id"
    if not isinstance(obj.get("ts"), str) or not _TS.match(obj["ts"]):
        return "invalid ts"
    if obj.get("decision") not in DECISIONS:
        return "invalid decision"
    if not isinstance(obj.get("by"), str) or not obj["by"].strip():
        return "invalid by"
    if not isinstance(obj.get("role"), str) or not obj["role"]:
        return "invalid role"
    note = obj.get("note", "")
    if not isinstance(note, str) or len(note) > 500:
        return "invalid note"
    return None


# --- reader ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LogEntry:
    line: int  # 1-based line number in the file
    sha: str  # sha256 of the raw line bytes (without the newline)
    obj: dict[str, Any]


@dataclass
class LogRead:
    changes: list[LogEntry] = field(default_factory=list)
    reviews: list[LogEntry] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    shas: dict[int, str] = field(default_factory=dict)  # line number -> sha of every complete line
    partial_tail: bool = False


def line_sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_line(raw: bytes) -> tuple[dict[str, Any] | None, str | None]:
    if len(raw) > MAX_LINE_BYTES:
        return None, "line too long"
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, "invalid JSON"
    if not isinstance(obj, dict):
        return None, "not an object"
    if obj.get("v") != SCHEMA_VERSION:
        return None, "unsupported version"
    kind = obj.get("type")
    if kind == "change":
        return obj, validate_change(obj)
    if kind == "review":
        return obj, validate_review(obj)
    return None, "unknown type"


def read_log_bytes(data: bytes) -> LogRead:
    """Parse the log. A last line without a newline is a partial write and is ignored. Never raises."""
    out = LogRead()
    pieces = data.split(b"\n")
    out.partial_tail = pieces[-1] != b""
    complete = pieces[:-1]
    seen: set[str] = set()
    reviewed: set[str] = set()
    for number, raw in enumerate(complete, start=1):
        out.shas[number] = line_sha(raw)
        if not raw.strip():
            continue
        obj, reason = _parse_line(raw)
        if reason is None and obj is not None:
            reason = _link_check(obj, seen, reviewed)
        if reason is not None or obj is None:
            out.skipped.append({"line": number, "reason": reason or "invalid"})
            continue
        entry = LogEntry(number, out.shas[number], obj)
        (out.changes if obj["type"] == "change" else out.reviews).append(entry)
    return out


def _link_check(obj: dict[str, Any], seen: set[str], reviewed: set[str]) -> str | None:
    if obj["type"] == "change":
        if obj["id"] in seen:
            return "duplicate id"
        seen.add(obj["id"])
        return None
    if obj["change_id"] not in seen:
        return "unknown change_id"
    if obj["change_id"] in reviewed:
        return "change already reviewed"
    reviewed.add(obj["change_id"])
    return None


def read_log(path: Path) -> LogRead | None:
    """None when the file does not exist (the console then shows sample rows)."""
    try:
        return read_log_bytes(path.read_bytes())
    except FileNotFoundError:
        return None


def next_change_id(read: LogRead | None, raw_ids: list[str] | None = None) -> str:
    numbers = [int(e.obj["id"][3:]) for e in (read.changes if read else [])]
    numbers += [int(i[3:]) for i in raw_ids or [] if CHANGE_ID.match(i)]
    return f"HC-{max(numbers, default=0) + 1:03d}"


# --- lock and append -------------------------------------------------------------------------------


@contextlib.contextmanager
def log_lock(log_path: Path) -> Iterator[None]:
    """Exclusive flock on `<log dir>/.log.lock`; the console and this script share it."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path.parent / LOCK_NAME, "a+b") as handle:
        _lock_exclusive(handle.fileno())
        try:
            yield
        finally:
            _unlock(handle.fileno())


def append_line(log_path: Path, obj: dict[str, Any]) -> None:
    """One O_APPEND write of one line. Call under `log_lock`. A torn last line gets a newline first."""
    line = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(line) > MAX_LINE_BYTES:
        raise ValueError("line too long")
    fd = os.open(log_path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        size = os.fstat(fd).st_size
        if size and os.pread(fd, 1, size - 1) != b"\n":
            line = b"\n" + line
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)


# --- assertion classifier (F08 6.2) ----------------------------------------------------------------

SCOPE_PREFIXES = ("tests/", "pages/", "test_data/")
_WEAKER = {
    "to_have_text": "to_contain_text",
    "to_have_value": "to_contain_text",
    "to_have_count": "to_be_visible",
    "to_be_visible": "to_be_attached",
    "to_be_enabled": "to_be_attached",
}
_IGNORED_KWARGS = ("timeout", "soft")
_EXPECTED_NAME = re.compile(r"(?i)expected")
_DATA_NAME = re.compile(r"(?i)expected|total|tax|itc|gst|round|cgst|sgst|igst|cess|amount|rate")
_ASSIGN = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*(?::\s*[^=]+?)?=(?!=)\s*(?P<val>.+?)\s*$")
_DICT_ITEM = re.compile(r"""^\s*["'](?P<name>\w*expected\w*)["']\s*:\s*(?P<val>.+?),?\s*$""", re.IGNORECASE)
_ROW = re.compile(r"^\s*[(\[].*[)\]],?\s*$")
_PARAM = re.compile(r"parametrize\(\s*[\"'][^\"']*expected", re.IGNORECASE)
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    reason: str
    key: str = field(default="", compare=False)  # what changed, without line numbers (CI matches approvals)


@dataclass(frozen=True)
class Classification:
    assertion: bool
    findings: tuple[Finding, ...]

    @property
    def reason(self) -> str | None:
        return self.findings[0].reason if self.findings else None


@dataclass
class DLine:
    tag: str  # "+", "-" or " "
    text: str
    old: int
    new: int


@dataclass
class FileDiff:
    path: str = ""
    is_new: bool = False
    lines: list[DLine] = field(default_factory=list)


def _clean_path(raw: str) -> str:
    raw = raw.strip().split("\t")[0]
    for prefix in ("a/", "b/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
    return raw[4:] if raw.startswith("e2e/") else raw


class _DiffParser:
    def __init__(self) -> None:
        self.files: list[FileDiff] = []
        self.current: FileDiff | None = None
        self.old = 0
        self.new = 0

    def open_file(self) -> FileDiff:
        self.current = FileDiff()
        self.files.append(self.current)
        return self.current

    def file(self) -> FileDiff:
        return self.current or self.open_file()

    def header(self, minus: str, plus: str) -> None:
        current = self.current
        if current is None or current.lines or current.path:
            current = self.open_file()
        current.is_new = current.is_new or minus.strip() == "/dev/null"
        target = minus if plus.strip() == "/dev/null" else plus
        current.path = _clean_path(target)

    def hunk(self, match: re.Match[str]) -> None:
        self.old, self.new = int(match.group(1)), int(match.group(2))

    def content(self, row: str) -> None:
        self.file().lines.append(DLine(row[0], row[1:], self.old, self.new))
        self.old += row[0] != "+"
        self.new += row[0] != "-"


def parse_diff(diff: str) -> list[FileDiff]:
    """Split a unified diff into files with numbered lines. A diff without headers is one unnamed file."""
    parser = _DiffParser()
    rows = diff.splitlines()
    skip = False
    for i, row in enumerate(rows):
        following = rows[i + 1] if i + 1 < len(rows) else ""
        if skip:
            skip = False
        elif row.startswith("diff --git"):
            parser.open_file()
        elif row.startswith("new file mode"):
            parser.file().is_new = True
        elif row.startswith("--- ") and following.startswith("+++ "):
            parser.header(row[4:], following[4:])
            skip = True
        elif m := _HUNK.match(row):
            parser.hunk(m)
        elif row[:1] in ("+", "-", " "):
            parser.content(row)
    return parser.files


def _norm(value: str) -> str:
    return re.sub(r"\s+", "", value.replace("'", '"'))


def _outside_strings(text: str, start: int = 0) -> Iterator[tuple[int, str]]:
    """(position, char) of each char outside a string literal; a backslash escapes the next char."""
    quote, escaped = "", False
    for pos in range(start, len(text)):
        ch = text[pos]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        else:
            yield pos, ch


def _balanced(text: str, start: int) -> int:
    """Index of the ')' that closes the '(' at `start`, or -1. Skips string literals."""
    depth = 0
    for pos, ch in _outside_strings(text, start):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return pos
    return -1


def _split_top(text: str) -> list[str]:
    parts, depth, last = [], 0, 0
    for pos, ch in _outside_strings(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[last:pos])
            last = pos + 1
    parts.append(text[last:])
    return [p for p in parts if p.strip()]


@dataclass(frozen=True)
class Assertion:
    subject: str
    matcher: str
    args: str
    line: int

    @property
    def signature(self) -> tuple[str, str, str]:
        return (self.subject, self.matcher, self.args)


def _kept_args(raw: str) -> str:
    kept = [p for p in _split_top(raw) if p.split("=", 1)[0].strip() not in _IGNORED_KWARGS or "=" not in p]
    return _norm(",".join(kept))


def parse_assertion(text: str, line: int) -> Assertion | None:
    stripped = text.strip()
    if stripped.startswith("assert ") or stripped.startswith("assert("):
        expr = _split_top(stripped[6:])
        return Assertion("", "assert", _norm(expr[0] if expr else ""), line)
    pos = stripped.find("expect(")
    if pos < 0:
        return None
    open_subject = pos + len("expect")
    close = _balanced(stripped, open_subject)
    rest = stripped[close + 1 :] if close >= 0 else ""
    m = re.match(r"\.((?:not_)?to_\w+)\(", rest)
    if close < 0 or not m:
        return None
    arg_open = close + 1 + m.end() - 1
    arg_close = _balanced(stripped, arg_open)
    if arg_close < 0:
        return None
    subject = _norm(stripped[open_subject + 1 : close])
    return Assertion(subject, m.group(1), _kept_args(stripped[arg_open + 1 : arg_close]), line)


def _is_code(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and not stripped.startswith("#")


def _pair_assertions(removed: list[Assertion], added: list[Assertion], file: str) -> list[Finding]:
    removed, added = list(removed), list(added)
    for item in list(removed):  # unchanged after normalisation (comment, timeout, move)
        twin = next((a for a in added if a.signature == item.signature), None)
        if twin is not None:
            removed.remove(item)
            added.remove(twin)
    for item in list(removed):  # same matcher and arguments, new subject: a locator change
        twin = next((a for a in added if a.matcher == item.matcher and a.args == item.args), None)
        if twin is not None and item.matcher != "assert":
            removed.remove(item)
            added.remove(twin)
    findings: list[Finding] = []
    for item in removed:
        findings.append(_describe(item, added, file))
        if added:
            added.pop(0)
    return findings


def _describe(item: Assertion, added: list[Assertion], file: str) -> Finding:
    twin = next((a for a in added if a.subject == item.subject), added[0] if added else None)
    key = f"{item.signature}->{twin.signature if twin else None}"
    if twin is None:
        return Finding(file, item.line, f"{item.matcher} assertion deleted on line {item.line}", key)
    if twin.matcher != item.matcher:
        weaker = _WEAKER.get(item.matcher) == twin.matcher
        word = "weakened" if weaker else "changed"
        return Finding(
            file, twin.line, f"matcher {word} ({item.matcher} to {twin.matcher}) on line {twin.line}", key
        )
    return Finding(file, twin.line, f"matcher argument changed on line {twin.line}", key)


def _code_part(text: str) -> str:
    """The line without a trailing `#` comment (a `#` inside a string literal is kept)."""
    for pos, ch in _outside_strings(text):
        if ch == "#":
            return text[:pos]
    return text


def _bracket_depth(text: str) -> tuple[int, int]:
    """(net bracket depth change, lowest running depth) of one line, skipping strings and comments."""
    depth = low = 0
    for _, ch in _outside_strings(_code_part(text)):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            low = min(low, depth)
    return depth, low


@dataclass
class Statement:
    """One logical statement as seen on one side of a diff (context lines plus `tag` lines)."""

    tag: str
    lines: list[DLine] = field(default_factory=list)
    truncated: bool = False  # opened before the hunk or still open at its end: content not fully shown

    @property
    def text(self) -> str:
        return " ".join(_code_part(d.text).strip() for d in self.lines)

    @property
    def touched(self) -> list[DLine]:
        return [d for d in self.lines if d.tag == self.tag and _is_code(d.text)]

    def number(self, d: DLine) -> int:
        return d.old if self.tag == "-" else d.new


class _StatementGrouper:
    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.out: list[Statement] = []
        self.current: Statement | None = None
        self.depth, self.previous, self.hunk_start = 0, -1, 0

    def add(self, d: DLine) -> None:
        number = d.old if self.tag == "-" else d.new
        if number != self.previous + 1:  # a new hunk starts
            self.close(truncated=True)
            self.hunk_start = len(self.out)
        self.previous = number
        net, low = _bracket_depth(d.text)
        if self.current is None:
            self.current = Statement(self.tag)
            self.out.append(self.current)
        self.current.lines.append(d)
        if (
            self.depth + low < 0
        ):  # closes a bracket opened above the hunk: all lines since its start are in it
            self._merge_since_hunk_start()
            self.depth = net - low
        else:
            self.depth += net
        if self.depth <= 0:
            self.close(truncated=False)

    def _merge_since_hunk_start(self) -> None:
        merged = [line for st in self.out[self.hunk_start :] for line in st.lines]
        del self.out[self.hunk_start :]
        self.current = Statement(self.tag, merged, truncated=True)
        self.out.append(self.current)

    def close(self, truncated: bool) -> None:
        if self.current is not None and truncated:
            self.current.truncated = True
        self.current, self.depth = None, 0


def statements(lines: list[DLine], tag: str) -> list[Statement]:
    """Group one side of a diff into logical statements, joining lines while a bracket is open."""
    grouper = _StatementGrouper(tag)
    for d in lines:
        if d.tag in (" ", tag):
            grouper.add(d)
    grouper.close(truncated=True)
    return grouper.out


def _assertions(stmts: list[Statement]) -> list[Assertion]:
    out = []
    for st in stmts:
        touched = st.touched
        if touched and not st.truncated:
            parsed = parse_assertion(st.text, st.number(touched[0]))
            if parsed is not None:
                out.append(parsed)
    return out


_ASSERT_WORD = re.compile(r"\bexpect\(|(?:^|\s)assert\b")
_WAIT_KWARG = re.compile(rf"^\s*(?:{'|'.join(_IGNORED_KWARGS)})\s*=[^,]*,?\s*$")
_BARE_LITERAL = re.compile(
    r"""^\s*(?:[-+]?\d[\d_.]*|[rbuf]{0,2}(?:"(?!"")[^"]*"|'(?!'')[^']*'))\s*,?\s*$""", re.I
)


def _fragment(text: str) -> bool:
    """A line that is not a statement on its own: an item of a list or call opened outside the hunk."""
    code = _code_part(text).rstrip()
    return code.endswith((",", "\\")) or bool(_BARE_LITERAL.match(code))


def _unseen_expectation(st: Statement, expectations_file: bool) -> bool:
    """A statement the hunk does not show in full, whose change may alter what a test expects.

    In tests/ and test_data/ any such change counts (the opener of a wrapped `expect(...)` or list of
    expected values may sit outside the context lines), except a change of only a `timeout=` / `soft=`
    argument. In pages/ only a change in a visibly open `expect(` or `assert` counts, so a wrapped
    locator or wait fix in a page object stays a locator change.
    """
    touched = st.touched
    if not touched:
        return False
    if not st.truncated and not (expectations_file and len(st.lines) == 1 and _fragment(touched[0].text)):
        return False
    if _ASSERT_WORD.search(st.text):
        return True
    return expectations_file and not all(_WAIT_KWARG.match(_code_part(d.text)) for d in touched)


def _truncated_findings(fd: FileDiff, sides: list[list[Statement]]) -> list[Finding]:
    """Fail closed: a change inside a statement the hunk does not show in full may change an expectation."""
    findings = []
    expectations_file = fd.path.startswith(("tests/", "test_data/"))
    for stmts in sides:
        for st in stmts:
            touched = st.touched
            if _unseen_expectation(st, expectations_file):
                line = st.number(touched[0])
                key = "|".join(f"{d.tag}{_norm(d.text)}" for d in touched)
                reason = (
                    f"change inside a statement the diff does not show in full on line {line} (fail closed)"
                )
                findings.append(Finding(fd.path, line, reason, key))
        if findings:
            return findings
    return findings


def _assigned(text: str, data_file: bool) -> tuple[str, str] | None:
    m = _DICT_ITEM.match(text) or _ASSIGN.match(text)
    if m is None:
        return None
    name = m.group("name")
    pattern = _DATA_NAME if data_file else _EXPECTED_NAME
    return (name, _norm(m.group("val"))) if pattern.search(name) else None


def _constants(
    items: list[tuple[str, str, int]], data_file: bool
) -> tuple[dict[str, str], dict[str, tuple[str, int]]]:
    old: dict[str, str] = {}
    new: dict[str, tuple[str, int]] = {}
    for tag, text, line in items:
        hit = _assigned(text, data_file)
        if hit and tag == "-":
            old[hit[0]] = hit[1]
        elif hit:
            new[hit[0]] = (hit[1], line)
    return old, new


def _compare_constants(path: str, old: dict[str, str], new: dict[str, tuple[str, int]]) -> list[Finding]:
    findings = []
    for name, value in old.items():
        if name not in new:
            findings.append(Finding(path, 0, f"expected constant {name} removed", f"{name}:{value}->None"))
        elif new[name][0] != value:
            line = new[name][1]
            key = f"{name}:{value}->{new[name][0]}"
            findings.append(Finding(path, line, f"expected constant {name} changed on line {line}", key))
    return findings


def _constant_findings(fd: FileDiff, sides: list[list[Statement]], data_file: bool) -> list[Finding]:
    """Per changed line, then per whole statement (a wrapped value), both sides of the diff."""
    lines = [(d.tag, d.text, d.new) for d in fd.lines if d.tag != " " and _is_code(d.text)]
    findings = _compare_constants(fd.path, *_constants(lines, data_file))
    whole = [
        (st.tag, st.text, st.number(st.lines[0]))
        for stmts in sides
        for st in stmts
        if len(st.lines) > 1 and not st.truncated
    ]
    seen = {f.reason for f in findings}
    for finding in _compare_constants(fd.path, *_constants(whole, data_file)):
        if finding.reason not in seen and finding.line != 0:
            findings.append(finding)
    return findings


def _parametrize_findings(fd: FileDiff) -> list[Finding]:
    in_block = False
    for d in fd.lines:
        if _PARAM.search(d.text):
            in_block = True
            if d.tag != " ":
                key = f"{d.tag}{_norm(d.text)}"
                return [Finding(fd.path, d.new or d.old, "parametrize expected values changed", key)]
        elif in_block and d.tag != " " and _is_code(d.text) and _ROW.match(d.text):
            line, key = d.new or d.old, f"{d.tag}{_norm(d.text)}"
            return [Finding(fd.path, line, f"parametrize expected row changed on line {line}", key)]
    return []


def _helper_findings(fd: FileDiff) -> list[Finding]:
    """Any code change in a rounding helper such as test_data/gst_calc.py alters expected numbers."""
    for d in fd.lines:
        if d.tag != " " and _is_code(d.text) and not d.text.lstrip().startswith(("import ", "from ")):
            line, key = d.new or d.old, f"{d.tag}{_norm(d.text)}"
            return [Finding(fd.path, line, f"rounding helper changed on line {line}", key)]
    return []


def _in_scope(path: str) -> bool:
    return not path or path.startswith(SCOPE_PREFIXES)


def _classify_file(fd: FileDiff) -> list[Finding]:
    data_file = fd.path.startswith("test_data/")
    removed, added = statements(fd.lines, "-"), statements(fd.lines, "+")
    findings = _pair_assertions(_assertions(removed), _assertions(added), fd.path)
    findings += _constant_findings(fd, [removed, added], data_file) + _parametrize_findings(fd)
    findings += _truncated_findings(fd, [added, removed])
    if data_file and Path(fd.path).name == "gst_calc.py" and not findings:
        findings += _helper_findings(fd)
    return findings


def classify_diff(diff: str) -> Classification:
    """True `assertion` when the diff changes what a test expects. Pure; new files are not classified."""
    findings: list[Finding] = []
    for fd in parse_diff(diff or ""):
        if fd.is_new or not _in_scope(fd.path):
            continue
        findings += _classify_file(fd)
    return Classification(bool(findings), tuple(findings))


def raise_verdict(verdict: str, diff: str) -> tuple[str, Classification]:
    """May raise a verdict to `assertion`, never lowers it."""
    result = classify_diff(diff)
    return ("assertion" if result.assertion else verdict), result


# --- add command -----------------------------------------------------------------------------------


class InvalidInputError(ValueError):
    pass


@dataclass
class AddArgs:
    verdict: str
    summary: str
    test: str
    nodeid: str
    files: list[str] = field(default_factory=list)
    diff: str | None = None
    request_id: str | None = None
    run_id: str | None = None
    branch: str | None = None
    applied: bool = True
    agent: str = "test-healer"
    evidence: list[str] = field(default_factory=list)


def _git(argv: list[str], cwd: Path) -> str | None:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, shell=False, read-only git
            argv, cwd=cwd, capture_output=True, text=True, timeout=20, check=False, shell=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def capture_diff(files: list[str], cwd: Path) -> str:
    if not files:
        return ""
    return _git(["git", "diff", "--", *files], cwd) or ""


def build_change(args: AddArgs, change_id: str, e2e_dir: Path) -> dict[str, Any]:
    branch = args.branch
    if branch is None:
        out = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"], e2e_dir)
        branch = out.strip() if out else None
    diff = args.diff if args.diff is not None else capture_diff(args.files, e2e_dir)
    obj: dict[str, Any] = {
        "v": SCHEMA_VERSION,
        "type": "change",
        "id": change_id,
        "ts": now_iso(),
        "request_id": args.request_id,
        "run_id": args.run_id,
        "test": redact(args.test),
        "nodeid": args.nodeid,
        "verdict": args.verdict,
        "summary": redact(args.summary),
        "files": args.files,
        "diff": truncate_diff(redact(diff)),
        "applied": args.applied and args.verdict != "app_defect",
        "branch": branch,
        "evidence": args.evidence,
        "agent": args.agent,
    }
    problem = validate_change(obj)
    if problem:
        raise InvalidInputError(problem)
    return obj


def add_change(args: AddArgs, log_path: Path, e2e_dir: Path) -> dict[str, Any]:
    """Validate, take the lock, assign the next HC-nnn and append one line. Nothing is written on error."""
    build_change(args, "HC-000", e2e_dir)  # validate before touching the file
    with log_lock(log_path):
        data = log_path.read_bytes() if log_path.exists() else b""
        ids = re.findall(rb'"id"\s*:\s*"(HC-\d+)"', data)
        change_id = next_change_id(read_log_bytes(data), [i.decode() for i in ids])
        obj = build_change(args, change_id, e2e_dir)
        append_line(log_path, obj)
    return obj


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="healer_log.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="append one change line")
    add.add_argument("--verdict", required=True)
    add.add_argument("--summary", required=True)
    add.add_argument("--test", required=True)
    add.add_argument("--nodeid", required=True)
    add.add_argument("--files", nargs="*", default=[])
    add.add_argument("--diff", help="diff text, or '-' to read stdin; default: git diff of --files")
    add.add_argument("--request-id")
    add.add_argument("--run-id")
    add.add_argument("--branch")
    add.add_argument("--not-applied", action="store_true")
    add.add_argument("--agent", default="test-healer")
    add.add_argument("--evidence", nargs="*", default=[])
    add.add_argument("--log", type=Path, default=Path(os.environ.get("HEALER_LOG", DEFAULT_LOG)))
    return parser


def main(argv: list[str] | None = None) -> int:
    ns = _parser().parse_args(argv)
    diff = sys.stdin.read() if ns.diff == "-" else ns.diff
    args = AddArgs(
        verdict=ns.verdict, summary=ns.summary, test=ns.test, nodeid=ns.nodeid, files=ns.files, diff=diff,
        request_id=ns.request_id, run_id=ns.run_id, branch=ns.branch, applied=not ns.not_applied,
        agent=ns.agent, evidence=ns.evidence,
    )  # fmt: skip
    try:
        obj = add_change(args, ns.log, E2E_DIR)
    except (InvalidInputError, ValueError) as exc:
        print(f"healer_log: invalid input: {exc}", file=sys.stderr)
        return 2
    print(obj["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
