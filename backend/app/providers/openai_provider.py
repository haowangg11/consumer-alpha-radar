from app.providers.base import ModelProvider


class OpenAIProvider(ModelProvider):
    """
    Placeholder for the OpenAI (GPT) backend. No API key or HTTP
    call is wired in yet - generate() returns a structured stub so
    the pipeline stays runnable before real integration lands.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate(self, task_type: str, payload: dict) -> dict:
        return {
            "provider": "openai",
            "status": "not_implemented",
            "detail": "OpenAI (GPT) provider is a placeholder - no real API call has been wired in yet.",
        }
