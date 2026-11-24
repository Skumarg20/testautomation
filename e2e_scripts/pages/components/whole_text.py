"""A regex that matches a cell's whole text, so "Cash" does not match "Cash Account"."""

import re


def whole_text(text: str, *, ignore_case: bool = False) -> re.Pattern[str]:
    """Any run of whitespace, &nbsp; included, may sit between the words.

    Playwright normalises whitespace for a string matcher but not for a regex, and the grids show
    multi-word names with non-breaking spaces.
    """
    words = r"\s+".join(re.escape(word) for word in text.split())
    return re.compile(rf"^\s*{words}\s*$", re.IGNORECASE if ignore_case else 0)
