from app.evaluation.base import Evaluator


class CostLatencyEvaluator(Evaluator):
    """
    Scores a case's execution efficiency against its declared
    latency/cost budget. The only evaluator that reads `meta`
    instead of the agent's own output.
    """

    @property
    def name(self) -> str:
        return "cost_latency_evaluator"

    def score(self, case: dict, output: dict, meta: dict) -> dict:
        expected = case.get("expected", {})
        checks = {}

        if "max_latency_ms" in expected:
            checks["within_latency_budget"] = (
                meta.get("latency_ms", float("inf")) <= expected["max_latency_ms"]
            )
        if "max_cost" in expected:
            checks["within_cost_budget"] = (
                meta.get("cost", float("inf")) <= expected["max_cost"]
            )

        passed_count = sum(1 for ok in checks.values() if ok)
        score = passed_count / len(checks) if checks else 0.0

        return {"score": score, "passed": score == 1.0, "checks": checks}
