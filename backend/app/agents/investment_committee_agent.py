from app.services.llm_service import LLMService


class InvestmentCommitteeAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Investment Committee Agent"
        self.llm_service = llm_service or LLMService()

    def synthesize(
        self,
        trend: str,
        ticker: str,
        psychology: dict,
        financials: dict,
        risk_review: dict,
    ) -> dict:
        """
        Weigh consumer psychology, financial analysis, and the risk
        critique for a single trend/ticker pair into a final
        investment call, by delegating reasoning to the LLM service.
        """

        return self.llm_service.run(
            task_type="investment_committee",
            payload={
                "trend": trend,
                "ticker": ticker,
                "psychology": psychology,
                "financials": financials,
                "risk_review": risk_review,
            },
        )
