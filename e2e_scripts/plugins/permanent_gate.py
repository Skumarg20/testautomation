"""Opt-in gate for tests that leave a change on QA that cannot be undone (e.g. creating an online store).

A test marked `pytest.mark.permanent("what it leaves behind")` is skipped unless the run passes
`--allow-permanent`, so a normal or CI run never makes such a change by accident.
"""

import pytest

OPTION = "--allow-permanent"
MARKER = "permanent"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        OPTION,
        action="store_true",
        default=False,
        help="also run tests marked `permanent`, which leave a change on QA that cannot be undone",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", f"{MARKER}(effect): leaves an irreversible change on QA; needs {OPTION}"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption(OPTION):
        return
    for item in items:
        marker = item.get_closest_marker(MARKER)
        if marker:
            item.add_marker(pytest.mark.skip(reason=_skip_reason(marker)))


def _skip_reason(marker: pytest.Mark) -> str:
    effect = marker.args[0] if marker.args else "an irreversible change"
    return f"leaves {effect} on QA; run with {OPTION} to include it"
