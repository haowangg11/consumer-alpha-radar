import json
import os
import tempfile
import time
from copy import deepcopy
from threading import Lock
from typing import Any


DEFAULT_WORKSPACE_STATE = {
    "version": 1,
    "analysis_history": [],
    "watchlist": [],
    "saved_evidence": [],
    "selected_stock": None,
    "updated_at": None,
}


class WorkspaceStateStore:
    """
    Small product-level JSON store for the single-user radar workspace.

    This is intentionally separate from JSONFileMemoryStore: memory is a
    namespace/key-value primitive, while workspace state has product rules
    such as recent-history limits and user-managed asset lists.
    """

    def __init__(self, file_path: str, history_limit: int = 6):
        self.file_path = file_path
        self.history_limit = history_limit
        self._lock = Lock()

        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.file_path):
            self._write(deepcopy(DEFAULT_WORKSPACE_STATE))

    def get_state(self) -> dict:
        with self._lock:
            return self._normalize_state(self._read())

    def replace_state(self, state: dict) -> dict:
        with self._lock:
            normalized = self._normalize_state(state)
            normalized["updated_at"] = _now_ms()
            self._write(normalized)
            return normalized

    def save_analysis(self, analysis: dict) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            record = self._normalize_analysis(analysis)
            existing = [
                item
                for item in state["analysis_history"]
                if item.get("run_id") != record.get("run_id")
            ]
            state["analysis_history"] = [record, *existing][: self.history_limit]
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def delete_analysis(self, run_id: str) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            state["analysis_history"] = [
                item for item in state["analysis_history"] if item.get("run_id") != run_id
            ]
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def upsert_watchlist_item(self, item: dict) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            normalized = self._normalize_watchlist_item(item)
            key = _asset_key(normalized)
            state["watchlist"] = [
                entry for entry in state["watchlist"] if _asset_key(entry) != key
            ]
            state["watchlist"].insert(0, normalized)
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def delete_watchlist_item(self, item_id: str) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            state["watchlist"] = [
                item
                for item in state["watchlist"]
                if item.get("id") != item_id and _asset_key(item) != item_id
            ]
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def upsert_saved_evidence(self, item: dict) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            normalized = self._normalize_evidence_item(item)
            key = str(normalized.get("id") or "")
            state["saved_evidence"] = [
                entry for entry in state["saved_evidence"] if str(entry.get("id")) != key
            ]
            state["saved_evidence"].insert(0, normalized)
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def delete_saved_evidence(self, item_id: str) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            state["saved_evidence"] = [
                item for item in state["saved_evidence"] if str(item.get("id")) != item_id
            ]
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def set_selected_stock(self, stock: dict | None) -> dict:
        with self._lock:
            state = self._normalize_state(self._read())
            state["selected_stock"] = self._normalize_stock(stock) if stock else None
            state["updated_at"] = _now_ms()
            self._write(state)
            return state

    def _read(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return deepcopy(DEFAULT_WORKSPACE_STATE)
        return data if isinstance(data, dict) else deepcopy(DEFAULT_WORKSPACE_STATE)

    def _write(self, state: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)

    def _normalize_state(self, state: dict) -> dict:
        normalized = deepcopy(DEFAULT_WORKSPACE_STATE)
        normalized.update(state or {})
        raw_history = normalized.get("analysis_history") or normalized.get("recent_analyses")
        normalized["analysis_history"] = [
            self._normalize_analysis(item)
            for item in _as_list(raw_history)
        ][: self.history_limit]
        normalized.pop("recent_analyses", None)
        normalized["watchlist"] = [
            self._normalize_watchlist_item(item)
            for item in _as_list(normalized.get("watchlist"))
        ]
        normalized["saved_evidence"] = [
            self._normalize_evidence_item(item)
            for item in _as_list(normalized.get("saved_evidence"))
        ]
        if normalized.get("selected_stock"):
            normalized["selected_stock"] = self._normalize_stock(normalized["selected_stock"])
        return normalized

    def _normalize_analysis(self, analysis: dict) -> dict:
        analysis = analysis if isinstance(analysis, dict) else {}
        run_id = str(analysis.get("run_id") or f"analysis-{_now_ms()}")
        return {
            "run_id": run_id,
            "signal": str(analysis.get("signal") or ""),
            "market_scope": str(analysis.get("market_scope") or "ALL"),
            "maturity": str(analysis.get("maturity") or "Insufficient"),
            "created_at": analysis.get("created_at") or _now_ms(),
            "sections": _as_list(analysis.get("sections")),
            "candidates": _as_list(analysis.get("candidates")),
            "evidence": _as_list(analysis.get("evidence")),
            "agent_messages": _as_list(analysis.get("agent_messages")),
            "steps": _as_list(analysis.get("steps")),
            "messages": _as_list(analysis.get("messages")),
        }

    def _normalize_watchlist_item(self, item: dict) -> dict:
        item = item if isinstance(item, dict) else {}
        stock = self._normalize_stock(item)
        item_id = str(item.get("id") or _asset_key(stock) or f"watch-{_now_ms()}")
        return {
            **item,
            **stock,
            "id": item_id,
            "name": str(item.get("name") or item.get("company") or item.get("candidate", {}).get("name") or stock.get("ticker") or "未命名标的"),
            "theme": str(item.get("theme") or item.get("signal") or ""),
            "reason": str(item.get("reason") or item.get("why") or item.get("candidate", {}).get("why") or ""),
            "risk": str(item.get("risk") or ""),
            "maturity": str(item.get("maturity") or ""),
            "added_at": item.get("added_at") or _now_ms(),
        }

    def _normalize_evidence_item(self, item: dict) -> dict:
        item = item if isinstance(item, dict) else {}
        item_id = str(item.get("id") or item.get("url") or f"evidence-{_now_ms()}")
        return {
            **item,
            "id": item_id,
            "title": str(item.get("title") or "未命名证据"),
            "source": str(item.get("source") or ""),
            "url": str(item.get("url") or ""),
            "timestamp": item.get("timestamp"),
            "theme": str(item.get("theme") or item.get("signal") or ""),
            "relatedTicker": str(item.get("relatedTicker") or item.get("ticker") or ""),
            "relatedMarket": _normalize_market(item.get("relatedMarket") or item.get("market"), item.get("relatedTicker") or item.get("ticker")),
            "snippet": str(item.get("snippet") or item.get("summary") or ""),
            "saved_at": item.get("saved_at") or _now_ms(),
        }

    def _normalize_stock(self, stock: dict) -> dict:
        stock = stock if isinstance(stock, dict) else {}
        ticker = str(stock.get("ticker") or stock.get("code") or "").strip()
        market = _normalize_market(stock.get("market"), ticker)
        return {
            "ticker": ticker,
            "market": market,
        }


def default_workspace_store() -> WorkspaceStateStore:
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.environ.get(
        "WORKSPACE_STATE_PATH",
        os.path.join(backend_dir, "data", "workspace_state.json"),
    )
    try:
        return WorkspaceStateStore(file_path=file_path, history_limit=6)
    except PermissionError:
        fallback_path = os.path.join(
            tempfile.gettempdir(),
            "consumer_alpha_radar_workspace_state.json",
        )
        return WorkspaceStateStore(file_path=fallback_path, history_limit=6)


def _normalize_market(market: Any, ticker: Any) -> str:
    ticker_text = str(ticker or "").strip()
    market_text = str(market or "").strip().upper()
    if ticker_text.isdigit() and len(ticker_text) == 6:
        return "A"
    if market_text in ("A", "HK", "US", "KR", "UNKNOWN"):
        return market_text
    if ticker_text.isdigit() and 4 <= len(ticker_text) <= 5:
        return "HK"
    return market_text or "UNKNOWN"


def _asset_key(item: dict) -> str:
    market = str(item.get("market") or "").strip().upper()
    ticker = str(item.get("ticker") or "").strip()
    if market and ticker:
        return f"{market}:{ticker}"
    return str(item.get("id") or "")


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _now_ms() -> int:
    return int(time.time() * 1000)
