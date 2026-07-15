from unittest.mock import Mock, patch

from app import config as config_module
from app.skills.errors import (
    SkillError,
    SkillHTTPError,
    SkillInvalidPayloadError,
    SkillInvalidResponseError,
)
from app.skills.reddit_skill import RedditSkill


def _token_response(token: str = "tok-1", expires_in: int = 3600) -> Mock:
    resp = Mock()
    resp.json.return_value = {"access_token": token, "expires_in": expires_in, "token_type": "bearer"}
    return resp


def _search_response(posts: list, after: str | None = None) -> Mock:
    resp = Mock()
    resp.json.return_value = {"data": {"children": [{"kind": "t3", "data": p} for p in posts], "after": after}}
    return resp


def _post(title: str = "hi", selftext: str = "body", score: int = 10, num_comments: int = 2) -> dict:
    return {"title": title, "selftext": selftext, "score": score, "num_comments": num_comments}


config_module.settings.reddit_client_id = "id"
config_module.settings.reddit_client_secret = "secret"


# --- missing/invalid payload rejected before any HTTP call ---
skill = RedditSkill()
with patch("app.skills.reddit_skill.http_request") as mock_request:
    try:
        skill.run("sentiment_scan", {"subreddit": "all", "keywords": []})
        raise AssertionError("expected SkillInvalidPayloadError")
    except SkillInvalidPayloadError:
        pass

    try:
        skill.run("unsupported_query_type", {"subreddit": "all", "keywords": ["x"]})
        raise AssertionError("expected SkillInvalidPayloadError")
    except SkillInvalidPayloadError:
        pass

    assert mock_request.call_count == 0


# --- missing credentials rejected before any HTTP call ---
skill = RedditSkill()
original_id = config_module.settings.reddit_client_id
original_secret = config_module.settings.reddit_client_secret
config_module.settings.reddit_client_id = None
config_module.settings.reddit_client_secret = None
try:
    with patch("app.skills.reddit_skill.http_request") as mock_request:
        try:
            skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["protein coffee"]})
            raise AssertionError("expected SkillError")
        except SkillError:
            pass
        assert mock_request.call_count == 0
finally:
    config_module.settings.reddit_client_id = original_id
    config_module.settings.reddit_client_secret = original_secret


# --- successful single-page search maps into the raw-signal contract ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[
        _token_response(),
        _search_response(
            [_post(title="A", score=10, num_comments=1), _post(title="B", score=20, num_comments=3)]
        ),
    ],
) as mock_request:
    result = skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["protein coffee"]})
    assert result["status"] == "ok"
    assert result["skill"] == "reddit"
    data = result["data"]
    assert data["mentions"] == 2
    assert data["avg_score"] == 15.0
    assert data["avg_comments"] == 2.0
    assert [p["title"] for p in data["posts"]] == ["A", "B"]
    assert mock_request.call_count == 2  # one token fetch, one search page

print("sample result:", result)


# --- the cached token is reused on a second call, no re-fetch ---
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[_search_response([_post()])],
) as mock_request:
    result = skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["protein coffee"]})
    assert result["data"]["mentions"] == 1
    assert mock_request.call_count == 1


# --- pagination follows `after` up to the page cap and aggregates results ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[
        _token_response(),
        _search_response([_post(title="p1")], after="cursor_1"),
        _search_response([_post(title="p2")], after=None),
    ],
) as mock_request:
    result = skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["x"]})
    assert result["data"]["mentions"] == 2
    assert mock_request.call_count == 3


# --- a 401 mid-session triggers one token refresh + retry, then succeeds ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[
        _token_response(token="tok-1"),
        SkillHTTPError("expired", status_code=401, retryable=False),
        _token_response(token="tok-2"),
        _search_response([_post()]),
    ],
) as mock_request:
    result = skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["x"]})
    assert result["status"] == "ok"
    assert mock_request.call_count == 4


# --- a 401 that persists even after reauth propagates as non-retryable ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[
        _token_response(),
        SkillHTTPError("expired", status_code=401, retryable=False),
        _token_response(),
        SkillHTTPError("still unauthorized", status_code=401, retryable=False),
    ],
):
    try:
        skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["x"]})
        raise AssertionError("expected SkillHTTPError")
    except SkillHTTPError as exc:
        assert exc.status_code == 401
        assert exc.retryable is False


# --- a malformed token response raises SkillInvalidResponseError ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[Mock(json=Mock(return_value={"token_type": "bearer"}))],
):
    try:
        skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["x"]})
        raise AssertionError("expected SkillInvalidResponseError")
    except SkillInvalidResponseError:
        pass


# --- a malformed search response raises SkillInvalidResponseError ---
skill = RedditSkill()
with patch(
    "app.skills.reddit_skill.http_request",
    side_effect=[_token_response(), Mock(json=Mock(return_value={"unexpected": "shape"}))],
):
    try:
        skill.run("sentiment_scan", {"subreddit": "all", "keywords": ["x"]})
        raise AssertionError("expected SkillInvalidResponseError")
    except SkillInvalidResponseError:
        pass

print("OK")
