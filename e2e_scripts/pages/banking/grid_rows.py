"""Rows of the read-only ag-Grid reports (bank reconciliation, ledger report), picked and read by col-id."""

import re

from playwright.sync_api import Locator, Page

# The list headers carry col-id on the columnheader itself, on a wrapper or on an inner element.
COLUMN_ID_SCRIPT = """
header => (header.closest('[col-id]') || header.querySelector('[col-id]'))?.getAttribute('col-id') ?? null
"""


class GridRows:
    def __init__(self, page: Page) -> None:
        self._page = page

    def where(self, column: str, text: str | re.Pattern[str]) -> Locator:
        """Body rows whose `column` cell contains `text`; the report pads its grid with blank rows."""
        # Why CSS: ag-Grid exposes only row-id and col-id; the screens have no test ids.
        rows = self._page.locator('[ref="eBodyContainer"] [row-id]')
        return rows.filter(has=self._page.locator(f'[col-id="{column}"]', has_text=text))

    def read_by_header(self, row: Locator) -> dict[str, str]:
        """The row's cells keyed by their column header text. Cells are matched to headers by col-id, not
        by position: ag-Grid keeps neither DOM order nor pinned columns in one container, and the page may
        hold headers of other grids or blank ones (a selection column)."""
        cells: dict[str, str] = {}
        for header in self._page.get_by_role("columnheader").all():
            name = header.inner_text().strip()
            cell = row.locator(f'[col-id="{header.evaluate(COLUMN_ID_SCRIPT)}"]')
            if name and cell.count():
                cells[name] = cell.first.inner_text().strip()
        return cells

    @staticmethod
    def read(row: Locator, columns: tuple[str, ...]) -> dict[str, str]:
        return {column: row.locator(f'[col-id="{column}"]').inner_text().strip() for column in columns}
