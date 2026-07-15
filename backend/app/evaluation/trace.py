import time
from dataclasses import asdict, dataclass, field


@dataclass
class EvaluationTrace:
    """
    Full record of one evaluation case run: what was fed in, what
    came out, and how it scored - the unit TraceLogger persists so
    eval runs can be inspected or diffed after the fact.
    """

    case_id: str
    task_type: str
    input: dict
    output: dict
    scores: dict
    passed: bool
    latency_ms: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)
