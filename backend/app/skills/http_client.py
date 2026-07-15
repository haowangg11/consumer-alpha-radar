import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.skills.errors import SkillConnectionError, SkillHTTPError, SkillTimeoutError

# 429 (rate limited) and 5xx (server-side) are worth retrying; other
# non-2xx statuses (4xx) mean the request itself is wrong and won't
# succeed on a second attempt.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class _RetryableHTTPStatus(Exception):
    """Internal signal so tenacity retries on a retryable status code."""

    def __init__(self, response: requests.Response):
        self.response = response


def request(
    method: str,
    url: str,
    *,
    timeout: float | None = None,
    max_retries: int | None = None,
    **kwargs,
) -> requests.Response:
    """
    Shared synchronous HTTP entrypoint for all skills. Every skill
    should call this instead of `requests` directly, so timeout and
    retry policy stay in one place.

    - Applies a bounded timeout (default: settings.http_timeout_seconds).
    - Retries connection errors, timeouts, and 429/5xx responses with
      exponential backoff, up to max_retries attempts total.
    - Raises a SkillError subclass on final failure so callers never
      have to handle requests/urllib3 exceptions directly.
    """
    timeout = settings.http_timeout_seconds if timeout is None else timeout
    max_retries = settings.http_max_retries if max_retries is None else max_retries

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout, _RetryableHTTPStatus)
        ),
        reraise=True,
    )
    def _do_request() -> requests.Response:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise _RetryableHTTPStatus(response)
        return response

    try:
        response = _do_request()
    except requests.Timeout as exc:
        raise SkillTimeoutError(
            f"Request to {url} timed out after {max_retries} attempt(s)"
        ) from exc
    except requests.ConnectionError as exc:
        raise SkillConnectionError(
            f"Connection error requesting {url}: {exc}"
        ) from exc
    except _RetryableHTTPStatus as exc:
        raise SkillHTTPError(
            f"Request to {url} failed with status {exc.response.status_code} "
            f"after {max_retries} attempt(s)",
            status_code=exc.response.status_code,
            retryable=True,
        ) from exc

    if not response.ok:
        raise SkillHTTPError(
            f"Request to {url} failed with status {response.status_code}",
            status_code=response.status_code,
            retryable=False,
        )

    return response
