from abc import ABC, abstractmethod


class MemoryStore(ABC):
    """
    Common interface every memory backend must implement.
    Domain memories (TrendMemory, CompanyMemory, MarketMemory) talk
    only to this interface, never to a specific storage mechanism
    directly - mirrors how LLMService talks only to ModelProvider.

    Every record lives under a namespace so unrelated domains can
    share one store/file without key collisions.
    """

    @abstractmethod
    def set(self, namespace: str, key: str, value: dict) -> None:
        ...

    @abstractmethod
    def get(self, namespace: str, key: str) -> dict:
        ...

    @abstractmethod
    def query(self, namespace: str, **filters) -> list:
        ...
