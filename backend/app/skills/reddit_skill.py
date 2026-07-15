import time

from app.config import settings
from app.skills.base import Skill
from app.skills.errors import (
    SkillError,
    SkillHTTPError,
    SkillInvalidPayloadError,
    SkillInvalidResponseError,
)
from app.skills.http_client import request as http_request
from app.skills.metadata import SkillMetadata
from app.skills.responses import success_response

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_API_BASE = "https://oauth.reddit.com"
_TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 60
_MAX_SEARCH_PAGES = 3
_PAGE_SIZE = 100
_MAX_SAMPLE_POSTS = 10


class RedditSkill(Skill):
    """
    Retrieves Reddit discussion volume for consumer keywords via
    Reddit's application-only OAuth2 (client_credentials) flow.

    Returns raw signal only (mention counts, engagement, post
    snippets) - interpreting sentiment/psychology from that signal
    is the Consumer Psychology Agent's job, not this skill's.
    """

    def __init__(self):
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="reddit",
            description="Retrieves discussion volume and engagement for consumer topics from Reddit.",
            version="0.2.0",
            input_schema={"subreddit": "str", "keywords": "list[str]"},
            output_schema={
                "mentions": "int",
                "avg_score": "float",
                "avg_comments": "float",
                "posts": "list[dict]",
            },
            tags=["social", "consumer-data", "trend-discovery", "consumer-psychology"],
        )

    def run(self, query_type: str, payload: dict) -> dict:
        if query_type != "sentiment_scan":
            raise SkillInvalidPayloadError(
                f"Reddit skill does not support query_type '{query_type}'"
            )

        subreddit = payload.get("subreddit")
        keywords = payload.get("keywords")
        if not subreddit or not keywords:
            raise SkillInvalidPayloadError(
                "Reddit skill requires a non-empty 'subreddit' and 'keywords' list"
            )

        data = self._search(subreddit, keywords)
        return success_response(skill="reddit", data=data)

    # --- authentication ---

    def _user_agent(self) -> str:
        return settings.reddit_user_agent or "consumer-alpha-radar:reddit-skill:0.2.0"

    def _get_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise SkillError(
                "Reddit skill is not configured: set REDDIT_CLIENT_ID and "
                "REDDIT_CLIENT_SECRET"
            )

        response = http_request(
            "POST",
            _TOKEN_URL,
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self._user_agent()},
        )
        try:
            body = response.json()
            access_token = body["access_token"]
            expires_in = body["expires_in"]
        except (ValueError, KeyError) as exc:
            raise SkillInvalidResponseError(
                f"Reddit token response missing expected fields: {exc}"
            ) from exc

        self._access_token = access_token
        self._token_expires_at = (
            time.time() + expires_in - _TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS
        )
        return access_token

    def _auth_headers(self, force_refresh: bool = False) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token(force_refresh=force_refresh)}",
            "User-Agent": self._user_agent(),
        }

    # --- search ---

    def _search(self, subreddit: str, keywords: list) -> dict:
        query = " ".join(keywords)
        posts = []
        after = None

        for _ in range(_MAX_SEARCH_PAGES):
            page_posts, after = self._search_page(subreddit, query, after)
            posts.extend(page_posts)
            if not after:
                break

        scores = [post.get("score", 0) for post in posts]
        comments = [post.get("num_comments", 0) for post in posts]
        return {
            "mentions": len(posts),
            "avg_score": (sum(scores) / len(scores)) if scores else 0.0,
            "avg_comments": (sum(comments) / len(comments)) if comments else 0.0,
            "posts": [
                {
                    "title": post.get("title", ""),
                    "snippet": post.get("selftext", "")[:280],
                    "score": post.get("score", 0),
                }
                for post in posts[:_MAX_SAMPLE_POSTS]
            ],
        }

    def _search_page(self, subreddit: str, query: str, after: str | None) -> tuple[list, str | None]:
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "new",
            "limit": _PAGE_SIZE,
            "t": settings.reddit_search_window,
        }
        if after:
            params["after"] = after

        url = f"{_API_BASE}/r/{subreddit}/search"
        try:
            response = http_request("GET", url, headers=self._auth_headers(), params=params)
        except SkillHTTPError as exc:
            if exc.status_code not in (401, 403):
                raise
            # Token may have expired or been revoked mid-session - refresh
            # once and retry this page before giving up.
            response = http_request(
                "GET", url, headers=self._auth_headers(force_refresh=True), params=params
            )

        try:
            body = response.json()
            children = body["data"]["children"]
            next_after = body["data"].get("after")
        except (ValueError, KeyError) as exc:
            raise SkillInvalidResponseError(
                f"Unexpected Reddit search response shape: {exc}"
            ) from exc

        return [child["data"] for child in children], next_after
