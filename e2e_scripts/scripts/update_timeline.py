"""Updates the "Journey Matrix" sheet of the timeline workbook from the journey matrix and collected tests.

Per journey row it rewrites the Status cell and the first line of the Notes cell (the line that starts with
`[auto`); the rest of a note is the team's own text and is kept. A row a human set to "Blocked" keeps that
status. The footer note of the sheet is rewritten too. Nothing else changes.

The workbook is patched in its XML instead of being re-saved through a spreadsheet library, because
openpyxl drops the sheet's data bars and other Excel extensions on save.

Usage (from e2e/): python -m scripts.update_timeline <path/to/timeline.xlsx>
"""

import contextlib
import io
import re
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import pytest

from scripts.report_coverage import MATRIX_FILE, Journey, Matrix

SHEET_NAME = "Journey Matrix"
JOURNEY_TESTS = "tests/journeys"
STATUS_COLUMN = "J"
NOTES_COLUMN = "K"
AUTO_PREFIX = "[auto"
FOOTER_PREFIX = "Updated "
MANUAL_STATUS = "Blocked"
STATUS_LABELS = {
    "not_started": "Not Started",
    "planned": "Planned",
    "generated": "Generated",
    "passing": "Passing",
}
JOURNEY_REF = re.compile(r"^J\d{2}$")
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class SheetNotFoundError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(f"The workbook has no sheet named {name!r}")


class CellNotFoundError(LookupError):
    def __init__(self, ref: str) -> None:
        super().__init__(f"Cell {ref} does not exist in the sheet; this script never inserts cells")


class JourneyCounter:
    """pytest plugin: counts the collected tests per `journey` marker."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            marker = item.get_closest_marker("journey")
            if marker:
                self.counts[marker.args[0]] += 1


def collect_test_counts() -> Counter[str]:
    """Collects the journey tests in-process. Reports go to a temporary folder so results/ is untouched."""
    counter = JourneyCounter()
    with tempfile.TemporaryDirectory() as reports, contextlib.redirect_stdout(io.StringIO()):
        pytest.main(_collect_only_args(Path(reports)), plugins=[counter])
    return counter.counts


def _collect_only_args(reports: Path) -> list[str]:
    return [
        JOURNEY_TESTS,
        "--collect-only",
        "-q",
        "-n",
        "0",
        "-p",
        "no:cacheprovider",
        f"--junitxml={reports / 'junit.xml'}",
        f"--json-report-file={reports / 'report.json'}",
        f"--html={reports / 'report.html'}",
    ]


class TimelineWorkbook:
    """One sheet of an .xlsx package, read and patched as XML; every other part is copied byte for byte."""

    def __init__(self, path: Path, sheet_name: str) -> None:
        with zipfile.ZipFile(path) as package:
            self._parts = {info.filename: package.read(info) for info in package.infolist()}
            self._infos = package.infolist()
        self._sheet_part = self._sheet_part_named(sheet_name)
        self._sheet_xml = self._parts[self._sheet_part].decode("utf-8")
        self._shared = self._shared_strings()

    def column_a_refs(self) -> dict[int, str]:
        """Row number -> text of column A, for every row that has one."""
        return {
            int(row): text
            for row in re.findall(r'<c r="A(\d+)"', self._sheet_xml)
            if (text := self.cell_text(f"A{row}"))
        }

    def cell_text(self, ref: str) -> str:
        match = _cell_pattern(ref).search(self._sheet_xml)
        if not match:
            return ""
        return self._text_of(ElementTree.fromstring(_with_namespace(match.group(0))))

    def set_cell_text(self, ref: str, text: str) -> None:
        match = _cell_pattern(ref).search(self._sheet_xml)
        if not match:
            raise CellNotFoundError(ref)
        style = re.search(r'\ss="(\d+)"', match.group("attrs"))
        style_attribute = f' s="{style.group(1)}"' if style else ""
        cell = (
            f'<c r="{ref}"{style_attribute} t="inlineStr">'
            f'<is><t xml:space="preserve">{escape(text)}</t></is></c>'
        )
        self._sheet_xml = self._sheet_xml[: match.start()] + cell + self._sheet_xml[match.end() :]

    def save(self, path: Path) -> None:
        """Writes a new package next to `path`, then swaps it in, so a failed write leaves the old file."""
        self._parts[self._sheet_part] = self._sheet_xml.encode("utf-8")
        partial = path.with_suffix(".partial.xlsx")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as package:
            for info in self._infos:
                package.writestr(info, self._parts[info.filename])
        partial.replace(path)

    def _sheet_part_named(self, name: str) -> str:
        workbook = ElementTree.fromstring(self._parts["xl/workbook.xml"])
        relations = ElementTree.fromstring(self._parts["xl/_rels/workbook.xml.rels"])
        targets = {
            rel.get("Id"): rel.get("Target", "") for rel in relations.iter(f"{PACKAGE_REL_NS}Relationship")
        }
        for sheet in workbook.iter(f"{MAIN_NS}sheet"):
            if sheet.get("name") == name:
                return "xl/" + targets[sheet.get(f"{REL_NS}id")].removeprefix("/xl/")
        raise SheetNotFoundError(name)

    def _shared_strings(self) -> list[str]:
        part = self._parts.get("xl/sharedStrings.xml")
        if part is None:
            return []
        return [_joined_text(item) for item in ElementTree.fromstring(part).iter(f"{MAIN_NS}si")]

    def _text_of(self, cell: ElementTree.Element) -> str:
        if cell.get("t") == "s":
            return self._shared[int(cell.findtext(f"{MAIN_NS}v", "0"))]
        if cell.get("t") == "inlineStr":
            return _joined_text(cell)
        return cell.findtext(f"{MAIN_NS}v", "")


def _cell_pattern(ref: str) -> re.Pattern[str]:
    return re.compile(rf'<c r="{ref}"(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', re.S)


def _with_namespace(cell_xml: str) -> str:
    """A cell cut out of the sheet loses the sheet's namespace declaration; put it back for parsing."""
    return cell_xml.replace("<c ", f'<c xmlns="{MAIN_NS[1:-1]}" ', 1)


def _joined_text(element: ElementTree.Element) -> str:
    return "".join(text.text or "" for text in element.iter(f"{MAIN_NS}t"))


def auto_line(journey: Journey, test_count: int, today: date) -> str:
    where = ", ".join(sorted({"/".join(spec.split("/")[:3]) + "/" for spec in journey.specs}))
    tests = f"{test_count} tests in {where}" if test_count else "no tests yet"
    return f"{AUTO_PREFIX} {today.isoformat()}] repo journey `{journey.id}` ({journey.name}): {tests}."


def merged_note(old_note: str, new_auto_line: str) -> str:
    """The new auto line, then the team's own lines of the old note."""
    own_lines = [line for line in old_note.splitlines() if not line.startswith(AUTO_PREFIX)]
    return "\n".join([new_auto_line, *own_lines]).strip()


def footer_note(journeys: list[Journey], test_counts: Counter[str], today: date) -> str:
    generated = sum(journey.status in ("generated", "passing") for journey in journeys)
    passing = sum(journey.is_passing for journey in journeys)
    return (
        f"{FOOTER_PREFIX}{today.isoformat()} by `make coverage` from e2e/coverage/journey-matrix.json and "
        f"the collected tests: {generated} of {len(journeys)} journeys have tests "
        f"({sum(test_counts.values())} journey tests), {passing} passing. 'Generated' means tests exist; "
        "'Passing' needs a green run on QA with reviewer sign-off. Notes lines starting [auto are "
        "rewritten each run; add your own text below them."
    )


class JourneySheetUpdate:
    def __init__(self, workbook: TimelineWorkbook, test_counts: Counter[str], today: date) -> None:
        self._workbook = workbook
        self._test_counts = test_counts
        self._today = today

    def apply(self, journeys: list[Journey]) -> list[str]:
        """Updates every journey row the sheet has; returns the refs the sheet has no row for."""
        by_ref = {journey.ref: journey for journey in journeys}
        rows = self._workbook.column_a_refs()
        journey_rows = {row: text for row, text in rows.items() if JOURNEY_REF.match(text)}
        for row, ref in journey_rows.items():
            if ref in by_ref:
                self._update_row(row, by_ref[ref])
        self._update_footer(rows, journeys)
        return sorted(set(by_ref) - set(journey_rows.values()))

    def _update_row(self, row: int, journey: Journey) -> None:
        status_ref, notes_ref = f"{STATUS_COLUMN}{row}", f"{NOTES_COLUMN}{row}"
        if self._workbook.cell_text(status_ref) != MANUAL_STATUS:
            self._workbook.set_cell_text(status_ref, STATUS_LABELS[journey.status])
        line = auto_line(journey, self._test_counts[journey.id], self._today)
        self._workbook.set_cell_text(notes_ref, merged_note(self._workbook.cell_text(notes_ref), line))

    def _update_footer(self, rows: dict[int, str], journeys: list[Journey]) -> None:
        for row, text in rows.items():
            if text.startswith(FOOTER_PREFIX):
                self._workbook.set_cell_text(f"A{row}", footer_note(journeys, self._test_counts, self._today))


def main(workbook_path: Path) -> None:
    if not workbook_path.is_file():
        print(f"Timeline workbook not found, skipped: {workbook_path}")
        return
    journeys = Matrix.model_validate_json(MATRIX_FILE.read_text()).journeys
    workbook = TimelineWorkbook(workbook_path, SHEET_NAME)
    missing = JourneySheetUpdate(workbook, collect_test_counts(), date.today()).apply(journeys)
    workbook.save(workbook_path)
    print(f"Updated {workbook_path} ({len(journeys) - len(missing)} journey rows).")
    if missing:
        print(f"No row in the sheet for: {', '.join(missing)} (add them by hand)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
