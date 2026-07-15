from app.evaluation.base import Evaluator


class CompanyMappingEvaluator(Evaluator):
    """
    Scores Company Mapping Agent output by how many expected tickers
    it recovered, penalizing tickers that don't belong on the list.
    """

    @property
    def name(self) -> str:
        return "company_mapping_evaluator"

    def score(self, case: dict, output: dict, meta: dict) -> dict:
        expected_tickers = set(case.get("expected", {}).get("tickers", []))
        actual_tickers = set(output.get("tickers", []))

        if not expected_tickers:
            return {"score": 0.0, "passed": False, "checks": {}}

        matched = expected_tickers & actual_tickers
        extra = actual_tickers - expected_tickers
        recall = len(matched) / len(expected_tickers)
        precision = len(matched) / len(actual_tickers) if actual_tickers else 0.0
        score = recall if not extra else (recall + precision) / 2

        return {
            "score": score,
            "passed": expected_tickers == actual_tickers,
            "checks": {
                "matched_tickers": sorted(matched),
                "missing_tickers": sorted(expected_tickers - actual_tickers),
                "unexpected_tickers": sorted(extra),
            },
        }
