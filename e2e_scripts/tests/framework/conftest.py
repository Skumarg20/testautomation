"""Framework checks run offline: the real QA_*/MARGBOOKS_* environment (CI variables) never leaks in."""

import os

import pytest

from config.settings import Settings

SETTINGS_ENV_NAMES = {name.upper() for name in Settings.model_fields}
SETTINGS_ENV_PREFIXES = ("QA_", "MARGBOOKS_")


@pytest.fixture(autouse=True)
def _no_settings_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper() in SETTINGS_ENV_NAMES or name.upper().startswith(SETTINGS_ENV_PREFIXES):
            monkeypatch.delenv(name, raising=False)
