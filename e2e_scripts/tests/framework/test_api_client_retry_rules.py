"""ApiClient retries: never repeat a POST the server may have processed; no sleep after the last attempt."""

import httpx
import pytest

from fixtures.api_client import MAX_ATTEMPTS, ApiClient, ThrottledError

pytestmark = pytest.mark.framework


def client_answering(status: int, headers: dict[str, str] | None = None) -> tuple[ApiClient, list[str]]:
    methods: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(status, json={"ok": True}, headers=headers)

    return ApiClient("https://qa.example.com", "run", httpx.MockTransport(respond)), methods


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []
    monkeypatch.setattr("fixtures.api_client.time.sleep", recorded.append)
    return recorded


@pytest.mark.parametrize("status", [502, 503, 504])
def test_post_is_not_retried_on_a_gateway_error(status: int, sleeps: list[float]) -> None:
    client, methods = client_answering(status)

    with pytest.raises(httpx.HTTPStatusError):
        client.post("/vouchers", {"amount": "1.00"})

    assert methods == ["POST"]


def test_post_is_retried_on_429(sleeps: list[float]) -> None:
    client, methods = client_answering(429)

    with pytest.raises(ThrottledError):
        client.post("/vouchers", {})

    assert len(methods) == MAX_ATTEMPTS


def test_no_sleep_after_the_last_attempt(sleeps: list[float]) -> None:
    client, _ = client_answering(503)

    with pytest.raises(ThrottledError):
        client.get("/ping")

    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_retry_after_seconds_is_honoured(sleeps: list[float]) -> None:
    client, _ = client_answering(429, {"Retry-After": "3"})

    with pytest.raises(ThrottledError):
        client.get("/ping")

    assert sleeps == [3.0] * (MAX_ATTEMPTS - 1)
