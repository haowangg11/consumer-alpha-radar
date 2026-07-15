from app.skills.base import Skill
from app.skills.metadata import SkillMetadata


class StockDataSkill(Skill):
    """
    Placeholder for the stock/market data source. No real API call
    is wired in yet - run() returns a structured stub so the Skill
    Layer is exercisable end-to-end before real integration lands.
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="stock_data",
            description="Retrieves price and fundamentals data for a public company ticker.",
            version="0.1.0",
            input_schema={"ticker": "str"},
            output_schema={"price": "float", "fundamentals": "dict"},
            tags=["market-data", "financial-analysis", "company-mapping"],
        )

    def run(self, query_type: str, payload: dict) -> dict:
        return {
            "skill": "stock_data",
            "status": "not_implemented",
            "detail": "Stock data skill is a placeholder - no real API call has been wired in yet.",
        }
