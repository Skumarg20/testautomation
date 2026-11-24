"""Reads a downloaded GST report. The app's ".xls" is an HTML table, so it is parsed as HTML."""

from dataclasses import dataclass
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from test_data.money import parse_amount

CELL_TAGS = ("td", "th")


class ExportRowNotFoundError(LookupError):
    def __init__(self, particulars: str) -> None:
        super().__init__(f'The exported report has no row "{particulars}"')


class ExportColumnNotFoundError(LookupError):
    def __init__(self, column: str, header: tuple[str, ...]) -> None:
        super().__init__(f'The exported report has no column "{column}"; header is {header}')


@dataclass(frozen=True)
class ExportedReport:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def figure(self, particulars: str, column: str) -> Decimal:
        """The amount in `column` of the first row whose Particulars equal `particulars`."""
        if column not in self.header:
            raise ExportColumnNotFoundError(column, self.header)
        row = self._row(particulars)
        return parse_amount(row[self.header.index(column)] or "0")

    def has_row(self, particulars: str) -> bool:
        return any(row[0] == particulars for row in self.rows)

    def _row(self, particulars: str) -> tuple[str, ...]:
        for row in self.rows:
            if row[0] == particulars:
                return row
        raise ExportRowNotFoundError(particulars)


class _TableReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.rows.append([])
        elif tag in CELL_TAGS and self.rows:
            self.rows[-1].append("")
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        if tag in CELL_TAGS:
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self.rows[-1][-1] += data


def read_export(path: Path) -> ExportedReport:
    reader = _TableReader()
    reader.feed(path.read_text(encoding="utf-8", errors="replace"))
    cleaned = [tuple(" ".join(cell.split()) for cell in row) for row in reader.rows if any(row)]
    header, *rows = (row for row in cleaned if len(row) > 1)
    return ExportedReport(header=header, rows=tuple(rows))
