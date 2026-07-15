from app.services.llm_service import LLMService


class ConsumerPsychologyAgent:

    def __init__(self, llm_service: LLMService = None):
        self.name = "Consumer Psychology Agent"
        self.llm_service = llm_service or LLMService()

    def analyze(self, trend: dict) -> dict:
        """
        Analyze the underlying consumer psychology driving a trend,
        by delegating reasoning to the LLM service.
        """

        return self.llm_service.run(
            task_type="consumer_psychology",
            payload={"trend": trend},
        )
