"""Contract C3: API client with retry/backoff on throttling. Endpoints come from the OpenAPI spec."""

import time

import httpx

RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})
# A gateway error on a POST may come after the server saved the record: retrying would duplicate it.
NON_IDEMPOTENT_RETRYABLE_STATUSES = frozenset({429})
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 0.5
MAX_RETRY_AFTER_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 30


class ThrottledError(RuntimeError):
    def __init__(self, method: str, path: str, attempts: int) -> None:
        super().__init__(f"{method} {path}: still throttled or unavailable after {attempts} attempts")


class ApiClient:
    def __init__(self, base_url: str, run_id: str, transport: httpx.BaseTransport | None = None) -> None:
        self.run_id = run_id
        self._http = httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS, transport=transport)

    def get(self, path: str) -> object:
        return self._send_with_retry("GET", path)

    def post(self, path: str, body: object) -> object:
        return self._send_with_retry("POST", path, body)

    def cleanup(self) -> None:
        """No-op until the API's delete endpoints are known (PRD contract C3)."""

    def close(self) -> None:
        self._http.close()

    def _send_with_retry(self, method: str, path: str, body: object = None) -> object:
        retryable = RETRYABLE_STATUSES if method in IDEMPOTENT_METHODS else NON_IDEMPOTENT_RETRYABLE_STATUSES
        for attempt in range(MAX_ATTEMPTS):
            response = self._http.request(method, path, json=body)
            if response.status_code not in retryable:
                return self._decode(response)
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(_retry_delay(response, attempt))
        raise ThrottledError(method, path, MAX_ATTEMPTS)

    @staticmethod
    def _decode(response: httpx.Response) -> object:
        response.raise_for_status()
        return response.json() if response.content else None


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """The server's Retry-After (in seconds, capped) when it sends one, else exponential backoff."""
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return float(min(int(retry_after), MAX_RETRY_AFTER_SECONDS))
    return float(BACKOFF_BASE_SECONDS * 2**attempt)
