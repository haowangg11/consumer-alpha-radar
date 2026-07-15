from app.providers.base import ModelProvider


class MockProvider(ModelProvider):
    """
    Deterministic stand-in provider. Returns canned structured
    responses instead of calling a real LLM API, so the
    Agent -> Service -> Router -> Provider chain can be exercised
    end-to-end before real integrations exist.
    """

    def generate(self, task_type: str, payload: dict) -> dict:
        if task_type == "trend_discovery":
            return {
                "trend": "Protein Coffee",
                "category": "Food & Beverage",
                "momentum_score": 85,
                "reason": "Growing demand for healthy convenient drinks",
            }

        if task_type == "company_mapping":
            return {
                "trend": "Protein Coffee",
                "tickers": ["KDP", "SBUX"],
                "reason": "Both companies sell ready-to-drink coffee and protein beverages",
            }

        if task_type == "financial_analysis":
            return {
                "ticker": "KDP",
                "revenue_growth": 0.08,
                "margin_trend": "expanding",
            }

        if task_type == "consumer_psychology":
            return {
                "trend": "Protein Coffee",
                "psychology": "Health-conscious convenience seeking",
                "confidence": 0.8,
            }

        if task_type == "risk_critic":
            return {
                "requires_revision": False,
                "reason": "Company mapping and financials are consistent with the trend.",
            }

        return {
            "result": f"No mock response configured for task_type '{task_type}'",
        }
