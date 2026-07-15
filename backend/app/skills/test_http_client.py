from unittest.mock import Mock, patch

import requests

from app.skills import http_client
from app.skills.errors import SkillConnectionError, SkillHTTPError, SkillTimeoutError


def _response(status_code: int) -> Mock:
    resp = Mock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = status_code < 400
    return resp


# --- a clean 200 passes straight through, no retries needed ---
with patch("app.skills.http_client.requests.request", return_value=_response(200)) as mock_request:
    result = http_client.request("GET", "https://example.com/ok", max_retries=3)
    assert result.status_code == 200
    assert mock_request.call_count == 1


# --- a transient 503 is retried and succeeds on the second attempt ---
with patch(
    "app.skills.http_client.requests.request",
    side_effect=[_response(503), _response(200)],
) as mock_request:
    result = http_client.request("GET", "https://example.com/flaky", max_retries=3)
    assert result.status_code == 200
    assert mock_request.call_count == 2


# --- persistent 503s exhaust retries and raise a retryable SkillHTTPError ---
with patch(
    "app.skills.http_client.requests.request",
    return_value=_response(503),
) as mock_request:
    try:
        http_client.request("GET", "https://example.com/down", max_retries=3)
        raise AssertionError("expected SkillHTTPError")
    except SkillHTTPError as exc:
        assert exc.status_code == 503
        assert exc.retryable is True
    assert mock_request.call_count == 3


# --- a 404 is not retried and raises a non-retryable SkillHTTPError ---
with patch(
    "app.skills.http_client.requests.request",
    return_value=_response(404),
) as mock_request:
    try:
        http_client.request("GET", "https://example.com/missing", max_retries=3)
        raise AssertionError("expected SkillHTTPError")
    except SkillHTTPError as exc:
        assert exc.status_code == 404
        assert exc.retryable is False
    assert mock_request.call_count == 1


# --- a connection error that never recovers raises SkillConnectionError ---
with patch(
    "app.skills.http_client.requests.request",
    side_effect=requests.ConnectionError("refused"),
) as mock_request:
    try:
        http_client.request("GET", "https://example.com/unreachable", max_retries=2)
        raise AssertionError("expected SkillConnectionError")
    except SkillConnectionError as exc:
        assert exc.retryable is True
    assert mock_request.call_count == 2


# --- a request that always times out raises SkillTimeoutError ---
with patch(
    "app.skills.http_client.requests.request",
    side_effect=requests.Timeout("timed out"),
) as mock_request:
    try:
        http_client.request("GET", "https://example.com/slow", max_retries=2)
        raise AssertionError("expected SkillTimeoutError")
    except SkillTimeoutError as exc:
        assert exc.retryable is True
    assert mock_request.call_count == 2

print("OK")
