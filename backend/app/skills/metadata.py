from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillMetadata:
    """
    Describes a Skill without executing it, so future agent tool
    selection (LLM-driven or otherwise) can enumerate what's
    available before deciding what to call.
    """

    name: str
    description: str
    version: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
