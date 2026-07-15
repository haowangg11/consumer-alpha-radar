from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """
    Common interface every LLM backend must implement.
    LLMService talks only to this interface, never to a
    specific provider's SDK or HTTP client directly.
    """

    @abstractmethod
    def generate(self, task_type: str, payload: dict) -> dict:
        ...
