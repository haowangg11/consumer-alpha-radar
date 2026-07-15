from abc import ABC, abstractmethod


class Evaluator(ABC):
    """
    Common interface every evaluator must implement. EvalHarness
    talks only to this interface, never to a specific scoring
    implementation directly - mirrors how SkillService talks only
    to Skill, and LLMService only to ModelProvider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def score(self, case: dict, output: dict, meta: dict) -> dict:
        """
        Returns a dict with at least {"score": float in [0, 1], "passed": bool}.
        `meta` carries run-level facts (e.g. latency_ms, cost) that
        aren't part of the agent's own output.
        """
        ...
