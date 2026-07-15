from app.services.llm_service import LLMService


class CompanyMappingAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Company Mapping Agent"
        self.llm_service = llm_service or LLMService()

    def map_companies(self, trend: str) -> dict:
        """
        Map a consumer trend to public companies positioned to
        benefit from it, by delegating reasoning to the LLM service.
        """

        return self.llm_service.run(
            task_type="company_mapping",
            payload={"trend": trend},
        )
