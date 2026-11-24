"""Environment settings, validated at import time. QA/staging/local hosts only, never production.

Test Studio mode (STUDIO_QA_GUARD=1, set only by Test Studio when it runs a script): the scripts run against the
environment chosen in Test Studio's Settings, which may be a production host. That is allowed only together with
the Studio QA guard (fixtures/studio_guard.py): every request that saves, changes or deletes data is refused
unless it is made inside one of the QA test companies, so real companies stay read-only.
"""

import json
import os
import re
from pathlib import Path
from typing import Literal, NamedTuple
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TradeAccount = Literal["chemist", "pharma", "retail", "grocery", "garments"]
Role = Literal["admin", "operator", "accountant"]
Account = TradeAccount | Role
ACCOUNTS: tuple[TradeAccount, ...] = ("chemist", "pharma", "retail", "grocery", "garments")
ROLE_ACCOUNTS: tuple[Role, ...] = ("admin", "operator", "accountant")
LoginStyle = Literal["single_step", "two_step"]

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"  # found from any working directory

_NON_PRODUCTION_HOST = re.compile(
    r"(localhost|127\.0\.0\.1|\bqa\b|staging|\btest\b|\bdev\b|\.internal|(?:^|\.)pre[a-z]*margbooks)", re.I
)

# Second check, required in addition to the pattern above (F09 6.4): the pattern alone accepts lookalikes
# such as qa.evil.com. An entry is an exact hostname, or `*.suffix` for any host ending in `.suffix`.
# Adding a host is a code change reviewed in a PR. console/api/app/services/hostguard.py mirrors this tuple.
ALLOWED_TARGET_HOSTS: tuple[str, ...] = (
    "localhost",
    "127.0.0.1",
    "premargbooks.com",
    "*.premargbooks.com",
)


STUDIO_QA_GUARD = os.environ.get("STUDIO_QA_GUARD") == "1"
# Hosts of the environment chosen in Test Studio; accepted only while the Studio QA guard is on.
STUDIO_TARGET_HOSTS: tuple[str, ...] = tuple(
    h.strip().lower() for h in os.environ.get("STUDIO_TARGET_HOSTS", "").split(",") if h.strip() and STUDIO_QA_GUARD
)
# complinkid of every QA test company: the only companies the guard lets a script write in.
STUDIO_QA_COMPLINKIDS: frozenset[str] = frozenset(
    x.strip() for x in os.environ.get("STUDIO_QA_COMPLINKIDS", "").split(",") if x.strip() and STUDIO_QA_GUARD
)
# The companies the scripts were written for, mapped to QA test companies ({"Pharma New Company 23-09": "QA Chemist"}).
STUDIO_COMPANY_MAP: dict[str, str] = (
    json.loads(os.environ.get("STUDIO_COMPANY_MAP") or "{}") if STUDIO_QA_GUARD else {}
)
STUDIO_DEFAULT_COMPANY = os.environ.get("STUDIO_DEFAULT_COMPANY", "") if STUDIO_QA_GUARD else ""


def studio_company(name: str) -> str:
    """The QA test company a script's company stands for in Test Studio mode (the name itself otherwise)."""
    return STUDIO_COMPANY_MAP.get(name, name)


def _hostname_of(url: str) -> str:
    """Lower-case hostname with one trailing dot removed; empty when the URL carries credentials."""
    parts = urlparse(url)
    if "@" in parts.netloc or "\\" in url or any(ch.isspace() for ch in url):
        return ""
    host = (parts.hostname or "").lower()
    return host[:-1] if host.endswith(".") else host


def is_allowed_target(url: str) -> bool:
    """True only when the hostname passes the non-production pattern AND the explicit allowlist."""
    host = _hostname_of(url)
    if host and host in STUDIO_TARGET_HOSTS:          # only with the Studio QA guard on (see the module docstring)
        return True
    if not host or not _NON_PRODUCTION_HOST.search(host):
        return False
    for entry in ALLOWED_TARGET_HOSTS:
        if entry.startswith("*."):
            if host.endswith(entry[1:]) and len(host) > len(entry) - 1:
                return True
        elif host == entry:
            return True
    return False


class Credentials(NamedTuple):
    user: str
    password: str


def worker_index(worker_id: str) -> int:
    """xdist names workers gw0, gw1, ...; a run without xdist is "master"."""
    digits = re.sub(r"\D", "", worker_id)
    return int(digits) if digits else 0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    margbooks_qa_url: str = "http://localhost:4200"
    margbooks_login_url: str | None = None
    margbooks_api_url: str | None = None
    login_style: LoginStyle = "single_step"
    # QA_RECORD=1 saves a video and a final screenshot of every test under results/recordings/
    qa_record: bool = False
    # QA_REQUIRE_CREDENTIALS=1 (CI) fails a test whose account has no credentials instead of skipping it
    qa_require_credentials: bool = False
    qa_chemist_user: str | None = None
    qa_chemist_pass: str | None = None
    qa_pharma_user: str | None = None
    qa_pharma_pass: str | None = None
    qa_retail_user: str | None = None
    qa_retail_pass: str | None = None
    qa_grocery_user: str | None = None
    qa_grocery_pass: str | None = None
    qa_garments_user: str | None = None
    qa_garments_pass: str | None = None
    # The same garments account signs in with its mobile number and its e-mail; this is the other one.
    qa_garments_alt_user: str | None = None
    qa_admin_user: str | None = None
    qa_admin_pass: str | None = None
    qa_operator_user: str | None = None
    qa_operator_pass: str | None = None
    qa_accountant_user: str | None = None
    qa_accountant_pass: str | None = None
    # Parallel runs: one login per worker, e.g. QA_POOL={"chemist": [["user1", "pass1"], ["user2", "pass2"]]}
    qa_pool: dict[str, list[tuple[str, str]]] = {}

    @field_validator("margbooks_qa_url", "margbooks_login_url", "margbooks_api_url")
    @classmethod
    def _reject_production_hosts(cls, url: str | None) -> str | None:
        if url is None:
            return url
        if not is_allowed_target(url):
            raise ValueError(
                "The QA, login and API URLs must be an allowed non-production host "
                "(config.settings.ALLOWED_TARGET_HOSTS), never production"
            )
        return url

    @field_validator("margbooks_api_url", "margbooks_login_url", mode="before")
    @classmethod
    def _blank_means_unset(cls, url: str | None) -> str | None:
        return url or None

    @property
    def login_url(self) -> str:
        return self.margbooks_login_url or f"{self.margbooks_qa_url}/login"

    @property
    def api_base_url(self) -> str:
        return self.margbooks_api_url or self.margbooks_qa_url

    def credentials(self, account: Account, worker_index: int = 0) -> Credentials | None:
        pool = self.qa_pool.get(account)
        if pool:
            return Credentials(*pool[worker_index % len(pool)])
        user = getattr(self, f"qa_{account}_user")
        password = getattr(self, f"qa_{account}_pass")
        return Credentials(user, password) if user and password else None

    def garments_alternate_credentials(self) -> Credentials | None:
        if not (self.qa_garments_alt_user and self.qa_garments_pass):
            return None
        return Credentials(self.qa_garments_alt_user, self.qa_garments_pass)


settings = Settings()
