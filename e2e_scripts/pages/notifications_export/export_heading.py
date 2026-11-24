"""The heading block above the table in an exported ".xls" (an HTML file): company (h1), address (h2),
report title (h3) and period (p, "dd-mm-yyyy To dd-mm-yyyy"), as seen in the live exports of 2026-10-12."""

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

HEADING_TAGS = ("h1", "h3", "p")


@dataclass(frozen=True)
class ExportHeading:
    company: str
    title: str
    period: str


class _HeadingReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.texts: dict[str, str] = {}
        self._current: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in HEADING_TAGS and tag not in self.texts:
            self._current = tag
            self.texts[tag] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == self._current:
            self._current = None

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self.texts[self._current] += data


def read_heading(path: Path) -> ExportHeading:
    reader = _HeadingReader()
    reader.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = {tag: " ".join(reader.texts.get(tag, "").split()) for tag in HEADING_TAGS}
    return ExportHeading(company=text["h1"], title=text["h3"], period=text["p"])
