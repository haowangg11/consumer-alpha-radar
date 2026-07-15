from abc import ABC, abstractmethod

from app.skills.metadata import SkillMetadata


class Skill(ABC):
    """
    Common interface every data-retrieval tool must implement.
    SkillService talks only to this interface, never to a specific
    skill's HTTP client or SDK directly - mirrors how LLMService
    talks only to ModelProvider.
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        ...

    @abstractmethod
    def run(self, query_type: str, payload: dict) -> dict:
        ...
