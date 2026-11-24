"""The DataSync service's request endpoints, called directly (J35 DS-19, DS-31, DS-44..DS-46).

Host: `environment.preprod.ts:50` `DataSync` + `v1.1/` (`global.ts:18270`), the same host the web app calls
for the Data Sync screen. The controller has no `[Authorize]` and reads no session for these actions
(`MargERP.Margbook.OnlineofflineDataSync.Service.API/Controllers/OfflineOnlineController.cs:39-75`,
`:276-323`), so the calls need no login. The answers carry their own status code in the body (HTTP 200).
None of these calls sends anything to a person; `SyncRequestsave` with real ids writes a request row, so
only the throwaway company's ids are ever passed to it with a non-zero id pair.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from config.settings import is_allowed_target
from fixtures.api_client import ApiClient
from pages.data_sync.sync_status_stub import CompanyKeys

DATA_SYNC_API = "https://onlineofflinesyncservices.premargbooks.com/v1.1/"
O2DM_VALIDATE = "OfflineOnline/UservalidateforO2DM"
REQUEST_SAVE = "OfflineOnline/SyncRequestsave"
REQUEST_STATUS = "OfflineOnline/SyncRequeststatus"


class ProductionHostError(RuntimeError):
    def __init__(self, url: str) -> None:
        super().__init__(f"{url} is not an allowed non-production host (CLAUDE.md rule 4)")


@dataclass(frozen=True)
class SyncAnswer:
    """The body of an answer, read without caring for the key case (`statuscode` / `StatusCode`)."""

    body: dict[str, Any]

    @property
    def status_code(self) -> int:
        return int(str(self._value("statuscode")))

    @property
    def message(self) -> str:
        return str(self._value("message") or "")

    @property
    def data(self) -> object:
        return self._value("data")

    def _value(self, key: str) -> object:
        return next((value for name, value in self.body.items() if name.lower() == key), None)


def data_sync_client(run_id: str) -> ApiClient:
    if not is_allowed_target(DATA_SYNC_API):
        raise ProductionHostError(DATA_SYNC_API)
    return ApiClient(DATA_SYNC_API, run_id)


class SyncRequestApi:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    def validate_o2dm_user(self, email: str, branch_code: str) -> SyncAnswer:
        body = {"emailid": email, "branchcode": branch_code, "paswwrod": "not-used"}
        return self._post(O2DM_VALIDATE, body)

    def save_request(self, company: CompanyKeys, status: int) -> SyncAnswer:
        body = {"complinkid": company.complinkid, "dbinfolinkid": company.dbinfolinkid, "status": status}
        return self._post(REQUEST_SAVE, body)

    def request_status(self, company: CompanyKeys) -> SyncAnswer:
        body = {"complinkid": company.complinkid, "dbinfolinkid": company.dbinfolinkid}
        return self._post(REQUEST_STATUS, body)

    def _post(self, path: str, body: Mapping[str, object]) -> SyncAnswer:
        answer = self._client.post(path, body)
        if not isinstance(answer, dict):
            raise TypeError(f"{path} answered {answer!r}, expected a JSON object")
        return SyncAnswer(answer)
