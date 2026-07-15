import os
import tempfile

from app.graph.graph import build_graph, default_offline_agents
from app.memory.company_memory import CompanyMemory
from app.memory.json_file_store import JSONFileMemoryStore
from app.memory.market_memory import MarketMemory
from app.memory.task_memory import TaskMemory
from app.memory.trend_memory import TrendMemory


def _memories():
    tmp_dir = tempfile.mkdtemp()
    return (
        TrendMemory(store=JSONFileMemoryStore(os.path.join(tmp_dir, "trend.json"))),
        CompanyMemory(store=JSONFileMemoryStore(os.path.join(tmp_dir, "company.json"))),
        MarketMemory(store=JSONFileMemoryStore(os.path.join(tmp_dir, "market.json"))),
    )


# --- happy path: linear run straight through to the investment committee ---
trend_memory, company_memory, market_memory = _memories()
task_memory = TaskMemory()

graph = build_graph(
    agents=default_offline_agents(),
    trend_memory=trend_memory,
    company_memory=company_memory,
    market_memory=market_memory,
)
result = graph.invoke(
    {"run_id": "run_happy", "keywords": ["protein coffee"]},
    config={"configurable": {"thread_id": "run_happy", "task_memory": task_memory}},
)

assert result["trends"][0]["trend"] == "Protein Coffee"
assert result["company_candidates"]["Protein Coffee"]["tickers"] == ["KDP", "SBUX"]
assert set(result["financial_analysis"].keys()) == {"KDP", "SBUX"}
assert len(result["risk_flags"]) == 1
assert result["risk_flags"][0]["requires_revision"] is False
assert result["retry_count"] == 1

insight_tickers = {insight["ticker"] for insight in result["investment_insights"]}
assert insight_tickers == {"KDP", "SBUX"}
assert all(
    insight["committee_review"]["recommendation"] == "BUY"
    for insight in result["investment_insights"]
)

# ingest_signals stashed scratch data in TaskMemory, not in graph state
assert task_memory.get("raw_signals") is not None

# long-term memory got written as a side effect of the run
assert trend_memory.get_trend("Protein Coffee") is not None
assert company_memory.get_company("KDP") is not None
assert len(market_memory.find_snapshots()) == 2

print("happy path OK")


# --- critique loop: risk_critic forces a revision before the investment committee runs ---
class FlakyRiskCritic:
    """Flags a revision on its first call, then approves on the next."""

    def __init__(self, revise_times: int = 1):
        self.calls = 0
        self.revise_times = revise_times

    def critique(self, company_candidates, financial_analysis):
        self.calls += 1
        if self.calls <= self.revise_times:
            return {"requires_revision": True, "reason": "needs another look"}
        return {"requires_revision": False, "reason": "ok now"}


flaky_agents = default_offline_agents()
flaky_critic = FlakyRiskCritic(revise_times=1)
flaky_agents["risk_critic"] = flaky_critic

trend_memory, company_memory, market_memory = _memories()
loop_graph = build_graph(
    agents=flaky_agents,
    trend_memory=trend_memory,
    company_memory=company_memory,
    market_memory=market_memory,
)
loop_result = loop_graph.invoke(
    {"run_id": "run_loop", "keywords": ["protein coffee"]},
    config={"configurable": {"thread_id": "run_loop"}},
)

assert flaky_critic.calls == 2
assert loop_result["retry_count"] == 2
assert [flag["requires_revision"] for flag in loop_result["risk_flags"]] == [True, False]
assert loop_result["investment_insights"]

print("critique loop OK")
