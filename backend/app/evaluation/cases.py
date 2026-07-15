"""
Mock evaluation cases. No external APIs or datasets - inputs and
expected values are hand-authored so the harness stays fully offline
and deterministic. Each case is scored by the evaluators it names,
so a case can be checked by more than one evaluator (e.g. content
correctness and cost/latency budget together).
"""

MOCK_CASES = [
    {
        "case_id": "trend_001_pass",
        "agent": "trend_discovery",
        "input": {
            "consumer_data": [
                "protein coffee searches rising",
                "gym influencers promoting protein coffee",
            ]
        },
        "expected": {
            "trend": "Protein Coffee",
            "category": "Food & Beverage",
            "min_momentum_score": 70,
            "max_latency_ms": 1000,
            "max_cost": 1.0,
        },
        "evaluators": ["trend_evaluator", "cost_latency_evaluator"],
    },
    {
        "case_id": "trend_002_fail",
        "agent": "trend_discovery",
        "input": {"consumer_data": ["unrelated grocery browsing"]},
        "expected": {
            "trend": "Zero Sugar Energy Drinks",
            "category": "Food & Beverage",
            "min_momentum_score": 90,
        },
        "evaluators": ["trend_evaluator"],
    },
    {
        "case_id": "company_mapping_001_pass",
        "agent": "company_mapping",
        "input": {"trend": "Protein Coffee"},
        "expected": {"tickers": ["KDP", "SBUX"]},
        "evaluators": ["company_mapping_evaluator"],
    },
    {
        "case_id": "company_mapping_002_fail",
        "agent": "company_mapping",
        "input": {"trend": "Retro Gaming Consoles"},
        "expected": {"tickers": ["NTDOY", "MSFT"]},
        "evaluators": ["company_mapping_evaluator"],
    },
    {
        "case_id": "financial_001_pass",
        "agent": "financial_analysis",
        "input": {"ticker": "KDP"},
        "expected": {
            "revenue_growth": 0.08,
            "margin_trend": "expanding",
            "tolerance": 0.02,
        },
        "evaluators": ["financial_evaluator"],
    },
    {
        "case_id": "financial_002_fail",
        "agent": "financial_analysis",
        "input": {"ticker": "SBUX"},
        "expected": {"revenue_growth": 0.20, "tolerance": 0.01},
        "evaluators": ["financial_evaluator"],
    },
]
