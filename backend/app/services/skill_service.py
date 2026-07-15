from app.skills.registry import SkillRegistry


class SkillService:
    """
    Single entry point agents use to reach a skill. Delegates skill
    *lookup* to SkillRegistry and execution to the Skill itself.
    Agents must never call a skill implementation directly.
    """

    def __init__(self, registry: SkillRegistry = None):
        self.registry = registry or SkillRegistry()

    def run(self, skill_name: str, query_type: str, payload: dict) -> dict:
        skill = self.registry.get(skill_name)
        return skill.run(query_type=query_type, payload=payload)

    def list_available_skills(self) -> list:
        return self.registry.list_metadata()
