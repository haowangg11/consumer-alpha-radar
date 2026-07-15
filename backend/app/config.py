from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central source of secrets/config for external integrations
    (skills, model providers). Values load from environment
    variables first, falling back to a .env file in the backend
    directory - never hardcode a key in a Skill/Provider itself.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_trends_api_key: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str | None = None
    reddit_search_window: str = "week"
    stock_data_api_key: str | None = None

    http_timeout_seconds: float = 10.0
    http_max_retries: int = 3


settings = Settings()
