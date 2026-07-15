from enum import Enum


class ModelType(Enum):
    GPT = "gpt"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


class ModelRouter:

    def select_model(self, task_type: str):

        if task_type == "financial_reasoning":
            return ModelType.GPT
        
        elif task_type == "chinese_text":
            return ModelType.QWEN
        
        else:
            return ModelType.DEEPSEEK