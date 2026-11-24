"""The phase-1 case importer never exports a credential-like column (the source workbooks hold logins)."""

import pytest

from scripts.import_document_cases import _without_secrets

pytestmark = pytest.mark.framework


@pytest.mark.parametrize(
    "column",
    ["password", "Password", "user_password", "pwd", "email", "login_email", "E-mail", "otp", "token",
     "api_secret", "username", "user_id", "login"],
)  # fmt: skip
def test_credential_like_columns_are_dropped(column: str) -> None:
    assert _without_secrets({column: "x", "party_name": "Cash"}) == {"party_name": "Cash"}


@pytest.mark.parametrize("column", ["party_name", "mobile", "patient_mobile", "product_qty", "referral_code"])
def test_case_input_columns_are_kept(column: str) -> None:
    assert _without_secrets({column: "1"}) == {column: "1"}
