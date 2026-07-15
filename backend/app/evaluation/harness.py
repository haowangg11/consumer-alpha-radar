import json
import time

from app.agents.company_mapping_agent import CompanyMappingAgent
from app.agents.financial_agent import FinancialAnalysisAgent
from app.agents.trend_agent import TrendDiscoveryAgent
from app.evaluation.cases import MOCK_CASES
from app.evaluation.company_mapping_evaluator import CompanyMappingEvaluator
from app.evaluation.cost_latency_evaluator import CostLatencyEvaluator
from app.evaluation.financial_evaluator import FinancialEvaluator
from app.evaluation.trace import EvaluationTrace
from app.evaluation.trace_logger import TraceLogger
from app.evaluation.trend_evaluator import TrendEvaluator
from app.models.router import ModelType
from app.providers.mock_provider import MockProvider
from app.services.llm_service import LLMService

COST_PER_CHAR = 0.00001


def default_agents() -> dict:
    """
    Wires each agent to an all-MockProvider LLMService so the
    harness stays fully offline and deterministic - it never touches
    the real OpenAI/DeepSeek/Qwen provider stubs used elsewhere.
    """

    mock_llm_service = LLMService(
        providers={
            ModelType.GPT: MockProvider(),
            ModelType.DEEPSEEK: MockProvider(),
            ModelType.QWEN: MockProvider(),
        }
    )
    trend_agent = TrendDiscoveryAgent(llm_service=mock_llm_service)
    company_agent = CompanyMappingAgent(llm_service=mock_llm_service)
    financial_agent = FinancialAnalysisAgent(llm_service=mock_llm_service)

    return {
        "trend_discovery": lambda payload: trend_agent.analyze(payload["consumer_data"]),
        "company_mapping": lambda payload: company_agent.map_companies(payload["trend"]),
        "financial_analysis": lambda payload: financial_agent.analyze(payload["ticker"]),
    }


def default_evaluators() -> dict:
    evaluators = [
        TrendEvaluator(),
        CompanyMappingEvaluator(),
        FinancialEvaluator(),
        CostLatencyEvaluator(),
    ]
    return {evaluator.name: evaluator for evaluator in evaluators}


class EvalHarness:
    """
    Loads eval cases, runs each through its target agent, scores the
    output with the evaluators the case declares, and saves every
    run as a trace via TraceLogger.
    """

    def __init__(
        self,
        cases: list = None,
        agents: dict = None,
        evaluators: dict = None,
        trace_logger: TraceLogger = None,
    ):
        self.cases = cases if cases is not None else MOCK_CASES
        self.agents = agents or default_agents()
        self.evaluators = evaluators or default_evaluators()
        self.trace_logger = trace_logger or TraceLogger()

    def run(self) -> list:
        return [self._run_case(case) for case in self.cases]

    def _run_case(self, case: dict) -> EvaluationTrace:
        agent = self.agents[case["agent"]]

        start = time.perf_counter()
        output = agent(case["input"])
        latency_ms = (time.perf_counter() - start) * 1000
        meta = {
            "latency_ms": latency_ms,
            "cost": self._estimate_cost(case["input"], output),
        }

        scores = {
            evaluator_name: self.evaluators[evaluator_name].score(case, output, meta)
            for evaluator_name in case["evaluators"]
        }
        passed = all(result["passed"] for result in scores.values())

        trace = EvaluationTrace(
            case_id=case["case_id"],
            task_type=case["agent"],
            input=case["input"],
            output=output,
            scores=scores,
            passed=passed,
            latency_ms=latency_ms,
        )
        self.trace_logger.log(trace)
        return trace

    @staticmethod
    def _estimate_cost(payload: dict, output: dict) -> float:
        """
        Offline stand-in for a real per-token bill: proportional to
        payload/output size so cost_latency_evaluator has something
        deterministic to check without calling a priced API.
        """

        size = len(json.dumps(payload)) + len(json.dumps(output))
        return round(size * COST_PER_CHAR, 6)
