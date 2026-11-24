"""Test Studio live steps: readable step names, and no typed login or password ever shown."""

import pytest

from plugins import studio_live


@pytest.mark.parametrize(
    ("selector", "shown"),
    [
        ("internal:role=link[name=/^Sale( Sale)?$/] >> nth=0", 'link "Sale" (first)'),
        (r"internal:role=button[name=/^\s*Create\/F2\s*$/i] >> nth=0", 'button "Create/F2" (first)'),
        ('internal:role=button[name="Abha"s]', 'button "Abha"'),
        (":root", "the page"),
        ("input#password", "input#password"),
    ],
)
def test_selectors_read_like_words(selector: str, shown: str) -> None:
    assert studio_live._pretty(selector) == shown


def test_typed_secrets_are_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QA_CHEMIST_USER", "someone@example.com")
    assert studio_live._value("fill", "input#password", ("Secret#1",), {}) == "***"
    assert studio_live._value("fill", "#userid", ("someone@example.com",), {}) == "***"
    assert studio_live._value("fill", "#txtProduct", ("QA Item",), {}) == "QA Item"
    assert studio_live._value("click", "#btnSave", (), {}) == ""
