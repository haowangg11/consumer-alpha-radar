from app.models.router import ModelRouter, ModelType


class MockModelProvider:
    """
    Stand-in Model Provider. Returns deterministic structured
    responses instead of calling a real LLM API, so the
    Agent -> Service -> Router -> Provider chain can be exercised
    end-to-end before real integrations exist.
    """

    def generate(self, model: ModelType, task_type: str, payload: dict) -> dict:
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


class LLMService:
    """
    Single entry point agents use to reach a model.
    Delegates model *selection* to ModelRouter and execution
    to a Model Provider. Agents must never call a provider directly.
    """

    def __init__(self, router: ModelRouter = None, provider: MockModelProvider = None):
        self.router = router or ModelRouter()
        self.provider = provider or MockModelProvider()

    def run(self, task_type: str, payload: dict) -> dict:
        model = self.router.select_model(task_type)
        return self.provider.generate(model=model, task_type=task_type, payload=payload)
