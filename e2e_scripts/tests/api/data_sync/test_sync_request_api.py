"""J35 data-sync-offline: the DataSync service's request endpoints, called directly (DS-19 re-enable, DS-31,
DS-44, DS-45, DS-46).

Expected values from
`MargERP.Margbook.OnlineofflineDataSync.Service.API/Controllers/OfflineOnlineController.cs` and
`margerpdal/OfflineOnlineDataSync.cs`. The validation calls carry a zero id or a blank field and return
before any write. Only DS-45 writes (a request row on the throwaway company), so it is `permanent`. DRAFT:
written from the .NET source, not run against the service yet.
"""

import pytest

from pages.data_sync.sync_api import SyncAnswer, SyncRequestApi
from pages.data_sync.sync_status_stub import CompanyKeys, RequestStatus

pytestmark = [pytest.mark.api, pytest.mark.p3, pytest.mark.journey("data-sync-offline")]

REFUSED = 0
SAVED = 200
NO_REQUEST = 201
NOT_ALLOWED = 401
ENABLE = int(RequestStatus.PENDING.value)
QA_EMAIL = "qa.datasync@example.com"
# Ids no company has: the status query then finds no row (and a validation refuses before any write).
UNKNOWN_COMPANY = CompanyKeys(complinkid=0, dbinfolinkid=0)
SOME_COMPANY_ID = 1
SOME_DBINFO_ID = 1


def _current_status(sync_api: SyncRequestApi, company: CompanyKeys) -> str | None:
    answer = sync_api.request_status(company)
    if answer.status_code == NO_REQUEST:
        return None
    data = answer.data
    return str(data.get("status")) if isinstance(data, dict) else None


def _expect_refused(answer: SyncAnswer, message: str) -> None:
    assert (answer.status_code, answer.message) == (REFUSED, message), f"answered {answer.body}"


def test_o2dm_user_check_refuses_a_blank_branch_code(sync_api: SyncRequestApi) -> None:
    answer = sync_api.validate_o2dm_user(QA_EMAIL, branch_code="")

    _expect_refused(answer, "Invalid branchcode")


def test_request_save_refuses_a_zero_company_id(sync_api: SyncRequestApi) -> None:
    answer = sync_api.save_request(CompanyKeys(complinkid=0, dbinfolinkid=SOME_DBINFO_ID), ENABLE)

    # The source's text for a missing company id is "branchlinkid" (pack DS-44, D4 candidate).
    _expect_refused(answer, "branchlinkid")


def test_request_save_refuses_a_zero_dbinfo_id(sync_api: SyncRequestApi) -> None:
    answer = sync_api.save_request(CompanyKeys(complinkid=SOME_COMPANY_ID, dbinfolinkid=0), ENABLE)

    _expect_refused(answer, "Invalid DBInfolinkid")


def test_request_status_of_a_company_without_request_is_201_with_no_data(sync_api: SyncRequestApi) -> None:
    answer = sync_api.request_status(UNKNOWN_COMPANY)

    assert answer.status_code == NO_REQUEST, f"DS-46: answered {answer.body}"
    assert answer.data is None, f"DS-46: a company without a request got data {answer.data}"


def test_enabling_again_after_a_cancelled_request_is_refused(
    sync_api: SyncRequestApi, throwaway_keys: CompanyKeys
) -> None:
    if _current_status(sync_api, throwaway_keys) != RequestStatus.CANCELLED.value:
        pytest.skip("DS-19: needs the throwaway company's request cancelled (run DS-19 first)")

    answer = sync_api.save_request(throwaway_keys, ENABLE)

    assert (answer.status_code, answer.message) == (NOT_ALLOWED, "Invalid request"), f"answered {answer.body}"


@pytest.mark.permanent("a pending data sync request on the throwaway company")
def test_sending_the_same_request_twice_is_answered_already_requested(
    sync_api: SyncRequestApi, throwaway_keys: CompanyKeys
) -> None:
    if _current_status(sync_api, throwaway_keys) not in (None, RequestStatus.PENDING.value):
        pytest.skip("DS-45: needs the throwaway company with no request or a pending one")
    sync_api.save_request(throwaway_keys, ENABLE)

    answer = sync_api.save_request(throwaway_keys, ENABLE)

    assert (answer.status_code, answer.message) == (SAVED, "Already requested"), f"answered {answer.body}"
    assert _current_status(sync_api, throwaway_keys) == RequestStatus.PENDING.value
