import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from scripts.report_coverage import Journey
from scripts.update_timeline import (
    CellNotFoundError,
    JourneySheetUpdate,
    TimelineWorkbook,
    auto_line,
    merged_note,
)

pytestmark = pytest.mark.framework

TODAY = date(2026, 10, 12)
DATA_BAR_EXTENSION = '<extLst><ext uri="{B025F937}"><x14:id>{DATA-BAR}</x14:id></ext></extLst>'
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
SHEET = f"""<worksheet xmlns="{MAIN}" xmlns:x14="urn:x14"><sheetData>
<row r="9"><c r="A9" t="s"><v>0</v></c><c r="J9" s="4" t="s"><v>1</v></c>
<c r="K9" s="5" t="s"><v>2</v></c></row>
<row r="10"><c r="A10" t="inlineStr"><is><t>J02</t></is></c>
<c r="J10" s="4" t="inlineStr"><is><t>Blocked</t></is></c><c r="K10" s="5"/></row>
<row r="62"><c r="A62" t="inlineStr"><is><t>Updated long ago</t></is></c></row>
</sheetData>{DATA_BAR_EXTENSION}</worksheet>"""
SHARED = f"""<sst xmlns="{MAIN}"><si><t>J01</t></si><si><t>Not Started</t></si>
<si><t>[auto 2026-10-01] old line</t></si></sst>"""
WORKBOOK = f"""<workbook xmlns="{MAIN}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Journey Matrix" sheetId="1" r:id="rId4"/></sheets></workbook>"""
RELS = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId4" Type="worksheet" Target="worksheets/sheet3.xml"/></Relationships>"""


def journey(ref: str, status: str) -> Journey:
    return Journey.model_validate(
        {
            "id": f"journey-{ref}",
            "ref": ref,
            "name": f"Name {ref}",
            "priority": "P1",
            "layers": ["e2e"],
            "in30Plan": "yes",
            "targetDay": None,
            "status": status,
            "specs": [f"tests/journeys/{ref.lower()}/test_a.py", f"tests/journeys/{ref.lower()}/test_b.py"],
        }
    )


@pytest.fixture
def workbook_file(tmp_path: Path) -> Path:
    path = tmp_path / "timeline.xlsx"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("xl/workbook.xml", WORKBOOK)
        package.writestr("xl/_rels/workbook.xml.rels", RELS)
        package.writestr("xl/worksheets/sheet3.xml", SHEET)
        package.writestr("xl/sharedStrings.xml", SHARED)
    return path


def update(path: Path, journeys: list[Journey]) -> list[str]:
    workbook = TimelineWorkbook(path, "Journey Matrix")
    missing = JourneySheetUpdate(workbook, Counter({"journey-J01": 33}), TODAY).apply(journeys)
    workbook.save(path)
    return missing


def reopened(path: Path) -> TimelineWorkbook:
    return TimelineWorkbook(path, "Journey Matrix")


def test_status_follows_the_journey_matrix(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "generated"), journey("J02", "generated")])

    assert reopened(workbook_file).cell_text("J9") == "Generated"


def test_a_status_set_to_blocked_by_hand_is_kept(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "generated"), journey("J02", "generated")])

    assert reopened(workbook_file).cell_text("J10") == "Blocked"


def test_note_gets_a_fresh_auto_line_with_the_test_count(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "generated"), journey("J02", "generated")])

    assert reopened(workbook_file).cell_text("K9") == (
        "[auto 2026-10-12] repo journey `journey-J01` (Name J01): 33 tests in tests/journeys/j01/."
    )


def test_journey_without_tests_says_so(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "generated"), journey("J02", "not_started")])

    assert reopened(workbook_file).cell_text("K10").endswith("no tests yet.")


def test_footer_counts_journeys_with_tests_and_passing(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "passing"), journey("J02", "not_started")])

    footer = reopened(workbook_file).cell_text("A62")

    assert "1 of 2 journeys have tests (33 journey tests), 1 passing" in footer


def test_journeys_the_sheet_has_no_row_for_are_reported(workbook_file: Path) -> None:
    missing = update(workbook_file, [journey("J01", "generated"), journey("J42", "generated")])

    assert missing == ["J42"]


def test_cell_styles_and_excel_extensions_survive(workbook_file: Path) -> None:
    update(workbook_file, [journey("J01", "generated"), journey("J02", "generated")])

    sheet = zipfile.ZipFile(workbook_file).read("xl/worksheets/sheet3.xml").decode()
    assert DATA_BAR_EXTENSION in sheet
    assert '<c r="J9" s="4" t="inlineStr">' in sheet


def test_a_missing_cell_is_refused_not_inserted(workbook_file: Path) -> None:
    with pytest.raises(CellNotFoundError):
        reopened(workbook_file).set_cell_text("Z99", "x")


def test_own_lines_of_a_note_are_kept_below_the_auto_line() -> None:
    note = merged_note("[auto 2026-10-01] old\nD1 bell count defect\nOwner: QA", "[auto 2026-10-12] new")

    assert note == "[auto 2026-10-12] new\nD1 bell count defect\nOwner: QA"


def test_auto_line_lists_each_test_folder_once() -> None:
    line = auto_line(journey("J05", "generated"), 2, TODAY)

    assert line.endswith("2 tests in tests/journeys/j05/.")
