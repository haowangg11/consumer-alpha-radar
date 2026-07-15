from app.services.llm_service import LLMService


class TrendDiscoveryAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Trend Discovery Agent"
        self.llm_service = llm_service or LLMService()


    def analyze(self, consumer_data):

        """
        Analyze consumer signals and identify emerging trends
        by delegating reasoning to the LLM service.
        """

        return self.llm_service.run(
            task_type="trend_discovery",
            payload={"consumer_data": consumer_data},
        )