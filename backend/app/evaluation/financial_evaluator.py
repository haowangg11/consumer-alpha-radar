from app.evaluation.base import Evaluator

DEFAULT_TOLERANCE = 0.01


class FinancialEvaluator(Evaluator):
    """
    Scores Financial Analysis Agent output by checking each expected
    metric - numeric fields within a tolerance, others by equality.
    """

    @property
    def name(self) -> str:
        return "financial_evaluator"

    def score(self, case: dict, output: dict, meta: dict) -> dict:
        expected = case.get("expected", {})
        tolerance = expected.get("tolerance", DEFAULT_TOLERANCE)
        checks = {}

        for field_name, expected_value in expected.items():
            if field_name == "tolerance":
                continue

            actual_value = output.get(field_name)
            if isinstance(expected_value, (int, float)):
                checks[field_name] = (
                    isinstance(actual_value, (int, float))
                    and abs(actual_value - expected_value) <= tolerance
                )
            else:
                checks[field_name] = actual_value == expected_value

        passed_count = sum(1 for ok in checks.values() if ok)
        score = passed_count / len(checks) if checks else 0.0

        return {"score": score, "passed": score == 1.0, "checks": checks}
