import type {
  AnalysisEvent,
  AnalysisMode,
  MarketScope,
  ModelConfig,
  SavedEvidenceInput,
  SavedEvidenceItem,
  SaveAnalysisHistoryInput,
  StockSnapshot,
  TrendRadarData,
  WatchlistInput,
  WatchlistItem,
  WorkspaceState,
  WorkspaceStateInput
} from "./types";

export type AnalyzeInput = {
  signal: string;
  marketScope: MarketScope;
  mode: AnalysisMode;
  model: ModelConfig;
};

export async function streamConsumerAnalysis(
  input: AnalyzeInput,
  onEvent: (event: AnalysisEvent) => void,
  signal?: AbortSignal
) {
  const response = await fetch("/api/analyze-consumer-signal/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      signal: input.signal,
      market_scope: input.marketScope,
      mode: input.mode,
      llm: input.model
    }),
    signal
  });

  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || `Analyze request failed with ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) continue;
      onEvent(JSON.parse(line) as AnalysisEvent);
    }
  }

  if (buffer.trim()) {
    onEvent(JSON.parse(buffer) as AnalysisEvent);
  }
}

export async function fetchTrendRadarTopics(options: { keyword?: string; limit?: number; perTopic?: number; refresh?: boolean } = {}) {
  const params = new URLSearchParams();
  if (options.keyword) params.set("keyword", options.keyword);
  params.set("limit", String(options.limit ?? 24));
  params.set("per_topic", String(options.perTopic ?? 200));
  if (options.refresh) params.set("refresh", "true");
  const response = await fetch(`/api/trend-radar/topics?${params.toString()}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `热点雷达请求失败：${response.status}`);
  }
  return (await response.json()) as TrendRadarData;
}

export async function fetchStockSnapshot(market: string, ticker: string) {
  const stock = normalizeStockRoute(market, ticker);
  return requestJson<StockSnapshot>(
    `/api/stocks/${encodeURIComponent(stock.market)}/${encodeURIComponent(stock.ticker)}`,
    undefined,
    "个股行情请求失败"
  );
}

export async function fetchStockQuote(market: string, ticker: string) {
  const stock = normalizeStockRoute(market, ticker);
  return requestJson<StockSnapshot>(
    `/api/stocks/${encodeURIComponent(stock.market)}/${encodeURIComponent(stock.ticker)}/quote`,
    undefined,
    "价格快照请求失败"
  );
}

export async function fetchStockKline(market: string, ticker: string) {
  const stock = normalizeStockRoute(market, ticker);
  return requestJson<StockSnapshot>(
    `/api/stocks/${encodeURIComponent(stock.market)}/${encodeURIComponent(stock.ticker)}/kline`,
    undefined,
    "K 线请求失败"
  );
}

function normalizeStockRoute(market: string, ticker: string) {
  const rawTicker = ticker.trim().toUpperCase();
  const rawMarket = market.trim().toUpperCase();
  const suffixMatch = rawTicker.match(/^(.+?)\.(SH|SZ|BJ|HK|US)$/);
  const normalizedTicker = suffixMatch ? suffixMatch[1] : rawTicker;
  const suffix = suffixMatch?.[2];
  if (/^\d{6}$/.test(normalizedTicker) && (suffix === "SH" || suffix === "SZ" || suffix === "BJ" || rawMarket === "A" || !rawMarket)) {
    return { market: "A", ticker: normalizedTicker };
  }
  if (/^\d{4,5}$/.test(normalizedTicker) && (suffix === "HK" || rawMarket === "HK" || !rawMarket)) {
    return { market: "HK", ticker: normalizedTicker };
  }
  if (suffix === "US") return { market: "US", ticker: normalizedTicker };
  return { market: rawMarket || "UNKNOWN", ticker: normalizedTicker };
}

async function requestJson<T>(url: string, init?: RequestInit, fallbackMessage = "请求失败") {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${fallbackMessage}：${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function fetchWorkspaceState() {
  return requestJson<WorkspaceState>("/api/workspace/state", undefined, "读取雷达工作区失败");
}

export async function saveWorkspaceState(state: WorkspaceStateInput) {
  return requestJson<WorkspaceState>(
    "/api/workspace/state",
    {
      method: "PUT",
      body: JSON.stringify({ state })
    },
    "保存雷达工作区失败"
  );
}

export async function saveAnalysisHistory(input: SaveAnalysisHistoryInput) {
  const analysis = {
    run_id: input.result.run_id,
    signal: input.signal,
    maturity: input.result.maturity,
    sections: input.result.sections,
    candidates: input.result.candidates,
    evidence: input.result.evidence,
    agent_messages: input.agent_messages || [],
    steps: input.steps || [],
    messages: input.messages || []
  };
  return requestJson<WorkspaceState>(
    "/api/workspace/history",
    {
      method: "POST",
      body: JSON.stringify({ analysis })
    },
    "保存分析历史失败"
  );
}

export async function deleteAnalysisHistory(historyId: string) {
  return requestJson<WorkspaceState>(
    `/api/workspace/history/${encodeURIComponent(historyId)}`,
    { method: "DELETE" },
    "删除分析历史失败"
  );
}

export async function addWatchlistItem(input: WatchlistInput) {
  const item = {
    ...input.candidate,
    signal: input.signal,
    reason: input.reason || input.candidate.why,
    maturity: input.maturity,
    risk: input.risk_summary
  };
  return requestJson<WorkspaceState>(
    "/api/workspace/watchlist",
    {
      method: "POST",
      body: JSON.stringify({ item })
    },
    "加入观察清单失败"
  );
}

export async function removeWatchlistItem(itemId: string) {
  return requestJson<WorkspaceState>(
    `/api/workspace/watchlist/${encodeURIComponent(itemId)}`,
    { method: "DELETE" },
    "移出观察清单失败"
  );
}

export async function saveEvidenceItem(input: SavedEvidenceInput) {
  const item = {
    ...input.evidence,
    signal: input.signal,
    note: input.note,
    relatedMarket: input.related_candidate?.market,
    relatedTicker: input.related_candidate?.ticker || input.evidence.relatedTicker
  };
  return requestJson<WorkspaceState>(
    "/api/workspace/evidence",
    {
      method: "POST",
      body: JSON.stringify({ item })
    },
    "保存证据失败"
  );
}

export async function removeEvidenceItem(itemId: string) {
  return requestJson<WorkspaceState>(
    `/api/workspace/evidence/${encodeURIComponent(itemId)}`,
    { method: "DELETE" },
    "删除证据失败"
  );
}
