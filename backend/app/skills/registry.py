from app.skills.base import Skill
from app.skills.metadata import SkillMetadata
from app.skills.google_trends_skill import GoogleTrendsSkill
from app.skills.market_data_skill import MarketDataSkill
from app.skills.reddit_skill import RedditSkill
from app.skills.stock_data_skill import StockDataSkill


class SkillRegistry:
    """
    Looks up a Skill by name. Agents never import a concrete skill
    directly - they go through SkillService, which goes through
    this registry, mirroring the ModelRouter/Provider pattern.
    """

    def __init__(self, skills: dict = None):
        self.skills = skills or {
            "google_trends": GoogleTrendsSkill(),
            "reddit": RedditSkill(),
            "stock_data": StockDataSkill(),
            "market_data": MarketDataSkill(),
        }

    def get(self, name: str) -> Skill:
        if name not in self.skills:
            raise KeyError(f"No skill registered under name '{name}'")
        return self.skills[name]

    def list_metadata(self) -> list:
        return [skill.metadata for skill in self.skills.values()]
