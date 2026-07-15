from app.evaluation.base import Evaluator


class TrendEvaluator(Evaluator):
    """
    Scores Trend Discovery Agent output against the expected trend
    name, category, and minimum momentum score declared on the case.
    """

    @property
    def name(self) -> str:
        return "trend_evaluator"

    def score(self, case: dict, output: dict, meta: dict) -> dict:
        expected = case.get("expected", {})
        checks = {}

        if "trend" in expected:
            checks["trend_match"] = (
                str(output.get("trend", "")).strip().lower()
                == str(expected["trend"]).strip().lower()
            )
        if "category" in expected:
            checks["category_match"] = (
                str(output.get("category", "")).strip().lower()
                == str(expected["category"]).strip().lower()
            )
        if "min_momentum_score" in expected:
            checks["momentum_above_min"] = (
                output.get("momentum_score", 0) >= expected["min_momentum_score"]
            )

        passed_count = sum(1 for ok in checks.values() if ok)
        score = passed_count / len(checks) if checks else 0.0

        return {"score": score, "passed": score == 1.0, "checks": checks}
