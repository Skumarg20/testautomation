"""Export the test-case sheets of the TypeScript phase-1 suite into reusable files.

Usage: python scripts/import_document_cases.py <path to newmarg-web-automation-release-phase-1>

Writes `test_data/document_cases.json` (every case with its input columns and linked
line items) and `scenarios/document-catalogue.md` (one table per module sheet).
Credential columns are dropped; the source Excel files hold real logins.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
# Any column whose name looks like a credential, not only the exact names (user_password, login_email, pwd).
SECRET_COLUMN = re.compile(r"(?i)pass|pwd|e-?mail|otp|token|secret|login|user[_ ]?(?:name|id)?\b")
LINE_ITEM_SHEETS = {"ProductDetails", "OrderProductDetails"}
DISABLED_SHEETS = {("authentication", "register")}  # commented out in the source sat.list.ts

TABLE_HEADER = "| ID | Type | Description | Active |"
E2E_ROOT = Path(__file__).resolve().parent.parent
Row = dict[str, str]


def _tag(name: str) -> str:
    return f"{{{NS['m']}}}{name}"


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(_tag("t"))) for si in root.findall("m:si", NS)]


def _cell_value(cell: ET.Element, strings: list[str]) -> str:
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    return strings[int(value.text)] if cell.get("t") == "s" else value.text


def _sheet_paths(book: zipfile.ZipFile) -> dict[str, str]:
    relations = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): r.get("Target", "") for r in relations}
    sheets = ET.fromstring(book.read("xl/workbook.xml")).find("m:sheets", NS)
    assert sheets is not None
    paths: dict[str, str] = {}
    for sheet in sheets:
        target = targets[sheet.get(f"{{{NS['r']}}}id")].lstrip("/")
        paths[sheet.get("name", "")] = target if target.startswith("xl/") else "xl/" + target
    return paths


def _column_index(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - ord("A") + 1
    return index - 1


def _row_values(row: ET.Element, strings: list[str]) -> list[str]:
    """Cells by column position: blank cells are missing from the XML, so never rely on order."""
    cells = {_column_index(c.get("r", "")): _cell_value(c, strings) for c in row.findall("m:c", NS)}
    width = max(cells, default=-1) + 1
    return [cells.get(i, "") for i in range(width)]


def _read_rows(book: zipfile.ZipFile, path: str, strings: list[str]) -> list[Row]:
    table = [_row_values(row, strings) for row in ET.fromstring(book.read(path)).iter(_tag("row"))]
    table = [r for r in table if any(r)]
    if not table:
        return []
    header = table[0]
    return [dict(zip(header, r, strict=False)) for r in table[1:]]


def _without_secrets(row: Row) -> Row:
    return {k: v for k, v in row.items() if not SECRET_COLUMN.search(k) and v != ""}


def _linked_case_ids(row: Row) -> list[str]:
    """A line item may serve several cases: `tc_id` is then a comma-separated list."""
    return [case_id.strip() for case_id in row.get("tc_id", "").split(",") if case_id.strip()]


def read_workbook(path: Path) -> dict[str, list[Row]]:
    with zipfile.ZipFile(path) as book:
        strings = _shared_strings(book)
        return {name: _read_rows(book, p, strings) for name, p in _sheet_paths(book).items()}


def collect_cases(source: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for workbook in sorted((source / "test-data" / "test-input").glob("*.xlsx")):
        module = workbook.stem
        sheets = read_workbook(workbook)
        items: dict[str, list[Row]] = {}
        for name in LINE_ITEM_SHEETS & sheets.keys():
            for row in sheets[name]:
                for case_id in _linked_case_ids(row):
                    items.setdefault(case_id, []).append(_without_secrets(row))
        for sheet, rows in sheets.items():
            if sheet in LINE_ITEM_SHEETS:
                continue
            for row in rows:
                cases.append(_case((module, sheet), row, items))
    return cases


def _case(origin: tuple[str, str], row: Row, items: dict[str, list[Row]]) -> dict[str, object]:
    module, sheet = origin
    data = _without_secrets(row)
    case_id = data.pop("tc_id", "")
    return {
        "id": case_id,
        "module": module,
        "sheet": sheet,
        "type": data.pop("tc_type", ""),
        "description": data.pop("tc_description", ""),
        "active": (module, sheet) not in DISABLED_SHEETS,
        "inputs": data,
        "line_items": items.get(case_id, []),
    }


def _table_row(case: dict[str, object]) -> str:
    active = "yes" if case["active"] else "no"
    return f"| {case['id']} | {case['type']} | {case['description']} | {active} |"


def render_catalogue(cases: list[dict[str, object]]) -> str:
    lines = ["# Phase-1 case catalogue (imported from the TypeScript suite)", ""]
    lines.append(
        f"{len(cases)} cases, {sum(bool(c['active']) for c in cases)} active upstream. "
        "Regenerate with `scripts/import_document_cases.py`; data in `test_data/document_cases.json`."
    )
    lines.append("")
    for module, sheet in sorted({(str(c["module"]), str(c["sheet"])) for c in cases}):
        group = [c for c in cases if c["module"] == module and c["sheet"] == sheet]
        lines += [f"## {module} / {sheet} ({len(group)})", "", TABLE_HEADER, "|---|---|---|---|"]
        lines += [_table_row(c) for c in group]
        lines.append("")
    return "\n".join(lines)


def main(source: Path) -> None:
    cases = collect_cases(source)
    payload = json.dumps(cases, indent=2, ensure_ascii=False)
    (E2E_ROOT / "test_data" / "document_cases.json").write_text(payload + "\n")
    (E2E_ROOT / "scenarios" / "document-catalogue.md").write_text(render_catalogue(cases))
    print(f"exported {len(cases)} cases")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
