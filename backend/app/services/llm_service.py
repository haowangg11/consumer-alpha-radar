from app.models.router import ModelRouter, ModelType
from app.providers.openai_provider import OpenAIProvider
from app.providers.deepseek_provider import DeepSeekProvider
from app.providers.qwen_provider import QwenProvider


class LLMService:
    """
    Single entry point agents use to reach a model.
    Delegates model *selection* to ModelRouter and execution
    to a Model Provider. Agents must never call a provider directly.
    """

    def __init__(self, router: ModelRouter = None, providers: dict = None):
        self.router = router or ModelRouter()
        self.providers = providers or {
            ModelType.GPT: OpenAIProvider(),
            ModelType.DEEPSEEK: DeepSeekProvider(),
            ModelType.QWEN: QwenProvider(),
        }

    def run(self, task_type: str, payload: dict) -> dict:
        model = self.router.select_model(task_type)
        provider = self.providers[model]
        return provider.generate(task_type=task_type, payload=payload)
