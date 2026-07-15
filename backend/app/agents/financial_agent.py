from app.services.llm_service import LLMService


class FinancialAnalysisAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Financial Analysis Agent"
        self.llm_service = llm_service or LLMService()

    def analyze(self, ticker: str) -> dict:
        """
        Analyze a company's financial profile relative to a mapped
        trend, by delegating reasoning to the LLM service.
        """

        return self.llm_service.run(
            task_type="financial_analysis",
            payload={"ticker": ticker},
        )
