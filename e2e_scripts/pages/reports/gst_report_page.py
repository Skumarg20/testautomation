"""GST statutory reports (Report > Statutory Report > GST Report): open one, read a row, export."""

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from playwright.sync_api import Download, Locator, expect

from pages.base_page import BasePage
from test_data.money import parse_amount

REPORT_PATHS = {"GSTR-1": "/report/gst/gstr1", "GSTR-2": "/report/gst/gstr2", "GSTR-3B": "/report/gst/gstr3b"}
EXPORT_TIMEOUT_MS = 60_000
LOAD_TIMEOUT_MS = 60_000
FIGURE_COLUMNS = {
    "No. of vouchers": "Vouchers",
    "Taxable Value": "TaxableValue",
    "Integrated Tax": "IntegratedTax",
    "Central Tax": "CentralTax",
    "State Tax": "StateTax",
}
DATE_FILTER_SHORTCUT = "Alt+D"
IFF_DIALOG_TITLE = "GSTR 1: IFF Facility"
TAXABLE_VALUE_COLUMN = "Taxable Value"
# Either the GSTR-1 title ("GSTR-1 01-09-2026 to 30-09-2026") or the date span every report shows
# ("01-09-2026-To- 30-09-2026"; GSTR-3B has no title). A bare date range would also match the sidebar's
# company financial year, which made the locator ambiguous.
PERIOD = re.compile(
    r"GSTR-\S+\s+\d{2}-\d{2}-\d{4}\s+to\s+\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{4}-To-\s*\d{2}-\d{2}-\d{4}"
)


@dataclass(frozen=True)
class ReportPeriod:
    """Both dates as the Date Filter takes them, dd-mm-yyyy."""

    start: str
    end: str


class UnknownReportError(KeyError):
    def __init__(self, report_name: str) -> None:
        super().__init__(f'No path known for report "{report_name}"; known: {sorted(REPORT_PATHS)}')


class GstReportPage(BasePage):
    def open_report(self, report_name: str) -> None:
        """Opens a GST report by its page path, for example "GSTR-1" or "GSTR-3B"."""
        if report_name not in REPORT_PATHS:
            raise UnknownReportError(report_name)
        self.goto(REPORT_PATHS[report_name])
        expect(self._period).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def period(self) -> str:
        return self._period.inner_text().strip()

    def taxable_value_of(self, particulars: str) -> Decimal:
        row = self._row(particulars)
        index = self._column_index(TAXABLE_VALUE_COLUMN)
        return parse_amount(row.get_by_role("gridcell").nth(index).inner_text())

    def screen_figures(self, particulars: str) -> dict[str, Decimal]:
        """Vouchers, taxable value and the taxes of one grid row, keyed by the export's column names.

        The grid leaves out a tax column when the period has no figure for it (an inter-state-only month
        shows no State Tax), so a column that is not on screen is not in the result.
        """
        row = self._grid_row(particulars)
        cells = {column: row.locator(f'[col-id="{col_id}"]') for column, col_id in FIGURE_COLUMNS.items()}
        return {
            column: parse_amount(cell.inner_text() or "0") for column, cell in cells.items() if cell.count()
        }

    def set_period(self, period: ReportPeriod) -> None:
        self.submit_period(period)
        expect(self._period).to_contain_text(period.start, timeout=LOAD_TIMEOUT_MS)

    def submit_period(self, period: ReportPeriod) -> None:
        """Enters both dates in the Date Filter and presses OK, without waiting for the report to follow."""
        self.page.keyboard.press(DATE_FILTER_SHORTCUT)
        self._fill_date(self._date_input("fromDateFilter"), period.start)
        self._fill_date(self._date_input("toDateFilter"), period.end)
        self.page.locator("#btn-Ok").click()

    def _date_input(self, field_id: str) -> Locator:
        # The app gives the input and its calendar toggle the same id; `input` picks the one to type in.
        return self.page.locator(f"input#{field_id}")

    def expect_export_buttons(self, button_ids: tuple[str, ...]) -> None:
        for button_id in button_ids:
            expect(self.page.locator(f'[id="{button_id}"]')).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def export_excel(self) -> Download:
        with self.page.expect_download(timeout=EXPORT_TIMEOUT_MS) as download_info:
            self._excel_export.click()
        return download_info.value

    def export_pdf(self) -> Download:
        with self.page.expect_download(timeout=EXPORT_TIMEOUT_MS) as download_info:
            self.page.get_by_role("link", name="PDF").click()
        return download_info.value

    def open_iff_dialog(self) -> None:
        self.page.locator('[id="btn-IFF"]').click()
        expect(self._iff_dialog).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def expect_iff_choices(self, return_types: tuple[str, ...], months: tuple[str, ...]) -> None:
        expect(self._iff_dialog.locator("select#returnType option")).to_have_text(list(return_types))
        expect(self._iff_dialog.locator("select#filterType option")).to_have_text(list(months))

    def expect_iff_actions(self, actions: tuple[str, ...]) -> None:
        for action in actions:
            expect(self._iff_dialog.get_by_role("button", name=action)).to_be_visible()

    def downloaded_file(self, download: Download) -> Path:
        path = download.path()
        if path is None:
            raise FileNotFoundError(f"Download {download.suggested_filename} has no local file")
        return path

    @property
    def _period(self) -> Locator:
        return self.page.get_by_text(PERIOD).first

    @property
    def _iff_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text=IFF_DIALOG_TITLE)

    @property
    def _excel_export(self) -> Locator:
        return self.page.get_by_role("link", name="Excel")

    def _grid_row(self, particulars: str) -> Locator:
        cell = self.page.locator('[col-id="Particulars"]').get_by_text(particulars, exact=True)
        return self.page.locator(".ag-row").filter(has=cell).first

    @staticmethod
    def _fill_date(field: Locator, value: str) -> None:
        field.click()
        field.press("Control+A")
        field.press_sequentially(value)

    def _row(self, particulars: str) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.get_by_text(particulars, exact=True))

    def _column_index(self, header: str) -> int:
        headers = self.page.get_by_role("columnheader").all_inner_texts()
        return [" ".join(text.split()) for text in headers].index(header)
