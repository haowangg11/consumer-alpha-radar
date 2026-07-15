from app.skills.registry import SkillRegistry
from app.skills.responses import error_response


class SkillService:
    """
    Single entry point agents use to reach a skill. Delegates skill
    *lookup* to SkillRegistry and execution to the Skill itself.
    Agents must never call a skill implementation directly.

    Normalizes failures: an unknown skill name, or any exception a
    skill raises while running (SkillError or otherwise), comes back
    as an error_response(...) dict rather than propagating - callers
    (agents, graph nodes) only ever see a dict, never an exception.
    """

    def __init__(self, registry: SkillRegistry = None):
        self.registry = registry or SkillRegistry()

    def run(self, skill_name: str, query_type: str, payload: dict) -> dict:
        try:
            skill = self.registry.get(skill_name)
        except KeyError as exc:
            return error_response(skill=skill_name, exc=exc)

        try:
            return skill.run(query_type=query_type, payload=payload)
        except Exception as exc:
            return error_response(skill=skill_name, exc=exc)

    def list_available_skills(self) -> list:
        return self.registry.list_metadata()
