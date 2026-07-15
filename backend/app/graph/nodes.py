def _task_memory(config):
    """
    TaskMemory travels via config, not state (see state.py) - this
    is the one place every node reaches into config to find it.
    """

    return (config or {}).get("configurable", {}).get("task_memory")


def make_ingest_signals_node(skill_service):
    def ingest_signals(state, config):
        keywords = state.get("keywords", [])
        google_trends = skill_service.run(
            "google_trends", "keyword_interest", {"keywords": keywords}
        )
        reddit = skill_service.run(
            "reddit", "sentiment_scan", {"subreddit": "all", "keywords": keywords}
        )

        task_memory = _task_memory(config)
        if task_memory is not None:
            task_memory.set(
                "raw_signals", {"google_trends": google_trends, "reddit": reddit}
            )

        return {
            "raw_consumer_data": [
                f"google_trends[{keywords}]: {google_trends.get('detail', google_trends)}",
                f"reddit[{keywords}]: {reddit.get('detail', reddit)}",
            ]
        }

    return ingest_signals


def make_trend_discovery_node(agent, trend_memory):
    def trend_discovery(state, config):
        output = agent.analyze(state.get("raw_consumer_data", []))
        trend_id = output.get("trend", "unknown_trend")
        trend_memory.record_trend(trend_id, output)
        return {"trends": [output]}

    return trend_discovery


def make_consumer_psychology_node(agent):
    def consumer_psychology(state, config):
        insights = {}
        for trend in state.get("trends", []):
            trend_id = trend.get("trend", "unknown_trend")
            insights[trend_id] = agent.analyze(trend)
        return {"psychology_insights": insights}

    return consumer_psychology


def make_company_mapping_node(agent, company_memory):
    def company_mapping(state, config):
        candidates = {}
        for trend in state.get("trends", []):
            trend_id = trend.get("trend", "unknown_trend")
            result = agent.map_companies(trend_id)
            candidates[trend_id] = result
            for ticker in result.get("tickers", []):
                company_memory.record_company(ticker, {"trend_id": trend_id, **result})
        return {"company_candidates": candidates}

    return company_mapping


def make_financial_analysis_node(agent, market_memory):
    def financial_analysis(state, config):
        analysis = {}
        run_id = state.get("run_id", "run")
        for mapping in state.get("company_candidates", {}).values():
            for ticker in mapping.get("tickers", []):
                result = agent.analyze(ticker)
                analysis[ticker] = result
                market_memory.record_snapshot(f"{ticker}_{run_id}", result)
        return {"financial_analysis": analysis}

    return financial_analysis


def make_risk_critic_node(agent):
    def risk_critic(state, config):
        critique = agent.critique(
            state.get("company_candidates", {}),
            state.get("financial_analysis", {}),
        )
        return {
            "risk_flags": [critique],
            "retry_count": state.get("retry_count", 0) + 1,
        }

    return risk_critic


def make_investment_synthesis_node():
    def investment_synthesis(state, config):
        risk_flags = state.get("risk_flags", [])
        latest_critique = risk_flags[-1] if risk_flags else {}

        insights = []
        for trend_id, mapping in state.get("company_candidates", {}).items():
            for ticker in mapping.get("tickers", []):
                insights.append(
                    {
                        "trend": trend_id,
                        "ticker": ticker,
                        "psychology": state.get("psychology_insights", {}).get(trend_id),
                        "financials": state.get("financial_analysis", {}).get(ticker),
                        "risk_review": latest_critique,
                    }
                )
        return {"investment_insights": insights}

    return investment_synthesis
