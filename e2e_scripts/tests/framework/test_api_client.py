import httpx
import pytest

from fixtures.api_client import MAX_ATTEMPTS, ApiClient, ThrottledError

pytestmark = pytest.mark.framework


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fixtures.api_client.time.sleep", lambda _seconds: None)


def client_answering(*status_codes: int) -> tuple[ApiClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    remaining = list(status_codes)

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return httpx.Response(status, json={"ok": True})

    return ApiClient("https://qa.example.com", "run", httpx.MockTransport(respond)), requests


def test_get_returns_decoded_json() -> None:
    client, _ = client_answering(200)

    assert client.get("/ping") == {"ok": True}


def test_throttled_request_is_retried_until_it_succeeds() -> None:
    client, requests = client_answering(429, 503, 200)

    assert client.get("/ping") == {"ok": True}
    assert len(requests) == 3


def test_persistent_throttling_raises_a_descriptive_error() -> None:
    client, requests = client_answering(429)

    with pytest.raises(ThrottledError, match="GET /ping"):
        client.get("/ping")

    assert len(requests) == MAX_ATTEMPTS


def test_client_errors_are_not_retried() -> None:
    client, requests = client_answering(404)

    with pytest.raises(httpx.HTTPStatusError):
        client.get("/missing")

    assert len(requests) == 1
