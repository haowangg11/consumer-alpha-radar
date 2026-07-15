from app.skills.base import Skill
from app.skills.metadata import SkillMetadata


class GoogleTrendsSkill(Skill):
    """
    Placeholder for the Google Trends data source. No real API call
    is wired in yet - run() returns a structured stub so the Skill
    Layer is exercisable end-to-end before real integration lands.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="google_trends",
            description="Retrieves search interest trends for consumer keywords.",
            version="0.1.0",
            input_schema={"keywords": "list[str]"},
            output_schema={"trend_scores": "dict[str, int]"},
            tags=["search", "consumer-data", "trend-discovery"],
        )

    def run(self, query_type: str, payload: dict) -> dict:
        return {
            "skill": "google_trends",
            "status": "not_implemented",
            "detail": "Google Trends skill is a placeholder - no real API call has been wired in yet.",
        }
