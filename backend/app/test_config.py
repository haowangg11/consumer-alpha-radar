import os

from app.config import Settings

# Defaults apply when no env vars are set.
defaults = Settings(_env_file=None)
assert defaults.google_trends_api_key is None
assert defaults.http_timeout_seconds == 10.0
assert defaults.http_max_retries == 3

# Env vars override defaults (this is how real API keys reach skills).
os.environ["GOOGLE_TRENDS_API_KEY"] = "test-key-123"
os.environ["HTTP_MAX_RETRIES"] = "5"
try:
    overridden = Settings(_env_file=None)
    assert overridden.google_trends_api_key == "test-key-123"
    assert overridden.http_max_retries == 5
finally:
    del os.environ["GOOGLE_TRENDS_API_KEY"]
    del os.environ["HTTP_MAX_RETRIES"]

print("OK")
