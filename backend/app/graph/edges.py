from app.graph.state import GraphState

MAX_RISK_CRITIQUE_RETRIES = 2


def route_after_risk_critic(state: GraphState) -> str:
    """
    Sends the graph back to company_mapping for a bounded number of
    revisions when Risk Critic flags a problem, otherwise lets it
    proceed to the investment committee. `retry_count` (incremented
    by the risk_critic node every pass) guarantees termination even
    if the critic keeps flagging issues.
    """

    risk_flags = state.get("risk_flags", [])
    latest = risk_flags[-1] if risk_flags else {}

    if latest.get("requires_revision") and state.get("retry_count", 0) < MAX_RISK_CRITIQUE_RETRIES:
        return "revise"
    return "synthesize"
