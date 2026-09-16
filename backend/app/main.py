import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.consumer_analysis import stream_consumer_analysis
from app.skills.market_data_skill import MarketDataSkill
from app.trend_radar import trend_radar_topics
from app.workspace_store import default_workspace_store

app = FastAPI(
    title="Consumer Alpha Radar API"
)
workspace_store = default_workspace_store()


@app.get("/")
def home():
    return {
        "message": "Consumer Alpha Radar Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/api/trend-radar/topics")
def get_trend_radar_topics(keyword: str = "", limit: int = 24, per_topic: int = 100, refresh: bool = False):
    return trend_radar_topics(keyword=keyword, limit=limit, per_topic=per_topic, refresh=refresh)


@app.get("/api/stocks/{market}/{ticker}")
def get_stock_snapshot(market: str, ticker: str):
    market_data = MarketDataSkill()
    normalized_market, normalized_ticker = normalize_stock_route(market, ticker)
    if normalized_market == "A":
        return market_data.run("a_share_detail", {"code": normalized_ticker})
    symbol = f"{normalized_ticker}.{normalized_market}" if normalized_market in {"HK", "US"} else normalized_ticker
    return market_data.run("global_stock", {"symbol": symbol})


@app.get("/api/stocks/{market}/{ticker}/quote")
def get_stock_quote(market: str, ticker: str):
    market_data = MarketDataSkill()
    normalized_market, normalized_ticker = normalize_stock_route(market, ticker)
    if normalized_market == "A":
        quote = market_data.run("a_share_quote", {"codes": [normalized_ticker]})
        return {
            "skill": "market_data",
            "data": {
                "code": normalized_ticker,
                "market": normalized_market,
                "quote": (quote.get("data") or {}).get(normalized_ticker),
            },
        }
    symbol = f"{normalized_ticker}.{normalized_market}" if normalized_market in {"HK", "US"} else normalized_ticker
    return market_data.run("global_stock_quote", {"symbol": symbol})


@app.get("/api/stocks/{market}/{ticker}/kline")
def get_stock_kline(market: str, ticker: str):
    market_data = MarketDataSkill()
    normalized_market, normalized_ticker = normalize_stock_route(market, ticker)
    if normalized_market == "A":
        return market_data.run("a_share_kline", {"code": normalized_ticker})
    symbol = f"{normalized_ticker}.{normalized_market}" if normalized_market in {"HK", "US"} else normalized_ticker
    return market_data.run("global_stock_kline", {"symbol": symbol})


def normalize_stock_route(market: str, ticker: str) -> tuple[str, str]:
    raw_ticker = ticker.strip().upper()
    normalized_market = market.strip().upper()
    suffix = ""
    normalized_ticker = raw_ticker
    if "." in raw_ticker:
        base, maybe_suffix = raw_ticker.rsplit(".", 1)
        if maybe_suffix in {"SH", "SZ", "BJ", "HK", "US"}:
            normalized_ticker = base
            suffix = maybe_suffix
    if normalized_ticker.isdigit() and len(normalized_ticker) == 6 and suffix in {"", "SH", "SZ", "BJ"}:
        return "A", normalized_ticker
    if normalized_ticker.isdigit() and 4 <= len(normalized_ticker) <= 5 and (suffix in {"", "HK"} and normalized_market != "A"):
        return "HK", normalized_ticker
    if suffix == "US":
        return "US", normalized_ticker
    return normalized_market, normalized_ticker


class ConsumerAnalyzeRequest(BaseModel):
    signal: str
    market_scope: str = "ALL"
    mode: str = "full"
    llm: dict = Field(default_factory=dict)


class WorkspaceStateRequest(BaseModel):
    state: dict = Field(default_factory=dict)


class AnalysisHistoryRequest(BaseModel):
    analysis: dict = Field(default_factory=dict)


class WatchlistItemRequest(BaseModel):
    item: dict = Field(default_factory=dict)


class EvidenceItemRequest(BaseModel):
    item: dict = Field(default_factory=dict)


class SelectedStockRequest(BaseModel):
    stock: dict | None = None


@app.post("/api/analyze-consumer-signal/stream")
def analyze_consumer_signal_stream(req: ConsumerAnalyzeRequest):
    def generate():
        try:
            for event in stream_consumer_analysis(req.model_dump()):
                yield event
        except Exception as exc:
            yield json.dumps(
                {"type": "error", "message": f"Analysis failed: {exc}"},
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/api/workspace/state")
def get_workspace_state():
    return workspace_store.get_state()


@app.put("/api/workspace/state")
def replace_workspace_state(req: WorkspaceStateRequest):
    return workspace_store.replace_state(req.state)


@app.post("/api/workspace/analyses")
def save_analysis_history(req: AnalysisHistoryRequest):
    return workspace_store.save_analysis(req.analysis)


@app.post("/api/workspace/history")
def save_analysis_history_alias(req: AnalysisHistoryRequest):
    return workspace_store.save_analysis(req.analysis)


@app.delete("/api/workspace/analyses/{run_id}")
def delete_analysis_history(run_id: str):
    return workspace_store.delete_analysis(run_id)


@app.delete("/api/workspace/history/{run_id}")
def delete_analysis_history_alias(run_id: str):
    return workspace_store.delete_analysis(run_id)


@app.post("/api/workspace/watchlist")
def upsert_watchlist_item(req: WatchlistItemRequest):
    return workspace_store.upsert_watchlist_item(req.item)


@app.delete("/api/workspace/watchlist/{item_id}")
def delete_watchlist_item(item_id: str):
    return workspace_store.delete_watchlist_item(item_id)


@app.post("/api/workspace/saved-evidence")
def upsert_saved_evidence(req: EvidenceItemRequest):
    return workspace_store.upsert_saved_evidence(req.item)


@app.post("/api/workspace/evidence")
def upsert_saved_evidence_alias(req: EvidenceItemRequest):
    return workspace_store.upsert_saved_evidence(req.item)


@app.delete("/api/workspace/saved-evidence/{item_id}")
def delete_saved_evidence(item_id: str):
    return workspace_store.delete_saved_evidence(item_id)


@app.delete("/api/workspace/evidence/{item_id}")
def delete_saved_evidence_alias(item_id: str):
    return workspace_store.delete_saved_evidence(item_id)


@app.put("/api/workspace/selected-stock")
def set_selected_stock(req: SelectedStockRequest):
    return workspace_store.set_selected_stock(req.stock)
