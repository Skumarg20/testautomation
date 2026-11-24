from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from config.settings import ACCOUNTS, ROLE_ACCOUNTS, Credentials, Settings

pytestmark = pytest.mark.framework


class SettingsWithoutEnvFile(Settings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")


def build_settings(**overrides: Any) -> Settings:
    """Validates only the given values: neither the real environment nor a local .env file leaks in."""
    return SettingsWithoutEnvFile(**overrides)


@pytest.mark.parametrize(
    "url", ["https://app.margbooks.com", "https://margbooks.in/login", "https://accounts.margbooks.com/login"]
)
def test_production_like_hosts_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        build_settings(margbooks_qa_url=url)


@pytest.mark.parametrize(
    "url", ["https://accounts.premargbooks.com", "http://localhost:4200", "http://127.0.0.1:4200"]
)
def test_qa_staging_and_local_hosts_are_accepted(url: str) -> None:
    assert build_settings(margbooks_qa_url=url).margbooks_qa_url == url


def test_credentials_are_returned_only_when_user_and_password_are_both_set() -> None:
    settings = build_settings(qa_chemist_user="a@x.com", qa_chemist_pass="pw", qa_pharma_user="o@x.com")

    assert settings.credentials("chemist") == Credentials("a@x.com", "pw")
    assert settings.credentials("pharma") is None
    assert settings.credentials("retail") is None


def test_api_base_url_falls_back_to_the_ui_url_when_blank() -> None:
    settings = build_settings(margbooks_qa_url="https://accounts.premargbooks.com", margbooks_api_url="")

    assert settings.api_base_url == "https://accounts.premargbooks.com"


@pytest.mark.parametrize("url", ["https://premargbooks.com", "https://accounts.premargbooks.com/login"])
def test_premargbooks_hosts_are_accepted(url: str) -> None:
    assert build_settings(margbooks_qa_url=url, margbooks_login_url=url).margbooks_login_url == url


def test_garments_is_a_trade_account_after_the_existing_ones() -> None:
    assert ACCOUNTS == ("chemist", "pharma", "retail", "grocery", "garments")


def test_garments_credentials_come_from_the_garments_variables() -> None:
    settings = build_settings(qa_garments_user="g@x.com", qa_garments_pass="pw")

    assert settings.credentials("garments") == Credentials("g@x.com", "pw")


def test_garments_alternate_login_uses_the_garments_password() -> None:
    settings = build_settings(qa_garments_user="g@x.com", qa_garments_pass="pw", qa_garments_alt_user="9999")

    assert settings.garments_alternate_credentials() == Credentials("9999", "pw")


def test_garments_alternate_login_is_absent_without_its_user() -> None:
    settings = build_settings(qa_garments_user="g@x.com", qa_garments_pass="pw")

    assert settings.garments_alternate_credentials() is None


@pytest.mark.parametrize("role", ROLE_ACCOUNTS)
def test_each_role_resolves_its_own_credentials(role: str) -> None:
    settings = build_settings(**{f"qa_{role}_user": f"{role}@x.com", f"qa_{role}_pass": "pw"})

    assert settings.credentials(role) == Credentials(f"{role}@x.com", "pw")  # type: ignore[arg-type]


def test_roles_are_not_trade_accounts() -> None:
    assert set(ROLE_ACCOUNTS).isdisjoint(ACCOUNTS)


def test_role_with_only_a_user_has_no_credentials() -> None:
    assert build_settings(qa_admin_user="a@x.com").credentials("admin") is None


def test_login_url_defaults_to_the_app_host_and_can_be_a_separate_login_host() -> None:
    same_host = build_settings(margbooks_qa_url="https://premargbooks.com")
    separate = build_settings(
        margbooks_qa_url="https://premargbooks.com",
        margbooks_login_url="https://accounts.premargbooks.com/login",
    )

    assert same_host.login_url == "https://premargbooks.com/login"
    assert separate.login_url == "https://accounts.premargbooks.com/login"
