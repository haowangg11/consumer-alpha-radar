from app.skills.base import Skill
from app.skills.metadata import SkillMetadata


class RedditSkill(Skill):
    """
    Placeholder for the Reddit data source. No real API call is
    wired in yet - run() returns a structured stub so the Skill
    Layer is exercisable end-to-end before real integration lands.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="reddit",
            description="Retrieves discussion volume and sentiment for consumer topics from Reddit.",
            version="0.1.0",
            input_schema={"subreddit": "str", "keywords": "list[str]"},
            output_schema={"mentions": "int", "sentiment": "str"},
            tags=["social", "consumer-data", "trend-discovery", "consumer-psychology"],
        )

    def run(self, query_type: str, payload: dict) -> dict:
        return {
            "skill": "reddit",
            "status": "not_implemented",
            "detail": "Reddit skill is a placeholder - no real API call has been wired in yet.",
        }
