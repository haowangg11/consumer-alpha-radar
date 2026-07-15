from app.services.llm_service import LLMService


class RiskCriticAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Risk Critic Agent"
        self.llm_service = llm_service or LLMService()

    def critique(self, company_candidates: dict, financial_analysis: dict) -> dict:
        """
        Critique the proposed company mapping and financial read,
        flagging anything that warrants another pass before the
        graph moves on to the investment committee.
        """

        return self.llm_service.run(
            task_type="risk_critic",
            payload={
                "company_candidates": company_candidates,
                "financial_analysis": financial_analysis,
            },
        )
