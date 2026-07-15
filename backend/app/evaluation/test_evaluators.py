from app.evaluation.company_mapping_evaluator import CompanyMappingEvaluator
from app.evaluation.cost_latency_evaluator import CostLatencyEvaluator
from app.evaluation.financial_evaluator import FinancialEvaluator
from app.evaluation.trend_evaluator import TrendEvaluator


# trend_evaluator
trend_eval = TrendEvaluator()
trend_case = {
    "expected": {"trend": "Protein Coffee", "category": "Food & Beverage", "min_momentum_score": 70},
}
passing = trend_eval.score(trend_case, {"trend": "Protein Coffee", "category": "Food & Beverage", "momentum_score": 85}, {})
assert passing["passed"] is True and passing["score"] == 1.0

failing = trend_eval.score(trend_case, {"trend": "Cold Brew", "category": "Food & Beverage", "momentum_score": 85}, {})
assert failing["passed"] is False and 0.0 < failing["score"] < 1.0

# company_mapping_evaluator
company_eval = CompanyMappingEvaluator()
company_case = {"expected": {"tickers": ["KDP", "SBUX"]}}
passing = company_eval.score(company_case, {"tickers": ["KDP", "SBUX"]}, {})
assert passing["passed"] is True and passing["score"] == 1.0

failing = company_eval.score(company_case, {"tickers": ["MSFT"]}, {})
assert failing["passed"] is False and failing["score"] == 0.0

# financial_evaluator
financial_eval = FinancialEvaluator()
financial_case = {"expected": {"revenue_growth": 0.08, "margin_trend": "expanding", "tolerance": 0.01}}
passing = financial_eval.score(financial_case, {"revenue_growth": 0.081, "margin_trend": "expanding"}, {})
assert passing["passed"] is True

failing = financial_eval.score(financial_case, {"revenue_growth": 0.20, "margin_trend": "shrinking"}, {})
assert failing["passed"] is False and failing["score"] == 0.0

# cost_latency_evaluator
cost_eval = CostLatencyEvaluator()
cost_case = {"expected": {"max_latency_ms": 500, "max_cost": 0.05}}
passing = cost_eval.score(cost_case, {}, {"latency_ms": 100, "cost": 0.01})
assert passing["passed"] is True

failing = cost_eval.score(cost_case, {}, {"latency_ms": 900, "cost": 0.09})
assert failing["passed"] is False and failing["score"] == 0.0

print("OK")
