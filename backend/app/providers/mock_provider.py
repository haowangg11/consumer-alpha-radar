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

        return {
            "result": f"No mock response configured for task_type '{task_type}'",
        }
