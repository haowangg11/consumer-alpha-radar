export type MarketScope = "ALL" | "A" | "HK" | "US";
export type AnalysisMode = "quick" | "full";

export type ModelConfig = {
  provider: string;
  baseURL: string;
  apiKey: string;
  model: string;
};

export type StepId =
  | "parse_signal"
  | "expand_thesis"
  | "map_companies"
  | "pull_evidence"
  | "score_line"
  | "debate_round"
  | "draft_brief";

export type StepStatus = "waiting" | "running" | "done" | "warning" | "failed";

export type AnalysisStep = {
  id: StepId;
  label: string;
  status: StepStatus;
  messages: string[];
};

export type AgentStance =
  | "observation"
  | "hypothesis"
  | "mapping"
  | "evidence"
  | "market"
  | "bull"
  | "bear"
  | "review"
  | "decision";

export type AgentMessage = {
  id: string;
  agent: string;
  agent_label: string;
  stance: AgentStance;
  step: StepId;
  message: string;
  payload?: Record<string, unknown>;
};

export type CandidateExposure = "direct" | "adjacent" | "weak";

export type Candidate = {
  id: string;
  name: string;
  ticker: string;
  market: "A" | "HK" | "US" | "KR" | "UNKNOWN";
  exposure: CandidateExposure;
  why: string;
  confidence: "high" | "medium" | "low";
  quote?: {
    price?: number | null;
    change_pct?: number | null;
    pe_ttm?: number | null;
    pb?: number | null;
  };
  debate?: {
    bull?: string;
    bear?: string;
    valuation?: string;
    risk?: string;
    decision?: "track" | "pause" | "drop";
    decision_reason?: string;
  };
};

export type EvidenceKind =
  | "news"
  | "report"
  | "announcement"
  | "financial"
  | "market"
  | "risk"
  | "company";

export type EvidenceItem = {
  id: string;
  kind: EvidenceKind;
  title: string;
  source: string;
  url?: string;
  timestamp?: string;
  relatedTicker?: string;
  relevance: string;
  snippet: string;
};

export type Maturity =
  | "Emerging"
  | "Supported"
  | "Validated"
  | "Stretched"
  | "Insufficient"
  | "Broken";

export type BriefSectionId =
  | "signal_summary"
  | "consumer_thesis"
  | "investment_hypothesis"
  | "candidate_map"
  | "evidence_scorecard"
  | "risk_disconfirmation"
  | "next_verification";

export type BriefSection = {
  id: BriefSectionId;
  title: string;
  body: string;
};

export type AnalysisResult = {
  run_id: string;
  maturity: Maturity;
  sections: BriefSection[];
  candidates: Candidate[];
  evidence: EvidenceItem[];
};

export type AnalysisEvent =
  | { type: "run_started"; run_id: string }
  | { type: "step_started"; step: StepId; label: string }
  | { type: "step_delta"; step: StepId; message: string }
  | { type: "step_done"; step: StepId }
  | { type: "agent_message"; agent: string; agent_label: string; stance: AgentStance; step: StepId; message: string; payload?: Record<string, unknown> }
  | { type: "candidate_found"; candidate: Candidate }
  | { type: "evidence_found"; evidence: EvidenceItem }
  | { type: "brief_section"; section: BriefSection; maturity?: Maturity }
  | { type: "warning"; message: string; step?: StepId }
  | { type: "error"; message: string; code?: string }
  | { type: "done"; result: AnalysisResult };

export type TrendRadarItem = {
  title: string;
  url?: string;
  time?: string;
  source?: string;
  summary?: string;
  industry?: string;
  industry_key?: string;
  accent?: string;
};

export type TrendRadarTopic = {
  id: string;
  topic: string;
  heat_score: number;
  sources: string[];
  industries: string[];
  first_seen?: string;
  latest_seen?: string;
  summary: string;
  items: TrendRadarItem[];
  lifecycle: Array<{ stage: string; at?: string; note: string }>;
};

export type TrendRadarData = {
  generated_at?: string | null;
  recent_days?: number;
  source_stats?: {
    industries?: number;
    total_sources?: number;
    failed_sources?: number;
  };
  topics: TrendRadarTopic[];
};

export type StockSnapshot = {
  skill?: string;
  data?: Record<string, unknown>;
  error?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "radar" | "system";
  text: string;
};

export type AnalysisHistoryEntry = {
  id?: string;
  run_id: string;
  signal: string;
  created_at: string | number;
  updated_at?: string | number;
  maturity?: Maturity;
  entry_price?: number | string;
  entry_currency?: string;
  sections: BriefSection[];
  candidates: Candidate[];
  evidence: EvidenceItem[];
  agent_messages: AgentMessage[];
  steps?: AnalysisStep[];
  messages?: ChatMessage[];
};

export type WatchlistItem = {
  id: string;
  name: string;
  ticker: string;
  market: Candidate["market"];
  exposure?: CandidateExposure;
  confidence?: Candidate["confidence"];
  why?: string;
  signal?: string;
  theme?: string;
  entry_price?: number | string;
  entry_currency?: string;
  reason?: string;
  risk?: string;
  maturity?: Maturity;
  added_at?: string | number;
  created_at?: string | number;
  updated_at?: string | number;
};

export type SavedEvidenceItem = {
  id: string;
  kind: EvidenceKind;
  title: string;
  source: string;
  url?: string;
  timestamp?: string;
  relatedTicker?: string;
  relatedMarket?: Candidate["market"];
  relevance?: string;
  snippet: string;
  signal?: string;
  theme?: string;
  note?: string;
  saved_at?: string | number;
  created_at?: string | number;
  updated_at?: string | number;
};

export type WorkspaceState = {
  active_history_id?: string | null;
  selected_stock?: {
    market: Candidate["market"];
    ticker: string;
    name?: string;
  } | null;
  analysis_history: AnalysisHistoryEntry[];
  watchlist: WatchlistItem[];
  saved_evidence: SavedEvidenceItem[];
};

export type WorkspaceStateInput = Partial<WorkspaceState>;

export type SaveAnalysisHistoryInput = {
  signal: string;
  result: AnalysisResult;
  agent_messages?: AgentMessage[];
  steps?: AnalysisStep[];
  messages?: ChatMessage[];
};

export type WatchlistInput = {
  candidate: Candidate;
  signal?: string;
  theme?: string;
  entry_price?: number | string;
  entry_currency?: string;
  reason?: string;
  maturity?: Maturity;
  risk_summary?: string;
};

export type SavedEvidenceInput = {
  evidence: EvidenceItem;
  signal?: string;
  related_candidate?: Candidate;
  note?: string;
};
