"""Test Studio QA guard: real companies stay read-only when Test Studio runs a script on its own environment."""

import importlib
import subprocess
import sys

import pytest

GATEWAY = "https://gateway6.margbooks.com"
QA_CHEMIST = "7145375269391"
REAL_COMPANY = "7145263462142"


@pytest.fixture
def guard(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    from fixtures import studio_guard

    monkeypatch.setattr(studio_guard, "STUDIO_QA_COMPLINKIDS", frozenset({QA_CHEMIST}))
    return studio_guard


@pytest.mark.parametrize(
    ("method", "path", "company", "refused"),
    [
        ("POST", "/greet.S/CallGrpcSaveSaleBill", REAL_COMPANY, True),
        ("POST", "/greet.S/CallGrpcSaveSaleBill", QA_CHEMIST, False),
        ("POST", "/greet.S/CallGrpcGetDoctorList", REAL_COMPANY, False),
        ("POST", "/v4.2/DashBoard/NEWLYADDEDASHBOARD", REAL_COMPANY, False),
        ("DELETE", "/v4.2/Ledger/9", REAL_COMPANY, True),
        ("POST", "/v4.2/Item/UpdateItem", REAL_COMPANY, True),
        ("POST", "/v4.2/ControlRoom/SaveProfile", QA_CHEMIST, True),
        ("POST", "/v4.2/Company/UpdateCompanyProfileAndUser", REAL_COMPANY, False),
        ("POST", "/v4.2/TempBillHold/Delete", REAL_COMPANY, False),
        ("POST", "/v4.2/Company/List", "", False),
    ],
)
def test_writes_go_out_only_in_qa_companies(guard, method: str, path: str, company: str, refused: bool) -> None:  # type: ignore[no-untyped-def]
    assert bool(guard.refusal(method, GATEWAY + path, {"complinkid": company})) is refused


def test_base64_company_header_is_read(guard) -> None:  # type: ignore[no-untyped-def]
    assert guard.company_id("NzE0NTM3NTI2OTM5MQ==") == QA_CHEMIST
    assert guard.company_id(QA_CHEMIST) == QA_CHEMIST
    assert not guard.refusal("POST", GATEWAY + "/v4.2/Item/Save", {"complinkid": "NzE0NTM3NTI2OTM5MQ=="})


def _settings_in_a_new_process(env: dict[str, str], code: str) -> str:
    """config.settings reads the environment once at import: check it in a fresh interpreter."""
    import os

    result = subprocess.run(
        [sys.executable, "-c", code], env={**os.environ, **env}, capture_output=True, text=True, check=False
    )
    return (result.stdout + result.stderr).strip()


def test_production_host_needs_the_studio_guard() -> None:
    check = "from config.settings import is_allowed_target as a; print(a('https://books6.margbooks.com'))"
    assert _settings_in_a_new_process({"STUDIO_QA_GUARD": "", "STUDIO_TARGET_HOSTS": "books6.margbooks.com"}, check) \
        .endswith("False")
    assert _settings_in_a_new_process({"STUDIO_QA_GUARD": "1", "STUDIO_TARGET_HOSTS": "books6.margbooks.com"}, check) \
        .endswith("True")


def test_company_map_applies_only_in_studio_mode() -> None:
    code = "from config.settings import studio_company as s; print(s('Pharma New Company 23-09'))"
    mapping = '{"Pharma New Company 23-09": "QA Chemist"}'
    assert _settings_in_a_new_process({"STUDIO_QA_GUARD": "1", "STUDIO_COMPANY_MAP": mapping}, code).endswith("QA Chemist")
    assert _settings_in_a_new_process({"STUDIO_QA_GUARD": "", "STUDIO_COMPANY_MAP": mapping}, code) \
        .endswith("Pharma New Company 23-09")


def test_guard_module_is_inert_without_studio() -> None:
    importlib.import_module("fixtures.studio_guard")
    code = "from fixtures import studio_guard as g; print(g.STUDIO_QA_GUARD)"
    assert _settings_in_a_new_process({"STUDIO_QA_GUARD": ""}, code).endswith("False")
