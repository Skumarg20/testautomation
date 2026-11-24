"""F09 6.4: a target host must pass the non-production pattern AND the explicit allowlist."""

from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from config.settings import ALLOWED_TARGET_HOSTS, Settings, is_allowed_target

pytestmark = pytest.mark.framework


class SettingsWithoutEnvFile(Settings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")


def build(**overrides: Any) -> Settings:
    return SettingsWithoutEnvFile(**overrides)


ALLOWED = [
    "http://localhost:4200",
    "http://127.0.0.1:4200/x",
    "https://premargbooks.com",
    "https://PreMargBooks.com/",
    "https://accounts.premargbooks.com/login",
    "https://a.b.premargbooks.com:8443",
    "https://premargbooks.com.",
]
BLOCKED = [
    "https://qa.evil.com",
    "https://margbooks-test.com",
    "https://localhost.evil.com",
    "https://margbooks.com.internal",
    "https://app.margbooks.com",
    "https://margbooks.com",
    "https://api.margbooks.com",
    "https://evilpremargbooks.com",
    "https://premargbooks.com.evil.com",
    "https://premargbooks.com@evil.com",
    "https://evil.com@premargbooks.com",
    "https://evil.com\\@premargbooks.com",
    "https://premargbooks.com\n.evil.com",
    "premargbooks.com",
    "",
]


@pytest.mark.parametrize("url", ALLOWED)
def test_allowlisted_hosts_pass(url: str) -> None:
    assert is_allowed_target(url)


@pytest.mark.parametrize("url", BLOCKED)
def test_lookalike_and_production_hosts_are_blocked(url: str) -> None:
    assert not is_allowed_target(url)


@pytest.mark.parametrize("field", ["margbooks_qa_url", "margbooks_login_url", "margbooks_api_url"])
def test_all_three_urls_are_checked_on_load(field: str) -> None:
    with pytest.raises(ValidationError):
        build(**{field: "https://qa.evil.com"})
    assert getattr(build(**{field: "https://accounts.premargbooks.com"}), field)


def test_api_url_production_host_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build(margbooks_api_url="https://api.margbooks.com")


def test_blank_api_url_still_means_unset() -> None:
    assert build(margbooks_api_url="").margbooks_api_url is None


def test_allowlist_entries_are_wildcards_on_a_label_boundary_or_exact() -> None:
    assert all(not entry.startswith("*") or entry.startswith("*.") for entry in ALLOWED_TARGET_HOSTS)
    assert "premargbooks.com" in ALLOWED_TARGET_HOSTS
