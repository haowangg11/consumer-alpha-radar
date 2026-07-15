from enum import Enum


class ModelType(Enum):
    GPT = "gpt"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


class ModelRouter:

    TASK_MODEL_MAP = {
        "trend_discovery": ModelType.QWEN,
        "consumer_psychology": ModelType.QWEN,
        "financial_analysis": ModelType.GPT,
        "investment_committee": ModelType.GPT,
        "cost_sensitive_summary": ModelType.DEEPSEEK,
    }

    def select_model(self, task_type: str) -> ModelType:
        return self.TASK_MODEL_MAP.get(task_type, ModelType.DEEPSEEK)