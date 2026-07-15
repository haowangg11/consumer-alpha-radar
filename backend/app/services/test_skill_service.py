from app.skills.base import Skill
from app.skills.errors import SkillHTTPError
from app.skills.metadata import SkillMetadata
from app.services.skill_service import SkillService


service = SkillService()

result = service.run("reddit", "sentiment_scan", {"subreddit": "wallstreetbets", "keywords": ["protein coffee"]})
assert result["skill"] == "reddit"

available = service.list_available_skills()
assert {m.name for m in available} == {"google_trends", "reddit", "stock_data"}

print("available skills:", [(m.name, m.version) for m in available])
print("sample result:", result)


# --- error contract: SkillService normalizes a raised SkillError ---

class _FailingSkill(Skill):
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name="failing", description="Always fails.", version="0.0.1")

    def run(self, query_type: str, payload: dict) -> dict:
        raise SkillHTTPError("upstream returned 503", status_code=503, retryable=True)


# --- error contract: SkillService normalizes an unexpected exception too ---

class _BuggySkill(Skill):
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name="buggy", description="Raises a bug, not a SkillError.", version="0.0.1")

    def run(self, query_type: str, payload: dict) -> dict:
        raise ValueError("boom")


error_service = SkillService(registry=None)
error_service.registry.skills = {"failing": _FailingSkill(), "buggy": _BuggySkill()}

failing_result = error_service.run("failing", "any", {})
assert failing_result["status"] == "error"
assert failing_result["skill"] == "failing"
assert failing_result["error"]["type"] == "SkillHTTPError"
assert failing_result["error"]["retryable"] is True

buggy_result = error_service.run("buggy", "any", {})
assert buggy_result["status"] == "error"
assert buggy_result["error"]["type"] == "ValueError"
assert buggy_result["error"]["retryable"] is False

unknown_result = service.run("does_not_exist", "any", {})
assert unknown_result["status"] == "error"
assert unknown_result["error"]["type"] == "KeyError"

print("failing skill normalized:", failing_result)
print("buggy skill normalized:", buggy_result)
print("unknown skill normalized:", unknown_result)
print("OK")
