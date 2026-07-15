import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict, total=False):
    """
    Shared state threaded through every node, mirroring the Core
    Product Flow: signals -> trend -> psychology -> company mapping
    -> financial analysis -> (risk critique loop) -> investment
    insight.

    Fields a single node writes once just overwrite on update (the
    LangGraph default). Fields that accumulate across nodes or
    across risk-critique loop iterations are Annotated with
    `operator.add` so repeated writes append instead of clobbering.

    TaskMemory is deliberately NOT a field here - it's ephemeral and
    non-serializable by design, so it travels via the run's
    `config["configurable"]` instead of the checkpointed state.
    """

    run_id: str
    keywords: list[str]

    raw_consumer_data: list[str]
    trends: list[dict]
    psychology_insights: dict
    company_candidates: dict
    # trend_id -> {ticker -> financial analysis result}, mirroring
    # company_candidates' trend_id -> {tickers: [...]} shape so a
    # ticker shared by two trends never collides on a bare key.
    financial_analysis: dict

    retry_count: int
    risk_flags: Annotated[list[dict], operator.add]
    warnings: Annotated[list[str], operator.add]

    investment_insights: list[dict]
