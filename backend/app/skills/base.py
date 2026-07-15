from abc import ABC, abstractmethod

from app.skills.metadata import SkillMetadata


class Skill(ABC):
    """
    Common interface every data-retrieval tool must implement.
    SkillService talks only to this interface, never to a specific
    skill's HTTP client or SDK directly - mirrors how LLMService
    talks only to ModelProvider.

    Contract for run():
    - On success, return app.skills.responses.success_response(...),
      i.e. {"skill": <name>, "status": "ok", "data": {...}}.
    - On failure, raise an app.skills.errors.SkillError (or subclass)
      rather than returning an error dict directly. Do not swallow
      errors inside run() - SkillService is responsible for catching
      them and normalizing them into
      app.skills.responses.error_response(...).
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        ...

    @abstractmethod
    def run(self, query_type: str, payload: dict) -> dict:
        ...
