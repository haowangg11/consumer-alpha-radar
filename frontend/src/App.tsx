import {
  AppleLogo,
  ArrowRight,
  BookmarkSimple,
  Brain,
  Buildings,
  CaretDown,
  ChartLine,
  CheckCircle,
  ChatCircleText,
  CircleNotch,
  Database,
  FileText,
  Fire,
  GearSix,
  Gauge,
  House,
  ListChecks,
  MagnifyingGlass,
  Moon,
  Newspaper,
  SealWarning,
  SidebarSimple,
  Sparkle,
  Sun,
  Trash,
  UsersThree,
  X
} from "@phosphor-icons/react";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import {
  addWatchlistItem,
  deleteAnalysisHistory,
  fetchStockKline,
  fetchStockQuote,
  fetchStockSnapshot,
  fetchTrendRadarTopics,
  fetchWorkspaceState,
  removeEvidenceItem,
  removeWatchlistItem,
  saveAnalysisHistory,
  saveEvidenceItem,
  streamConsumerAnalysis
} from "./api";
import type {
  AnalysisEvent,
  AnalysisHistoryEntry,
  AnalysisMode,
  AnalysisResult,
  AnalysisStep,
  AgentMessage,
  AgentStance,
  BriefSection,
  Candidate,
  EvidenceItem,
  MarketScope,
  Maturity,
  ModelConfig,
  SavedEvidenceItem,
  StockSnapshot,
  StepId,
  TrendRadarTopic,
  WatchlistItem,
  WorkspaceState
} from "./types";

const initialSteps: AnalysisStep[] = [
  { id: "parse_signal", label: "解析信号", status: "waiting", messages: [] },
  { id: "expand_thesis", label: "扩展假设", status: "waiting", messages: [] },
  { id: "map_companies", label: "映射公司", status: "waiting", messages: [] },
  { id: "pull_evidence", label: "拉取证据", status: "waiting", messages: [] },
  { id: "score_line", label: "评估成熟度", status: "waiting", messages: [] },
  { id: "debate_round", label: "多空研讨", status: "waiting", messages: [] },
  { id: "draft_brief", label: "生成简报", status: "waiting", messages: [] }
];

const defaultModel: ModelConfig = {
  provider: "deepseek",
  baseURL: "https://api.deepseek.com/v1",
  apiKey: "",
  model: "deepseek-chat"
};

type ChatMessage = {
  id: string;
  role: "user" | "radar" | "system";
  text: string;
};

type ViewId = "radar" | "trend" | "briefs" | "agents" | "evidence" | "stocks" | "watchlist";
type StockRef = { market: Candidate["market"]; ticker: string; name?: string };
type CandidateDecision = NonNullable<Candidate["debate"]>["decision"];
type StockLike = Pick<Candidate, "ticker" | "market" | "name">;
type CompanyLike = Pick<Candidate, "ticker" | "market"> & { name?: string };

const navItems: Array<{ id: ViewId; label: string; icon: typeof House }> = [
  { id: "radar", label: "雷达首页", icon: House },
  { id: "trend", label: "热点雷达", icon: Newspaper },
  { id: "briefs", label: "机会简报", icon: FileText },
  { id: "agents", label: "研讨室", icon: UsersThree },
  { id: "evidence", label: "证据库", icon: Database },
  { id: "stocks", label: "个股行情", icon: ChartLine },
  { id: "watchlist", label: "观察清单", icon: ListChecks }
];

const uiTranslations: Record<string, string> = {
  "雷达首页": "Radar Home",
  "热点雷达": "Trend Radar",
  "机会简报": "Opportunity Brief",
  "研讨室": "Research Room",
  "证据库": "Evidence Library",
  "个股行情": "Stock Quotes",
  "观察清单": "Watchlist",
  "研究工具箱": "Research Toolbox",
  "公司对比": "Company Comparison",
  "横向比较标的": "Compare candidates",
  "趋势追踪": "Trend Tracking",
  "追踪主题变化": "Track theme changes",
  "证据时间线": "Evidence Timeline",
  "梳理事件脉络": "Review event history",
  "验证清单": "Validation Checklist",
  "管理待验证项": "Manage validations",
  "设置": "Settings",
  "模型与终端配置": "Model & Terminal",
  "模型": "Model",
  "数据源": "Data Sources",
  "外观": "Appearance",
  "强调色": "Accent Color",
  "背景色": "Background Color",
  "跟随主题": "Follow Theme",
  "浅色": "Light",
  "深色": "Dark",
  "中文": "Chinese",
  "自定义": "Custom",
  "恢复默认蓝色": "Reset Blue",
  "语言 / Language": "Language",
  "关键证据": "Key Evidence",
  "查看证据库": "Open Evidence Library",
  "候选 Top": "Top Candidates",
  "打开个股行情": "Open Stock Quotes",
  "风险与下一步": "Risks & Next Steps",
  "深读入口": "Explore More"
};

function uiText(text: string, language: "zh" | "en") {
  return language === "en" ? (uiTranslations[text] || text) : text;
}

function summarizeWatchTheme(signal?: string) {
  const value = (signal || "").replace(/\s+/g, " ").trim();
  if (!value) return "未分类主题";
  const explicit = value.match(/主题\s*[：:]\s*([^；。\-]+?)(?=\s+(?:热度|摘要|信息|$))/);
  const cleaned = (explicit?.[1] || value.split(/[。；\n]/)[0])
    .replace(/^(请基于|请围绕|基于).{0,28}(生成|分析|研究)[：:]?/i, "")
    .trim();
  const compact = cleaned || "未分类主题";
  return `${compact.slice(0, 18)}${compact.length > 18 ? "…" : ""}`;
}

function loadModelConfig(): ModelConfig {
  try {
    const stored = JSON.parse(localStorage.getItem("car:model") || "{}") as Partial<ModelConfig>;
    return {
      ...defaultModel,
      ...stored,
      provider: stored.provider || defaultModel.provider,
      baseURL: stored.baseURL || defaultModel.baseURL,
      model: stored.model || defaultModel.model,
      apiKey: stored.apiKey || ""
    };
  } catch {
    return defaultModel;
  }
}

function saveModelConfig(config: ModelConfig) {
  localStorage.setItem("car:model", JSON.stringify(config));
}

type AppearanceConfig = {
  theme: "light" | "dark";
  accent: string;
  background: string | null;
};

const APPEARANCE_STORAGE_KEY = "car:appearance:v2";
const defaultAppearance: AppearanceConfig = { theme: "light", accent: "#0a84ff", background: null };
const accentPresets = ["#0a84ff", "#5856d6", "#00a6a6", "#248a3d", "#bf5af2", "#ff7a1a"];
const backgroundPresets = ["#ffffff", "#eaf2f8", "#edf1ed", "#f3eef6", "#f5f0e8", "#171d27"];

function loadAppearance(): AppearanceConfig {
  try {
    const stored = JSON.parse(localStorage.getItem(APPEARANCE_STORAGE_KEY) || "{}") as Partial<AppearanceConfig>;
    return {
      theme: stored.theme === "dark" ? "dark" : "light",
      accent: /^#[0-9a-f]{6}$/i.test(stored.accent || "") ? stored.accent! : defaultAppearance.accent,
      background: /^#[0-9a-f]{6}$/i.test(stored.background || "") ? stored.background! : null
    };
  } catch {
    return defaultAppearance;
  }
}

function hexToRgb(hex: string) {
  const value = hex.replace("#", "");
  return [0, 2, 4].map((offset) => Number.parseInt(value.slice(offset, offset + 2), 16));
}

function mixHex(base: string, target: string, amount: number) {
  const baseRgb = hexToRgb(base);
  const targetRgb = hexToRgb(target);
  const mixed = baseRgb.map((value, index) => Math.round(value + (targetRgb[index] - value) * amount));
  return `#${mixed.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function updateStep(steps: AnalysisStep[], id: StepId, patch: Partial<AnalysisStep>, message?: string) {
  return steps.map((step) =>
    step.id === id
      ? { ...step, ...patch, messages: message ? [...step.messages, message] : step.messages }
      : step
  );
}

function mergeCandidateList(candidates: Candidate[], next: Candidate) {
  if (!candidates.some((item) => item.id === next.id)) return [...candidates, next];
  return candidates.map((item) => (item.id === next.id ? { ...item, ...next, quote: next.quote || item.quote, debate: next.debate || item.debate } : item));
}

function candidateKey(candidate: StockLike) {
  const stock = normalizeStockRef(candidate);
  return `${stock.market}:${stock.ticker || stock.name}`.toLowerCase();
}

function findCandidateByTicker(candidates: Candidate[], ticker?: string) {
  if (!ticker) return undefined;
  const normalizedTicker = normalizeStockRef({ ticker, market: "UNKNOWN", name: "" }).ticker;
  return candidates.find((candidate) => normalizeStockRef(candidate).ticker === normalizedTicker);
}

function normalizeStockRef(stock: CompanyLike): StockRef {
  const rawTicker = (stock.ticker || "").trim().toUpperCase();
  const rawMarket = (stock.market || "").trim().toUpperCase();
  const suffixMatch = rawTicker.match(/^(.+?)\.(SH|SZ|BJ|HK|US)$/);
  const ticker = suffixMatch ? suffixMatch[1] : rawTicker;
  const suffix = suffixMatch?.[2];
  if (/^\d{6}$/.test(ticker) && (suffix === "SH" || suffix === "SZ" || suffix === "BJ" || rawMarket === "A" || !rawMarket)) {
    return { market: "A", ticker, name: stock.name };
  }
  if (/^\d{4,5}$/.test(ticker) && (suffix === "HK" || rawMarket === "HK" || !rawMarket)) {
    return { market: "HK", ticker, name: stock.name };
  }
  if (suffix === "US") return { market: "US", ticker, name: stock.name };
  return { market: (rawMarket as StockRef["market"]) || "UNKNOWN", ticker, name: stock.name };
}

const companyIconOverrides: Record<string, { label: string; color: string; shape?: "circle" }> = {
  AAPL: { label: "A", color: "#111111", shape: "circle" },
  GOOGL: { label: "G", color: "#4285f4" },
  GOOG: { label: "G", color: "#4285f4" },
  MSFT: { label: "M", color: "#0078d4" },
  AMZN: { label: "a", color: "#ff9900" },
  META: { label: "M", color: "#0866ff" },
  TSLA: { label: "T", color: "#e82127" },
  NVDA: { label: "N", color: "#76b900" },
  QCOM: { label: "Q", color: "#3253dc" },
  "1810": { label: "mi", color: "#ff6900" },
  "005930": { label: "S", color: "#1428a0" }
};

function CompanyIcon({ company, size = "medium" }: { company: CompanyLike; size?: "small" | "medium" | "large" }) {
  const stock = normalizeStockRef(company);
  const key = stock.ticker.toUpperCase().split(".")[0];
  const override = companyIconOverrides[key];
  const fallback = (key || company.name || "?").replace(/[^a-z0-9]/gi, "").slice(0, 2).toUpperCase() || "?";
  const palette = ["#3478f6", "#00a6a6", "#5856d6", "#248a3d", "#bf5af2", "#d97706"];
  const hash = [...`${key}${company.name || ""}`].reduce((total, character) => total + character.charCodeAt(0), 0);
  const color = override?.color || palette[hash % palette.length];
  return (
    <span
      className={`company-icon ${size}`}
      data-shape={override?.shape || "square"}
      style={{ "--company-color": color } as CSSProperties}
      aria-hidden="true"
    >
      {key === "AAPL" ? <AppleLogo weight="fill" /> : override?.label || fallback}
    </span>
  );
}

function watchlistToCandidate(item: WatchlistItem): Candidate {
  return {
    id: item.id || candidateKey(item),
    name: item.name,
    ticker: item.ticker,
    market: normalizeStockRef(item).market,
    exposure: item.exposure || "weak",
    why: item.reason || item.why || item.theme || "观察清单标的",
    confidence: item.confidence || "medium"
  };
}

function savedEvidenceToEvidence(item: SavedEvidenceItem): EvidenceItem {
  return {
    id: item.id,
    kind: item.kind,
    title: item.title,
    source: item.source,
    url: item.url,
    timestamp: item.timestamp,
    relatedTicker: item.relatedTicker,
    relevance: item.relevance || item.note || "",
    snippet: item.snippet || ""
  };
}

function maturityClass(maturity?: Maturity) {
  return `maturity ${(maturity || "Insufficient").toLowerCase()}`;
}

function translateMaturity(maturity?: Maturity) {
  const labels: Record<Maturity, string> = {
    Emerging: "萌芽",
    Supported: "有支撑",
    Validated: "已验证",
    Stretched: "偏拥挤",
    Insufficient: "证据不足",
    Broken: "已证伪"
  };
  return labels[maturity || "Insufficient"];
}

const consumerPromptLibrary = (() => {
  const categories = [
    "美妆护肤",
    "医美修复",
    "胶原蛋白",
    "功能饮料",
    "零糖食品",
    "宠物食品",
    "母婴用品",
    "潮玩 IP",
    "黄金珠宝",
    "运动户外",
    "家清个护",
    "小家电",
    "咖啡茶饮",
    "烘焙零食",
    "保健品",
    "香氛香水",
    "服饰鞋包",
    "便利店新品",
    "直播电商",
    "会员店消费"
  ];
  const researchAngles = [
    "最近有什么消费信号值得追踪？",
    "可能对应哪些上市公司？",
    "怎么拆成品牌、渠道、原料和代工链？",
    "最应该先验证哪三条证据？",
    "哪些信号可能只是短期噪音？",
    "如果要做成一条研究线，第一步看什么？",
    "哪些公司是直接受益，哪些只是相邻受益？",
    "估值风险应该怎么判断？"
  ];
  const signalPrompts = categories.flatMap((category) => researchAngles.map((angle) => `${category}${angle}`));
  const scenarioPrompts = [
    "小红书突然刷屏的消费品，怎么判断是不是投资机会？",
    "抖音爆品热度很高，怎么避免误判成长期需求？",
    "线下门店排队很长，应该映射到哪些公司和证据？",
    "一个品牌频繁上新，应该看新品还是看渠道？",
    "一个消费品涨价，应该先看品牌力还是成本压力？",
    "一个国货品牌开始出海，应该追踪哪些上市公司？",
    "一个消费品被达人集中推荐，怎么判断是不是投放驱动？",
    "一个新品复购很强，哪些财务指标会最先反映？",
    "一个消费趋势从一线城市下沉，应该看哪些渠道公司？",
    "一个消费品从线上走到线下，哪些公司可能受益？",
    "一个品牌突然被质疑安全性，应该先看哪些公告和舆情？",
    "一个品类出现平替潮，头部品牌和代工厂谁更受益？",
    "一个高端消费品降价，说明需求变弱还是渗透率提升？",
    "一个产品从小众圈层破圈，应该怎么设验证节点？",
    "一个品牌进入会员店，可能意味着什么？",
    "一个产品在即时零售卖得好，应该追踪哪些公司？",
    "一个消费品类开始做联名，是真增长还是营销热？",
    "一个老品牌重新变年轻，投资线索应该怎么拆？",
    "一个品牌关闭门店，可能是风险还是渠道调整？",
    "一个品类监管变严，谁可能受损，谁可能受益？",
    "如果我只知道一个产品名字，怎么找到上市公司线索？",
    "如果我只有一条新闻，怎么判断证据强弱？",
    "如果候选公司很多，怎么先筛掉弱相关标的？",
    "如果一个公司估值很高，还值得继续跟踪吗？",
    "如果消费热度很强但财报没体现，应该怎么处理？",
    "怎么把当前消费观察转成观察清单？",
    "怎么把一个品牌故事转成可验证的证据链？",
    "怎么判断爆品是否能传导到上市公司利润？",
    "怎么区分品牌受益和原料供应商受益？",
    "怎么区分渠道红利和产品力红利？",
    "哪些消费品信号更适合 A 股？",
    "哪些消费品信号更适合港股？",
    "哪些消费品信号可能映射到美股？",
    "一个消费品机会最强的反方证据通常是什么？",
    "当前研究线最可能缺哪类数据？",
    "把一个消费信号拆成多头、空头和估值三段",
    "帮我生成一个消费品研究 checklist",
    "帮我把当前问题改写得更适合雷达分析",
    "帮我找一个更窄的消费品切入点",
    "帮我判断这是不是消费者真实需求"
  ];
  return Array.from(new Set([...signalPrompts, ...scenarioPrompts]));
})();

function buildPilotPrompts(
  viewTitle: string,
  candidates: Candidate[],
  evidence: EvidenceItem[],
  sections: BriefSection[]
) {
  const viewPrompts: string[] = [];
  if (candidates.length) {
    const leader = candidates[0];
    viewPrompts.push(
      `解释为什么 ${leader.name} 和当前消费信号有关`,
      `质疑当前机会假设，找出最强反方证据`,
      `基于 ${evidence.length} 条证据，判断这条研究线是否值得继续跟踪`,
      `比较 ${candidates.slice(0, 3).map((candidate) => candidate.name).join("、")} 谁更值得继续看`,
      `帮我找出 ${leader.name} 这条线最大的估值风险`,
      `把 ${leader.name} 的多头和空头观点重新整理一下`,
      `${leader.name} 当前最需要补哪一类证据？`,
      `如果要剔除一个候选公司，应该先剔除谁？`,
      `把这些候选公司按直接受益程度重新排序`
    );
  }
  if (sections.length) {
    viewPrompts.push(
      "总结当前机会简报",
      "找出这份简报里证据最弱的一环",
      "下一步应该验证什么？",
      "把这份简报压缩成三句话",
      "把当前机会假设改写成可验证清单",
      "这份简报里哪句话最像未经验证的假设？",
      "把当前结论改写成观察清单条目",
      "如果我要继续研究，今天应该先看什么？"
    );
  }
  if (viewTitle === "热点雷达") {
    viewPrompts.push(
      "从当前消费资讯里找一个值得分析的信号",
      "解释当前热点可能对应哪些消费品类",
      "把选中的资讯转成消费投资假设",
      "哪些热点更像短期噪音？",
      "从这些资讯里筛一个最适合继续跑的消费品",
      "这些资讯里有没有品牌、渠道或新品信号？",
      "帮我把热点按美妆、食品、零售、宠物归类",
      "从热点里挑一个最像消费品机会的主题"
    );
  }
  if (viewTitle === "证据库") {
    viewPrompts.push("证据库里哪条证据最关键？", "哪些证据不足以支持当前结论？", "帮我按公司归纳证据链");
  }
  if (viewTitle === "个股行情") {
    viewPrompts.push("结合行情页解释这个标的的问题", "这只股票现在最大的估值压力是什么？", "把行情、财务和研讨结论合起来看");
  }
  return Array.from(new Set([...viewPrompts, ...consumerPromptLibrary]));
}

const sectionOrder: BriefSection["id"][] = [
  "signal_summary",
  "consumer_thesis",
  "investment_hypothesis",
  "candidate_map",
  "evidence_scorecard",
  "risk_disconfirmation",
  "next_verification"
];

const emptyWorkspaceState: WorkspaceState = {
  analysis_history: [],
  watchlist: [],
  saved_evidence: [],
  selected_stock: null
};

export function App() {
  const initialAppearance = useMemo(loadAppearance, []);
  const [theme, setTheme] = useState<"light" | "dark">(initialAppearance.theme);
  const [accent, setAccent] = useState(initialAppearance.accent);
  const [background, setBackground] = useState<string | null>(initialAppearance.background);
  const [language, setLanguage] = useState<"zh" | "en">(() => localStorage.getItem("car:language") === "en" ? "en" : "zh");
  const [activeView, setActiveView] = useState<ViewId>("radar");
  const [pilotOpen, setPilotOpen] = useState(true);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [modelConfig, setModelConfig] = useState<ModelConfig>(loadModelConfig);
  const [signal, setSignal] = useState("");
  const marketScope: MarketScope = "ALL";
  const mode: AnalysisMode = "full";
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "radar",
      text: "输入一个消费品、品牌、消费场景或资讯线索，我会把它转成可验证的上市公司研究线。"
    }
  ]);
  const [steps, setSteps] = useState<AnalysisStep[]>(initialSteps);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [sections, setSections] = useState<BriefSection[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [savedEvidence, setSavedEvidence] = useState<SavedEvidenceItem[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisHistoryEntry[]>([]);
  const [maturity, setMaturity] = useState<Maturity | undefined>();
  const [activeEvidenceKind, setActiveEvidenceKind] = useState("all");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState<StockRef | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const activeSignalRef = useRef("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const [red, green, blue] = hexToRgb(accent);
    document.documentElement.style.setProperty("--accent", accent);
    document.documentElement.style.setProperty("--accent-soft", `rgba(${red}, ${green}, ${blue}, ${theme === "dark" ? 0.16 : 0.1})`);
    if (background) {
      const isDarkBackground = hexToRgb(background).reduce((sum, value) => sum + value, 0) < 330;
      document.documentElement.dataset.customBackground = "true";
      document.documentElement.style.setProperty("--custom-bg", background);
      document.documentElement.style.setProperty("--custom-paper", mixHex(background, isDarkBackground ? "#ffffff" : "#ffffff", isDarkBackground ? 0.07 : 0.58));
    } else {
      delete document.documentElement.dataset.customBackground;
      document.documentElement.style.removeProperty("--custom-bg");
      document.documentElement.style.removeProperty("--custom-paper");
    }
    localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify({ theme, accent, background }));
  }, [theme, accent, background]);

  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "zh-CN";
    localStorage.setItem("car:language", language);
  }, [language]);

  useEffect(() => {
    saveModelConfig(modelConfig);
  }, [modelConfig]);

  useEffect(() => {
    let alive = true;
    fetchWorkspaceState()
      .then((state) => {
        if (!alive) return;
        applyWorkspaceState(state);
        const latest = state.analysis_history?.[0];
        if (latest) restoreAnalysis(latest);
      })
      .catch((error) => {
        if (!alive) return;
        const message = error instanceof Error ? error.message : "读取雷达工作区失败";
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", text: message }]);
      });
    return () => {
      alive = false;
    };
  }, []);

  const filteredEvidence = useMemo(() => {
    if (activeEvidenceKind === "all") return evidence;
    return evidence.filter((item) => item.kind === activeEvidenceKind);
  }, [activeEvidenceKind, evidence]);

  async function analyze() {
    const trimmed = signal.trim();
    if (!trimmed || status === "running") return;

    setActiveView("radar");
    activeSignalRef.current = trimmed;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("running");
    setRunId(null);
    setSteps(initialSteps);
    setAgentMessages([]);
    setSections([]);
    setCandidates([]);
    setEvidence([]);
    setMaturity(undefined);
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", text: trimmed },
      { id: crypto.randomUUID(), role: "radar", text: "开始调用真实数据源。我会按步骤流式返回解析、公司映射、证据和简报。" }
    ]);
    setSignal("");

    try {
      await streamConsumerAnalysis({ signal: trimmed, marketScope, mode, model: modelConfig }, handleEvent, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : "Analyze request failed.";
      setStatus("error");
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", text: message }]);
    }
  }

  function handleEvent(event: AnalysisEvent) {
    if (event.type === "run_started") setRunId(event.run_id);
    if (event.type === "step_started") setSteps((prev) => updateStep(prev, event.step, { status: "running" }, event.label));
    if (event.type === "step_delta") {
      setSteps((prev) => updateStep(prev, event.step, {}, event.message));
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "radar", text: event.message }]);
    }
    if (event.type === "step_done") setSteps((prev) => updateStep(prev, event.step, { status: "done" }));
    if (event.type === "agent_message") {
      setAgentMessages((prev) => [
        ...prev,
        {
          id: `${event.agent}-${event.step}-${prev.length}`,
          agent: event.agent,
          agent_label: event.agent_label,
          stance: event.stance,
          step: event.step,
          message: event.message,
          payload: event.payload
        }
      ]);
    }
    if (event.type === "candidate_found") {
      setCandidates((prev) => mergeCandidateList(prev, event.candidate));
    }
    if (event.type === "evidence_found") {
      setEvidence((prev) => (prev.some((item) => item.id === event.evidence.id) ? prev : [...prev, event.evidence]));
    }
    if (event.type === "brief_section") {
      setSections((prev) => [...prev.filter((section) => section.id !== event.section.id), event.section]);
      if (event.maturity) setMaturity(event.maturity);
    }
    if (event.type === "warning") {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", text: event.message }]);
      if (event.step) setSteps((prev) => updateStep(prev, event.step!, { status: "warning" }));
    }
    if (event.type === "error") {
      setStatus("error");
      if (event.code === "needs_model") setPreferencesOpen(true);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", text: event.message }]);
    }
    if (event.type === "done") {
      setStatus("done");
      applyResult(event.result);
    }
  }

  function applyResult(result: AnalysisResult) {
    setRunId(result.run_id);
    setMaturity(result.maturity);
    setSections(result.sections);
    setCandidates(result.candidates);
    setEvidence(result.evidence);
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "radar", text: "消费机会简报已生成。" }]);
    void saveAnalysisHistory({
      signal: activeSignalRef.current,
      result,
      agent_messages: agentMessages,
      steps,
      messages
    }).then(applyWorkspaceState).catch((error) => {
      const message = error instanceof Error ? error.message : "保存分析历史失败";
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", text: message }]);
    });
  }

  function applyWorkspaceState(state: WorkspaceState) {
    const normalized = { ...emptyWorkspaceState, ...state };
    setAnalysisHistory(normalized.analysis_history || []);
    setWatchlist(normalized.watchlist || []);
    setSavedEvidence(normalized.saved_evidence || []);
    if (normalized.selected_stock?.ticker) setSelectedStock(normalized.selected_stock);
  }

  function restoreAnalysis(record: AnalysisHistoryEntry) {
    activeSignalRef.current = record.signal || "";
    setRunId(record.run_id);
    setStatus("done");
    setMaturity(record.maturity);
    setSections(record.sections || []);
    setCandidates(record.candidates || []);
    setEvidence(record.evidence || []);
    setAgentMessages(record.agent_messages || []);
    setSteps(record.steps?.length ? record.steps : initialSteps);
    setMessages(record.messages?.length ? record.messages : [
      {
        id: `history-${record.run_id}`,
        role: "radar",
        text: record.signal ? `已恢复最近一次分析：${record.signal}` : "已恢复最近一次分析。"
      }
    ]);
  }

  const viewTitle = navItems.find((item) => item.id === activeView)?.label || "雷达首页";
  const stockCandidates = candidates.length ? candidates : watchlist.map(watchlistToCandidate);
  const openStock = (candidate: StockLike) => {
    if (!candidate.ticker) return;
    setSelectedStock(normalizeStockRef(candidate));
    setActiveView("stocks");
  };
  const saveEvidence = (item: EvidenceItem) => {
    const relatedCandidate = findCandidateByTicker(candidates, item.relatedTicker);
    void saveEvidenceItem({ evidence: item, signal: activeSignalRef.current, related_candidate: relatedCandidate }).then(applyWorkspaceState);
  };
  const removeEvidence = (id: string) => {
    void removeEvidenceItem(id).then(applyWorkspaceState);
  };
  const addToWatchlist = (candidate: Candidate) => {
    if (!candidate.ticker) return;
    void addWatchlistItem({
      candidate: { ...candidate, ...normalizeStockRef(candidate) },
      signal: activeSignalRef.current,
      theme: summarizeWatchTheme(activeSignalRef.current),
      entry_price: candidate.quote?.price ?? undefined,
      entry_currency: candidate.market === "HK" ? "HKD" : candidate.market === "US" ? "USD" : "CNY",
      reason: candidate.debate?.decision_reason || candidate.why,
      maturity,
      risk_summary: candidate.debate?.risk
    }).then(applyWorkspaceState);
  };
  const removeFromWatchlist = (candidate: StockLike) => {
    void removeWatchlistItem(candidateKey(candidate).toUpperCase()).then(applyWorkspaceState);
  };
  const removeHistory = (record: AnalysisHistoryEntry) => {
    void deleteAnalysisHistory(record.run_id).then(applyWorkspaceState);
  };
  const isInWatchlist = (candidate: Candidate) => watchlist.some((item) => candidateKey(item) === candidateKey(candidate));
  const isEvidenceSaved = (item: EvidenceItem) => savedEvidence.some((saved) => saved.id === item.id);

  return (
    <div className="terminal-shell">
      <SideNav
        activeView={activeView}
        setActiveView={setActiveView}
        onPreferences={() => setPreferencesOpen(true)}
      />
      <section className="terminal-main">
      <TopBar
        viewTitle={viewTitle}
        language={language}
        theme={theme}
        onThemeToggle={() => setTheme(theme === "light" ? "dark" : "light")}
        onPilotToggle={() => setPilotOpen((value) => !value)}
      />
      <main className="workspace-page">
        {activeView === "radar" && (
          <RadarHome
            sections={sections}
            maturity={maturity}
            candidates={candidates}
            evidence={evidence}
            status={status}
            runId={runId}
            steps={steps}
            onOpenStock={openStock}
            onOpenView={setActiveView}
            onSaveEvidence={saveEvidence}
            onAddToWatchlist={addToWatchlist}
            analysisHistory={analysisHistory}
            onRestoreHistory={restoreAnalysis}
            onDeleteHistory={removeHistory}
            isEvidenceSaved={isEvidenceSaved}
            isInWatchlist={isInWatchlist}
          />
        )}
        {activeView === "trend" && (
          <TrendRadarPage
            onSendToPilot={(prompt) => {
              setSignal(prompt);
              setPilotOpen(true);
            }}
          />
        )}
        {activeView === "briefs" && (
          <BriefCanvas
            sections={sections}
            maturity={maturity}
            candidates={candidates}
            status={status}
            runId={runId}
            onOpenStock={openStock}
            onAddToWatchlist={addToWatchlist}
            isInWatchlist={isInWatchlist}
          />
        )}
        {activeView === "agents" && <AgentRoomPage steps={steps} agentMessages={agentMessages} candidates={candidates} evidence={evidence} maturity={maturity} status={status} />}
        {activeView === "evidence" && (
          <EvidenceInspector
            evidence={savedEvidence.filter((item) => activeEvidenceKind === "all" || item.kind === activeEvidenceKind)}
            allEvidence={savedEvidence}
            currentEvidence={filteredEvidence}
            activeKind={activeEvidenceKind}
            setActiveKind={setActiveEvidenceKind}
            candidates={candidates}
            status={status}
            onSaveEvidence={saveEvidence}
            onRemoveEvidence={removeEvidence}
            onOpenStock={openStock}
            isEvidenceSaved={isEvidenceSaved}
          />
        )}
        {activeView === "stocks" && <StocksPage candidates={stockCandidates} selectedStock={selectedStock} setSelectedStock={setSelectedStock} onAddToWatchlist={addToWatchlist} isInWatchlist={isInWatchlist} />}
        {activeView === "watchlist" && <WatchlistPage watchlist={watchlist} onOpenStock={openStock} onRemove={removeFromWatchlist} />}
      </main>
      </section>
      <PilotDock
        open={pilotOpen}
        setOpen={setPilotOpen}
        signal={signal}
        setSignal={setSignal}
        messages={messages}
        status={status}
        viewTitle={viewTitle}
        candidates={candidates}
        evidence={evidence}
        sections={sections}
        onAnalyze={analyze}
      />
      <AnimatePresence>
        {preferencesOpen && (
          <PreferencesSheet
            modelConfig={modelConfig}
            setModelConfig={setModelConfig}
            theme={theme}
            setTheme={setTheme}
            accent={accent}
            setAccent={setAccent}
            background={background}
            setBackground={setBackground}
            language={language}
            setLanguage={setLanguage}
            onClose={() => setPreferencesOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function SideNav({
  activeView,
  setActiveView,
  onPreferences
}: {
  activeView: ViewId;
  setActiveView: (view: ViewId) => void;
  onPreferences: () => void;
}) {
  return (
    <aside className="side-nav">
      <div className="side-brand">
        <div className="brand-mark">
          <img src="/brand-cat.png" alt="消费雷达" />
        </div>
        <div>
          <strong>消费雷达</strong>
          <span className="side-brand-subtitle">Consumer Alpha Radar</span>
        </div>
      </div>
      <nav className="nav-list">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={activeView === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setActiveView(item.id)}
            >
              <Icon size={17} />
              <span>
                <strong>{item.label}</strong>
              </span>
            </button>
          );
        })}
      </nav>
      <div className="side-settings">
        <button onClick={onPreferences} aria-label="打开系统设置">
          <GearSix size={17} />
          <strong>系统设置</strong>
        </button>
      </div>
    </aside>
  );
}

function TopBar({
  viewTitle,
  language,
  theme,
  onThemeToggle,
  onPilotToggle
}: {
  viewTitle: string;
  language: "zh" | "en";
  theme: "light" | "dark";
  onThemeToggle: () => void;
  onPilotToggle: () => void;
}) {
  return (
    <header className="top-bar">
      <div className="brand-lockup">
        <button className="icon-button" onClick={onPilotToggle} aria-label="打开或收起雷达助手">
          <SidebarSimple size={18} />
        </button>
        <div>
          <strong>{uiText(viewTitle, language)}</strong>
        </div>
      </div>
      <div className="top-actions">
        <button className="icon-button" onClick={onThemeToggle} aria-label="切换主题">{theme === "light" ? <Moon size={18} /> : <Sun size={18} />}</button>
      </div>
    </header>
  );
}

function PilotDock({
  open,
  setOpen,
  signal,
  setSignal,
  messages,
  status,
  viewTitle,
  candidates,
  evidence,
  sections,
  onAnalyze
}: {
  open: boolean;
  setOpen: (value: boolean) => void;
  signal: string;
  setSignal: (value: string) => void;
  messages: ChatMessage[];
  status: string;
  viewTitle: string;
  candidates: Candidate[];
  evidence: EvidenceItem[];
  sections: BriefSection[];
  onAnalyze: () => void;
}) {
  const promptPool = useMemo(
    () => buildPilotPrompts(viewTitle, candidates, evidence, sections),
    [viewTitle, candidates, evidence, sections]
  );
  const [promptCursor, setPromptCursor] = useState(0);
  const isPromptRotationPaused = Boolean(signal.trim()) || status === "running";
  const pilotState = status === "error"
    ? "risk"
    : status === "done"
      ? "complete"
      : status === "running" && evidence.length > 0
        ? "insight"
        : status === "running"
          ? "thinking"
          : "idle";
  const pilotBubbleText = pilotState === "risk"
    ? "这里有一项风险需要注意"
    : pilotState === "complete"
      ? "机会简报已经生成"
      : pilotState === "insight"
        ? `发现 ${evidence.length} 条关键证据`
        : pilotState === "thinking"
          ? "正在梳理线索"
          : "我是雷达助手，需要我帮忙吗？";
  const quickPrompts = useMemo(() => {
    if (promptPool.length <= 3) return promptPool;
    return [0, 1, 2].map((offset) => promptPool[(promptCursor + offset) % promptPool.length]);
  }, [promptCursor, promptPool]);

  useEffect(() => {
    setPromptCursor(0);
  }, [promptPool]);

  useEffect(() => {
    if (!open || promptPool.length <= 3 || isPromptRotationPaused) return;
    const timer = window.setInterval(() => {
      setPromptCursor((cursor) => (cursor + 1) % promptPool.length);
    }, 50000);
    return () => window.clearInterval(timer);
  }, [open, promptPool.length, isPromptRotationPaused]);

  if (!open) {
    return (
      <button className={`pilot-fab pilot-${pilotState}`} onClick={() => setOpen(true)} aria-label={`打开雷达助手：${pilotBubbleText}`}>
        <span className="pilot-cat" aria-hidden="true" />
        <span className="pilot-bubble">
          <span className="pilot-state-dot" aria-hidden="true" />
          <span className="pilot-bubble-copy">{pilotBubbleText}</span>
          {pilotState === "thinking" && <span className="pilot-thinking-dots" aria-hidden="true"><i /><i /><i /></span>}
          {pilotState === "insight" && <Sparkle className="pilot-state-icon" size={15} weight="fill" />}
          {pilotState === "risk" && <SealWarning className="pilot-state-icon" size={15} weight="fill" />}
          {pilotState === "complete" && <CheckCircle className="pilot-state-icon" size={15} weight="fill" />}
        </span>
      </button>
    );
  }

  return (
    <aside className="pilot-dock terminal-panel">
      <header className="pilot-head">
        <div className="pilot-head-mark">
          <ChatCircleText size={18} weight="duotone" />
        </div>
        <div className="pilot-head-copy">
          <strong>雷达助手</strong>
          <span>{viewTitle}</span>
        </div>
        <button className="pilot-close" onClick={() => setOpen(false)} aria-label="收起雷达助手"><X size={18} /></button>
      </header>
      <section className="pilot-suggestions">
        <div className="suggestion-label">
          <Sparkle size={14} weight="duotone" />
          <span>可以这样问</span>
        </div>
        <div className="pilot-prompts">
          {quickPrompts.map((prompt) => (
            <button key={prompt} onClick={() => setSignal(prompt)}>
              <span>{prompt}</span>
              <ArrowRight size={16} />
            </button>
          ))}
        </div>
      </section>
      <div className="message-stream">
        {messages.map((message) => (
          <motion.div
            className={`message ${message.role}`}
            key={message.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", bounce: 0, duration: 0.28 }}
          >
            {message.text}
          </motion.div>
        ))}
      </div>
      <div className="composer">
        <textarea
          value={signal}
          onChange={(event) => setSignal(event.target.value)}
          placeholder="例如：可复美胶原棒最近在医美后修复人群里很火，背后有哪些上市公司线索？"
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) onAnalyze();
          }}
        />
        <button className="send-button" onClick={onAnalyze} disabled={!signal.trim() || status === "running"}>
          {status === "running" ? <CircleNotch className="spin" size={18} /> : <ArrowRight size={18} />}
        </button>
      </div>
    </aside>
  );
}

function RadarHome({
  sections,
  maturity,
  candidates,
  evidence,
  status,
  runId,
  steps,
  onOpenStock,
  onOpenView,
  onSaveEvidence,
  onAddToWatchlist,
  analysisHistory,
  onRestoreHistory,
  onDeleteHistory,
  isEvidenceSaved,
  isInWatchlist
}: {
  sections: BriefSection[];
  maturity?: Maturity;
  candidates: Candidate[];
  evidence: EvidenceItem[];
  status: string;
  runId: string | null;
  steps: AnalysisStep[];
  onOpenStock: (candidate: Candidate) => void;
  onOpenView: (view: ViewId) => void;
  onSaveEvidence: (item: EvidenceItem) => void;
  onAddToWatchlist: (candidate: Candidate) => void;
  analysisHistory: AnalysisHistoryEntry[];
  onRestoreHistory: (record: AnalysisHistoryEntry) => void;
  onDeleteHistory: (record: AnalysisHistoryEntry) => void;
  isEvidenceSaved: (item: EvidenceItem) => boolean;
  isInWatchlist: (candidate: Candidate) => boolean;
}) {
  const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const activeTicker = selectedTicker || hoveredTicker;
  const sectionMap = new Map(sections.map((section) => [section.id, section]));
  const hasRun = status !== "idle" || Boolean(runId) || sections.length > 0 || candidates.length > 0;
  const relatedEvidence = activeTicker
    ? evidence.filter((item) => {
        if (!item.relatedTicker) return false;
        return normalizeStockRef({ ticker: item.relatedTicker, market: "UNKNOWN" }).ticker === activeTicker;
      })
    : [];
  const visibleEvidence = activeTicker ? relatedEvidence : evidence.slice(0, 5);
  const risk = sectionMap.get("risk_disconfirmation")?.body;
  const nextVerification = sectionMap.get("next_verification")?.body;
  const activeStep = steps.find((step) => step.status === "running");
  const currentSignal = sectionMap.get("signal_summary")?.body;

  return (
    <div className="radar-home">
      <div className="overview-metrics-row">
        {!hasRun ? (
          <section className="home-empty terminal-panel">
            <div className="empty-symbol"><Sparkle size={28} weight="duotone" /></div>
            <h1>等待消费观察</h1>
            <p>输入产品、品牌、消费场景或资讯线索。</p>
          </section>
        ) : (
          <section className="home-overview terminal-panel">
            <div>
              <div className="overview-kicker">
                <span>当前总览</span>
                <div className={maturityClass(maturity)}>{translateMaturity(maturity)}</div>
              </div>
              <h1>{currentSignal || "正在分析"}</h1>
            </div>
          </section>
        )}
        <section className="metric-grid">
          <MetricCard tone="blue" label="候选公司" value={String(candidates.length)} icon={<Buildings size={28} weight="duotone" />} />
          <MetricCard tone="teal" label="证据条目" value={String(evidence.length)} icon={<Database size={28} weight="duotone" />} />
          <MetricCard tone="violet" label="机会简报" value={sections.length ? "已生成" : "待生成"} icon={<FileText size={28} weight="duotone" />} />
          <MetricCard tone="amber" label="成熟度" value={translateMaturity(maturity)} icon={<Gauge size={28} weight="duotone" />} />
        </section>
      </div>
      {hasRun && <ResearchRoomPulse steps={steps} briefReady={sections.length > 0} onOpenRoom={() => onOpenView("agents")} onOpenBrief={() => onOpenView("briefs")} />}
      <div className="home-summary-grid">
        <div className="summary-primary-row">
        <section className="summary-panel terminal-panel">
          <header>
            <span>候选 Top</span>
            <button className="text-button" onClick={() => onOpenView("stocks")}>打开个股行情</button>
          </header>
          {candidates.length ? (
            <div className="summary-candidates">
              {candidates.slice(0, 5).map((candidate) => (
                <article
                  className={activeTicker === normalizeStockRef(candidate).ticker ? "summary-candidate linked" : "summary-candidate"}
                  key={candidate.id}
                  onMouseEnter={() => setHoveredTicker(normalizeStockRef(candidate).ticker)}
                  onMouseLeave={() => setHoveredTicker(null)}
                  onClick={() => setSelectedTicker(normalizeStockRef(candidate).ticker)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedTicker(normalizeStockRef(candidate).ticker);
                    }
                  }}
                >
                  <div className="company-heading">
                    <CompanyIcon company={candidate} />
                    <div><strong>{candidate.name}</strong><span>{candidate.market} · {candidate.ticker || "未给代码"}</span></div>
                  </div>
                  <small>{candidate.debate?.decision_reason || candidate.why}</small>
                  {candidate.debate?.decision && <em className={`decision-badge mini ${candidate.debate.decision}`}>{decisionLabel(candidate.debate.decision)}</em>}
                  <div className="asset-actions">
                    <button className="mini-action" onClick={() => onOpenStock(candidate)} disabled={!candidate.ticker}>
                      <ChartLine size={14} /> 查看行情
                    </button>
                    <button className="mini-action" onClick={() => onAddToWatchlist(candidate)} disabled={!candidate.ticker || isInWatchlist(candidate)}>
                      <BookmarkSimple size={14} /> {isInWatchlist(candidate) ? "已观察" : "加入观察"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="summary-empty">暂无候选公司</p>
          )}
        </section>

        <section
          className={`summary-panel terminal-panel evidence-summary-panel ${activeTicker ? "evidence-linked" : ""}`}
        >
          <header>
            <span>{activeTicker ? `关联证据 · ${relatedEvidence.length} 条` : "关键证据"}</span>
            <button className="text-button" onClick={() => onOpenView("evidence")}>查看证据库</button>
          </header>
          <motion.div
            className="summary-evidence-list"
            key={activeTicker || "all-evidence"}
            initial={{ opacity: 0.55, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {visibleEvidence.length ? visibleEvidence.map((item) => (
              <article className="summary-evidence-item" key={item.id}>
                <div className="summary-evidence-meta">
                  <span>{({ company: "公司快照", news: "新闻资讯", announcement: "公司公告", report: "研究报告", financial: "财务数据", market: "市场数据", risk: "风险提示" } as Record<string, string>)[item.kind] || "相关证据"}</span>
                  <time>{item.timestamp || item.source}</time>
                </div>
                <strong>{item.title}</strong>
                <p>{item.snippet || item.relevance}</p>
                <div className="asset-actions">
                  <button className="mini-action" onClick={() => onSaveEvidence(item)} disabled={isEvidenceSaved(item)}>
                    <BookmarkSimple size={14} /> {isEvidenceSaved(item) ? "已保存" : "保存证据"}
                  </button>
                  {item.url && <a className="mini-action" href={item.url} target="_blank" rel="noreferrer">打开来源</a>}
                </div>
              </article>
            )) : (
              <p className="summary-empty">{activeTicker ? "该公司暂无直接关联证据" : "等待分析结果"}</p>
            )}
          </motion.div>
        </section>

        </div>

        <div className="summary-secondary-row">

        <section className="summary-panel terminal-panel">
          <header>
            <span>风险与下一步</span>
          </header>
          <div className="summary-copy">
            <strong>{risk ? "主要风险" : activeStep ? `正在${activeStep.label}` : "等待研判"}</strong>
            <p>{risk || activeStep?.messages.at(-1) || "暂无风险结论"}</p>
            {nextVerification && <p>{nextVerification}</p>}
          </div>
        </section>

        <section className="summary-panel terminal-panel">
          <header>
            <span>研究工具箱</span>
          </header>
          <div className="research-tools-grid">
            <button className="research-tool-card research-tool-blue" onClick={() => onOpenView("stocks")}>
              <div className="research-tool-icon"><ChartLine size={26} weight="duotone" /></div>
              <div className="research-tool-copy"><strong>公司对比</strong><p>横向比较候选标的</p><small>进入工具</small></div>
            </button>
            <button className="research-tool-card research-tool-teal" onClick={() => onOpenView("trend")}>
              <div className="research-tool-icon"><Newspaper size={26} weight="duotone" /></div>
              <div className="research-tool-copy"><strong>趋势追踪</strong><p>持续追踪主题变化</p><small>进入工具</small></div>
            </button>
            <button className="research-tool-card research-tool-violet" onClick={() => onOpenView("evidence")}>
              <div className="research-tool-icon"><Database size={26} weight="duotone" /></div>
              <div className="research-tool-copy"><strong>证据时间线</strong><p>梳理关键事件脉络</p><small>进入工具</small></div>
            </button>
            <button className="research-tool-card research-tool-amber" onClick={() => onOpenView("watchlist")}>
              <div className="research-tool-icon"><ListChecks size={26} weight="duotone" /></div>
              <div className="research-tool-copy"><strong>验证清单</strong><p>管理待验证事项</p><small>进入工具</small></div>
            </button>
          </div>
        </section>
        </div>
      </div>
      {analysisHistory.length > 0 && (
        <section className="recent-analyses terminal-panel">
          <header>
            <span>最近分析</span>
            <strong>{analysisHistory.length} / 6</strong>
          </header>
          <div className="recent-analysis-list">
            {analysisHistory.map((record) => (
              <article className={record.run_id === runId ? "recent-analysis active" : "recent-analysis"} key={record.run_id}>
                <button onClick={() => onRestoreHistory(record)}>
                  <strong>{record.signal || "未命名分析"}</strong>
                  <span>{translateMaturity(record.maturity)} · {record.candidates?.length || 0} 个候选 · {formatTime(record.created_at)}</span>
                </button>
                <button className="mini-action danger" onClick={() => onDeleteHistory(record)} aria-label="删除分析">
                  <Trash size={14} />
                </button>
              </article>
            ))}
          </div>
        </section>
      )}
      <AnimatePresence>
        {hoveredTicker && relatedEvidence.length > 0 && (
          <motion.div
            className="interaction-toast"
            initial={{ opacity: 0, y: 10, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 430, damping: 31 }}
          >
            <CheckCircle size={18} weight="fill" /> 已同步筛选 {relatedEvidence.length} 条证据
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MetricCard({ label, value, note, icon, tone = "blue" }: { label: string; value: string; note?: string; icon?: ReactNode; tone?: "blue" | "teal" | "violet" | "amber" }) {
  return (
    <div className={`metric-card metric-card-${tone} terminal-panel`}>
      {icon && <i className="metric-card-icon">{icon}</i>}
      <div className="metric-card-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        {note && <small>{note}</small>}
      </div>
    </div>
  );
}

function TrendRadarPage({
  onSendToPilot
}: {
  onSendToPilot: (prompt: string) => void;
}) {
  const [topics, setTopics] = useState<TrendRadarTopic[]>([]);
  const [activeTopicId, setActiveTopicId] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [generatedAt, setGeneratedAt] = useState<string | null | undefined>(null);
  const [sourceCount, setSourceCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadTrendRadar(refresh = false) {
    setLoading(true);
    setError("");
    try {
      const data = await fetchTrendRadarTopics({ keyword, limit: 24, perTopic: 200, refresh });
      setTopics(data.topics || []);
      setGeneratedAt(data.generated_at);
      setSourceCount(data.source_stats?.total_sources || 0);
      setActiveTopicId((current) => {
        if (current && data.topics.some((topic) => topic.id === current)) return current;
        return data.topics[0]?.id || null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "热点雷达加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTrendRadar(false);
  }, []);

  const rankedTopics = useMemo(
    () => [...topics].sort((left, right) => right.heat_score - left.heat_score),
    [topics]
  );
  const activeTopic = topics.find((topic) => topic.id === activeTopicId) || rankedTopics[0];
  const heatLevel = (score: number) => {
    if (score >= 100) return "critical";
    if (score >= 90) return "high";
    if (score > 70) return "warm";
    return "normal";
  };
  const sendTopicToPilot = (topic: TrendRadarTopic) => {
    const titles = topic.items.map((item) => `- ${item.title}`).join("\n");
    onSendToPilot(
      `请基于这个热点主题生成一个消费投资信号，并说明可能映射到哪些上市公司。\n\n主题：${topic.topic}\n热度：${topic.heat_score}\n行业：${topic.industries.join("、")}\n摘要：${topic.summary}\n资讯：\n${titles}`
    );
  };

  return (
    <section className="page-panel terminal-panel">
      <header className="page-header trend-page-header">
        <div className="trend-title-block">
          <h1>热点雷达</h1>
          <p className="trend-updated-at">
            <span className="trend-status-dot" aria-hidden="true" />
            {generatedAt ? `更新于 ${generatedAt}` : "暂无更新"}
          </p>
        </div>
        <div className="trend-actions">
          <div className="search-box">
            <MagnifyingGlass size={15} />
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索消费品类、品牌或场景" />
          </div>
          <button className="trend-action secondary" onClick={() => loadTrendRadar(false)} disabled={loading}>搜索</button>
          <button className="trend-action primary" onClick={() => loadTrendRadar(true)} disabled={loading}>
            {loading ? <CircleNotch className="spin" size={18} /> : <Newspaper size={18} />}
            刷新资讯
          </button>
        </div>
      </header>
      {error && <div className="inline-warning">{error}</div>}
      {!loading && !topics.length ? (
        <EmptyState
          icon={<Newspaper size={28} />}
          title="暂无热点缓存"
          text="点击“刷新资讯”获取最新热点。"
        />
      ) : (
        <div className="trend-workspace">
          <div className="topic-list">
            {loading && !topics.length ? (
              <div className="loading-card"><CircleNotch className="spin" size={18} />正在抓取公开资讯源...</div>
            ) : (
              rankedTopics.map((topic, index) => (
                <button
                  className={`${activeTopic?.id === topic.id ? "topic-card active" : "topic-card"} heat-${heatLevel(topic.heat_score)}`}
                  key={topic.id}
                  onClick={() => setActiveTopicId(topic.id)}
                >
                  <span className="topic-rank" aria-label={`第 ${index + 1} 名`}>{index + 1}</span>
                  <span className="topic-card-copy">
                    <strong>{topic.topic}</strong>
                    <small>{topic.industries.join("、") || "未分类"} · {topic.sources.length} 个来源 · {topic.items.length} 条资讯</small>
                  </span>
                  <span className="topic-heat" aria-label={`热度 ${topic.heat_score}`}>
                    <Fire size={18} weight="fill" />
                    <b>{topic.heat_score}</b>
                  </span>
                </button>
              ))
            )}
          </div>
          {activeTopic && (
            <article className="topic-detail">
              <div className="topic-detail-head">
                <div>
                  <span>选中主题</span>
                  <h2>{activeTopic.topic}</h2>
                  <p>{activeTopic.summary}</p>
                </div>
                <button className="trend-action primary" onClick={() => sendTopicToPilot(activeTopic)}>
                  <ChatCircleText size={18} />
                  交给雷达助手
                </button>
              </div>
              <div className="topic-pipeline" aria-label="主题处理进度">
                {activeTopic.lifecycle.map((stage, index) => {
                  const StageIcon = index === 0 ? FileText : index === 1 ? UsersThree : Sparkle;
                  return (
                    <div className="topic-pipeline-step" key={`${activeTopic.id}-${stage.stage}`}>
                      <div className="pipeline-visual" aria-hidden="true">
                        <span className="pipeline-icon"><StageIcon size={22} weight="duotone" /></span>
                        <span className="pipeline-check"><CheckCircle size={15} weight="fill" /></span>
                      </div>
                      <div className="pipeline-copy">
                        <div className="pipeline-title"><strong>{stage.stage}</strong><span>{stage.at || "—"}</span></div>
                        <p>{stage.note}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="news-list">
                {activeTopic.items.map((item, index) => (
                  <a className="news-row" href={item.url || "#"} target="_blank" rel="noreferrer" key={`${item.title}-${index}`}>
                    <span className="news-time">{item.time || "—"}</span>
                    <strong className="news-title">{item.title}</strong>
                    <span className="news-source">
                      <span className="news-source-mark" aria-hidden="true">{(item.source || "公").slice(0, 1).toUpperCase()}</span>
                      <small>{item.source || "公开来源"} · {item.industry || "未分类"}</small>
                    </span>
                    <ArrowRight className="news-arrow" size={16} />
                  </a>
                ))}
              </div>
            </article>
          )}
        </div>
      )}
    </section>
  );
}

function AgentRoomPage({
  steps,
  agentMessages,
  candidates,
  evidence,
  maturity,
  status,
  compact = false
}: {
  steps: AnalysisStep[];
  agentMessages: AgentMessage[];
  candidates: Candidate[];
  evidence: EvidenceItem[];
  maturity?: Maturity;
  status: string;
  compact?: boolean;
}) {
  const activeStep = steps.find((step) => step.status === "running");
  const completedSteps = steps.filter((step) => step.status === "done").length;
  const latestMessages = compact ? agentMessages.slice(-4) : agentMessages;
  const empty = !agentMessages.length;

  return (
    <section className={`page-panel terminal-panel agent-room ${compact ? "compact-panel" : ""}`}>
      <header className="page-header">
        <div>
          <span>多角色研讨</span>
          <h1>Agent 研讨室</h1>
          <p>这里展示后端真实分析流程中的角色发言：先从消费信号出发，再映射公司、拉取证据，最后进入多空质疑和委员会结论。</p>
        </div>
        <div className="agent-room-summary">
          <span>进度 {completedSteps}/{steps.length}</span>
          <strong>{activeStep ? activeStep.label : status === "done" ? "研讨完成" : "等待启动"}</strong>
        </div>
      </header>

      <div className="agent-room-layout">
        <aside className="agent-orchestration">
          {steps.map((step, index) => (
            <motion.article className={`agent-step ${step.status}`} key={step.id} whileHover={{ x: 2 }}>
              <div className="agent-step-index">
                {step.status === "done" ? <CheckCircle size={15} weight="fill" /> : step.status === "running" ? <CircleNotch className="spin" size={15} /> : index + 1}
              </div>
              <div>
                <strong>{step.label}</strong>
                <p>{step.messages.at(-1) || (status === "idle" ? "等待消费信号" : "等待上游结果")}</p>
              </div>
            </motion.article>
          ))}
        </aside>

        <main className="agent-discussion">
          <div className="discussion-strip">
            <MetricPill label="候选" value={`${candidates.length} 个`} />
            <MetricPill label="证据" value={`${evidence.length} 条`} />
            <MetricPill label="状态" value={translateMaturity(maturity)} />
          </div>

          {empty ? (
            <div className="agent-empty">
              <Brain size={26} />
              <h2>等待雷达助手发起研讨</h2>
              <p>输入一个消费品、品牌、场景或资讯线索后，这里会实时出现消费分析师、公司映射员、证据研究员、多头、空头和委员会的发言。</p>
            </div>
          ) : (
            <div className="agent-message-list">
              {latestMessages.map((message) => (
                <motion.article
                  className={`agent-message-card ${message.stance}`}
                  key={message.id}
                  initial={{ opacity: 0, y: 8, scale: 0.99 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", bounce: 0.18, duration: 0.38 }}
                >
                  <div className="agent-avatar">{agentInitial(message.agent_label)}</div>
                  <div className="agent-message-body">
                    <header>
                      <strong>{message.agent_label}</strong>
                      <span>{stanceLabel(message.stance)} · {stepLabel(message.step, steps)}</span>
                    </header>
                    <p>{message.message}</p>
                  </div>
                </motion.article>
              ))}
            </div>
          )}
        </main>
      </div>
    </section>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function stepLabel(stepId: StepId, steps: AnalysisStep[]) {
  return steps.find((step) => step.id === stepId)?.label || stepId;
}

function agentInitial(label: string) {
  return label.slice(0, 1);
}

function stanceLabel(stance: AgentStance) {
  const labels: Record<AgentStance, string> = {
    observation: "观察",
    hypothesis: "假设",
    mapping: "映射",
    evidence: "证据",
    market: "行情",
    bull: "多头",
    bear: "空头",
    review: "审查",
    decision: "结论"
  };
  return labels[stance];
}

function StocksPage({
  candidates,
  selectedStock,
  setSelectedStock,
  onAddToWatchlist,
  isInWatchlist
}: {
  candidates: Candidate[];
  selectedStock: StockRef | null;
  setSelectedStock: (stock: StockRef | null) => void;
  onAddToWatchlist: (candidate: Candidate) => void;
  isInWatchlist: (candidate: Candidate) => boolean;
}) {
  const activeStock = selectedStock || (candidates[0] ? normalizeStockRef(candidates[0]) : null);
  const [snapshot, setSnapshot] = useState<StockSnapshot | null>(null);
  const [quoteSnapshot, setQuoteSnapshot] = useState<StockSnapshot | null>(null);
  const [klineRows, setKlineRows] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [klineLoading, setKlineLoading] = useState(false);
  const [error, setError] = useState("");
  const [quoteError, setQuoteError] = useState("");
  const [klineError, setKlineError] = useState("");

  useEffect(() => {
    if (!activeStock?.ticker) {
      setSnapshot(null);
      setQuoteSnapshot(null);
      setKlineRows([]);
      return;
    }
    let alive = true;
    setLoading(true);
    setQuoteLoading(true);
    setKlineLoading(true);
    setError("");
    setQuoteError("");
    setKlineError("");
    setSnapshot(null);
    setQuoteSnapshot(null);
    setKlineRows([]);
    fetchStockQuote(activeStock.market, activeStock.ticker)
      .then((data) => {
        if (alive) setQuoteSnapshot(data);
      })
      .catch((err) => {
        if (alive) setQuoteError(err instanceof Error ? err.message : "价格快照加载失败");
      })
      .finally(() => {
        if (alive) setQuoteLoading(false);
      });
    fetchStockKline(activeStock.market, activeStock.ticker)
      .then((data) => {
        if (!alive) return;
        const rows = asRows(data.data?.daily_kline);
        setKlineRows(rows);
        if (!rows.length) setKlineError("暂未取得 K 线数据");
      })
      .catch((err) => {
        if (alive) setKlineError(err instanceof Error ? err.message : "K 线加载失败");
      })
      .finally(() => {
        if (alive) setKlineLoading(false);
      });
    fetchStockSnapshot(activeStock.market, activeStock.ticker)
      .then((data) => {
        if (alive) setSnapshot(data);
      })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : "个股行情加载失败");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [activeStock?.market, activeStock?.ticker]);

  const data = snapshot?.data || {};
  const fastQuoteData = quoteSnapshot?.data || {};
  const fastQuote = ((fastQuoteData.quote || fastQuoteData) as Record<string, unknown>) || {};
  const detailQuote = ((data.quote || data) as Record<string, unknown>) || {};
  // The fast quote endpoint is optimized for price and often omits PE/PB,
  // turnover, or market-cap fields. Merge it with the detail response so a
  // valid price does not hide the slower supplemental fields.
  const quote = {
    ...detailQuote,
    ...Object.fromEntries(Object.entries(fastQuote).filter(([, value]) => value !== null && value !== undefined && value !== ""))
  };
  const activeCandidate = candidates.find((candidate) => {
    const stock = normalizeStockRef(candidate);
    return stock.ticker === activeStock?.ticker && stock.market === activeStock?.market;
  });
  const metrics = ((data.metrics || data.financials || {}) as Record<string, unknown>) || {};
  const announcements = asRows(data.announcements).slice(0, 8);
  const reports = asRows(data.reports).slice(0, 6);
  const fundFlow = asRows(data.fund_flow).slice(-10);
  const concepts = asConcepts(data.concepts).slice(0, 10);
  const hotConcepts = asRows(data.hot_concepts).slice(0, 8);
  const dailyKline = asRows(data.daily_kline);
  const chartRows = dailyKline.length ? dailyKline : klineRows;
  const holderChanges = asRows(data.holder_num_change).slice(0, 5);
  const investorQa = asRows(data.investor_qa).slice(0, 5);
  const dataGaps = collectStockGaps(data);
  const visibleGaps = [...dataGaps, ...(quoteError && !quoteSnapshot ? [quoteError] : []), ...(klineError && !chartRows.length ? [klineError] : [])];

  return (
    <section className="page-panel terminal-panel">
      <header className="page-header">
        <div>
          <h1>个股行情</h1>
        </div>
      </header>
      {candidates.length ? (
        <div className="stock-workspace">
          <aside className="stock-list">
            {candidates.map((candidate) => {
              const stock = normalizeStockRef(candidate);
              return (
                <article
                  className={activeStock?.ticker === stock.ticker && activeStock.market === stock.market ? "stock-list-item active" : "stock-list-item"}
                  key={candidate.id}
                  onClick={() => setSelectedStock(stock)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelectedStock(stock); }}
                >
                  <div className="company-heading">
                    <CompanyIcon company={candidate} />
                    <div><strong>{candidate.name}</strong><span>{stock.market} · {stock.ticker}</span></div>
                  </div>
                  <small>{candidate.exposure === "direct" ? "直接相关" : candidate.exposure === "adjacent" ? "相邻相关" : "弱相关"}</small>
                  <span className="stock-watch-action">
                    <button
                      className="mini-action"
                      onClick={(event) => {
                        event.stopPropagation();
                        onAddToWatchlist(candidate);
                      }}
                      disabled={isInWatchlist(candidate) || !candidate.ticker}
                    >
                      <BookmarkSimple size={13} /> {isInWatchlist(candidate) ? "已观察" : "加入观察"}
                    </button>
                  </span>
                </article>
              );
            })}
          </aside>
          <article className="stock-detail">
            <div className="stock-detail-head">
              <CompanyIcon company={activeStock || { ticker: "", market: "UNKNOWN", name: String(quote.name || "") }} size="large" />
              <div className="stock-detail-title">
                <span>{activeStock?.market} · {activeStock?.ticker}</span>
                <h2>{String(quote.name || activeStock?.name || "未命名标的")}</h2>
              </div>
              {(quoteLoading || klineLoading) && <CircleNotch className="spin" size={20} />}
            </div>
            {(quoteLoading || klineLoading) && !chartRows.length && !quoteSnapshot ? (
              <div className="loading-card"><CircleNotch className="spin" size={18} />正在加载行情数据...</div>
            ) : null}
            {error ? (
              <div className="inline-warning">{error}</div>
            ) : null}
            {klineError && !chartRows.length ? (
              <div className="inline-warning">{klineError}</div>
            ) : null}
            {(snapshot || quoteSnapshot || chartRows.length > 0 || !loading) && (
              <>
                <div className="quote-metrics">
                  <MetricCard label="最新价" value={quoteLoading && !quoteSnapshot ? "加载中" : formatMetric(quote.price)} />
                  <MetricCard label="涨跌幅" value={quoteLoading && !quoteSnapshot ? "加载中" : `${formatMetric(quote.change_pct)}%`} />
                  <MetricCard label="PE TTM" value={formatMetric(quote.pe_ttm)} />
                  <MetricCard label="PB" value={formatMetric(quote.pb)} />
                </div>
                <StockChart rows={chartRows} quote={quote} loading={klineLoading} />
                <div className="stock-sections">
                  <section>
                    <h3>行情摘要</h3>
                    <div className="source-row"><span>成交额</span><em>{formatMetric(quote.amount_wan || quote.amount)}</em></div>
                    <div className="source-row"><span>总市值</span><em>{formatMetric(quote.mcap_yi || quote.mcap)}</em></div>
                    <div className="source-row"><span>换手率</span><em>{formatMetric(quote.turnover_pct)}</em></div>
                  </section>
                  <section>
                    <h3>财务摘要</h3>
                    <div className="source-row"><span>报告期</span><em>{formatMetric(metrics.period || metrics.report_date)}</em></div>
                    <div className="source-row"><span>营收</span><em>{formatCompact(metrics.revenue)}</em></div>
                    <div className="source-row"><span>净利润</span><em>{formatCompact(metrics.net_profit)}</em></div>
                    <div className="source-row"><span>毛利率</span><em>{formatPct(metrics.gross_margin)}</em></div>
                  </section>
                </div>
                {loading && !snapshot && (
                  <div className="loading-card subtle"><CircleNotch className="spin" size={18} />正在补充公告、研报和财务数据...</div>
                )}
                {activeCandidate?.debate && (
                  <section className="stock-debate-panel">
                    <div className="stock-debate-head">
                      <div>
                        <span>本轮研讨结论</span>
                        <h3>{decisionLabel(activeCandidate.debate.decision)}</h3>
                      </div>
                      <div className={`decision-badge ${activeCandidate.debate.decision || "pause"}`}>
                        {decisionLabel(activeCandidate.debate.decision)}
                      </div>
                    </div>
                    <div className="debate-grid">
                      <DebateNote label="多头" body={activeCandidate.debate.bull} />
                      <DebateNote label="空头" body={activeCandidate.debate.bear} />
                      <DebateNote label="估值" body={activeCandidate.debate.valuation} />
                      <DebateNote label="风险" body={activeCandidate.debate.risk} />
                    </div>
                    <p className="decision-reason">{activeCandidate.debate.decision_reason}</p>
                  </section>
                )}
                <div className="stock-info-grid">
                  <StockListPanel title="公告" rows={announcements} empty="暂无公告数据" render={(row) => (
                    <a href={String(row.url || "#")} target="_blank" rel="noreferrer">
                      <strong>{String(row.title || "未命名公告")}</strong>
                      <span>{String(row.date || "—")} · {String(row.type || "公告")}</span>
                    </a>
                  )} />
                  <StockListPanel title="研报" rows={reports} empty="暂无研报数据" render={(row) => (
                    <div>
                      <strong>{String(row.title || "未命名研报")}</strong>
                      <span>{String(row.publishDate || "—")} · {String(row.orgSName || row.industryName || "机构")}</span>
                    </div>
                  )} />
                  <StockListPanel title="资金流" rows={fundFlow} empty="暂无资金流数据" render={(row) => (
                    <div className="source-row flat">
                      <span>{String(row.date || "—")}</span>
                      <em>{formatCompact(row.main_net)}</em>
                    </div>
                  )} />
                  <StockListPanel title="概念与板块" rows={[...concepts, ...hotConcepts]} empty="暂无概念数据" render={(row) => (
                    <div className="tag-row">
                      <span>{String(row.name || row.concept || "未命名概念")}</span>
                      {row.change_pct !== undefined && <em>{formatPct(row.change_pct)}</em>}
                    </div>
                  )} />
                  <StockListPanel title="股东户数" rows={holderChanges} empty="暂无股东户数数据" render={(row) => (
                    <div className="source-row flat">
                      <span>{String(row.date || "—")}</span>
                      <em>{formatMetric(row.holder_num)}</em>
                    </div>
                  )} />
                  <StockListPanel title="互动问答" rows={investorQa} empty="暂无互动问答数据" render={(row) => (
                    <div>
                      <strong>{String(row.question || "未命名问题")}</strong>
                      <span>{String(row.ask_time || "—")}</span>
                    </div>
                  )} />
                </div>
                {visibleGaps.length > 0 && (
                  <section className="data-gap-panel">
                    <h3>数据缺口</h3>
                    <p>{visibleGaps.join("；")}</p>
                  </section>
                )}
                <details className="raw-snapshot">
                  <summary>查看原始快照</summary>
                  <pre>{JSON.stringify(data, null, 2)}</pre>
                </details>
              </>
            )}
          </article>
        </div>
      ) : (
        <EmptyState icon={<ChartLine size={28} />} title="暂无候选标的" text="运行一次消费信号分析后，候选股票会出现在这里。下一步会把股票卡片接到详情页。" />
      )}
    </section>
  );
}

function DebateNote({ label, body }: { label: string; body?: string }) {
  return (
    <div className="debate-note">
      <span>{label}</span>
      <p>{body || "暂无结论"}</p>
    </div>
  );
}

function decisionLabel(decision?: CandidateDecision) {
  if (decision === "track") return "继续跟踪";
  if (decision === "drop") return "剔除";
  return "暂缓";
}

function asRows(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function asConcepts(value: unknown): Array<Record<string, unknown>> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  const obj = value as Record<string, unknown>;
  return asRows(obj.boards);
}

function collectStockGaps(data: Record<string, unknown>) {
  const gaps: string[] = [];
  for (const [key, label] of [
    ["daily_kline", "K 线需要 mootdx"],
    ["financials", "A 股完整财务摘要需要 akshare"],
    ["stock_news", "个股新闻需要 akshare"],
    ["valuation_percentile", "估值分位需要 akshare"]
  ] as const) {
    const value = data[key];
    if (value && typeof value === "object" && !Array.isArray(value) && "error" in value) {
      gaps.push(`${label}：${String((value as Record<string, unknown>).error)}`);
    }
  }
  return gaps;
}

function hasQuoteData(quote: Record<string, unknown>) {
  return quote.price !== undefined || quote.change_pct !== undefined || quote.name !== undefined;
}

function StockChart({
  rows,
  quote,
  loading = false
}: {
  rows: Array<Record<string, unknown>>;
  quote: Record<string, unknown>;
  loading?: boolean;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const points = rows
    .map((row) => ({
      date: String(row.date || row.datetime || row.time || ""),
      close: numeric(row.close ?? row.price)
    }))
    .filter((row) => row.close !== null)
    .slice(-60) as Array<{ date: string; close: number }>;

  if (!points.length) {
    return (
      <section className="stock-chart empty">
        <div>
          <span>价格轨迹</span>
          <strong>{loading ? "加载中" : formatMetric(quote.price)}</strong>
        </div>
        <p>{loading ? "正在获取 K 线数据。" : "暂未取得 K 线数据。"}</p>
      </section>
    );
  }

  const values = points.map((point) => point.close);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const d = points
    .map((point, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 100;
      const y = 100 - ((point.close - min) / range) * 100;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <section className="stock-chart">
      <div className="stock-chart-head">
        <div>
          <span>价格轨迹</span>
          <strong>{points[0].date || "最近"} → {points.at(-1)?.date || "最新"}</strong>
        </div>
        <div>
          <span>区间</span>
          <strong>{formatMetric(min)} / {formatMetric(max)}</strong>
        </div>
      </div>
      <div className="stock-chart-plot">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        role="img"
        aria-label="价格轨迹"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
          setHoverIndex(Math.min(points.length - 1, Math.round(ratio * (points.length - 1))));
        }}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <path d={d} />
        {hoverIndex !== null && (() => {
          const point = points[hoverIndex];
          const x = points.length === 1 ? 0 : (hoverIndex / (points.length - 1)) * 100;
          const y = 100 - ((point.close - min) / range) * 100;
          return <><line className="stock-chart-crosshair" x1={x} x2={x} y1="0" y2="100" /><circle className="stock-chart-dot" cx={x} cy={y} r="1.8" /></>;
        })()}
      </svg>
      {hoverIndex !== null && <div className="stock-chart-tooltip"><strong>{points[hoverIndex].date}</strong><span>{formatMetric(points[hoverIndex].close)}</span></div>}
      </div>
    </section>
  );
}

function StockListPanel({
  title,
  rows,
  empty,
  render
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
  empty: string;
  render: (row: Record<string, unknown>, index: number) => ReactNode;
}) {
  return (
    <section className="stock-list-panel">
      <h3>{title}</h3>
      {rows.length ? (
        <div className="stock-list-rows">
          {rows.map((row, index) => (
            <div className="stock-list-row" key={`${title}-${index}`}>
              {render(row, index)}
            </div>
          ))}
        </div>
      ) : (
        <p className="privacy-note">{empty}</p>
      )}
    </section>
  );
}

function numeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.replace(/,/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatCompact(value: unknown) {
  const num = numeric(value);
  if (num === null) return formatMetric(value);
  const abs = Math.abs(num);
  if (abs >= 100000000) return `${(num / 100000000).toFixed(2)} 亿`;
  if (abs >= 10000) return `${(num / 10000).toFixed(2)} 万`;
  return formatMetric(num);
}

function formatPct(value: unknown) {
  const text = formatMetric(value);
  if (text === "—") return text;
  return text.endsWith("%") ? text : `${text}%`;
}

function formatMetric(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

function formatTime(value?: string | number) {
  if (!value) return "—";
  const date = typeof value === "number" ? new Date(value) : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function WatchlistPage({
  watchlist,
  onOpenStock,
  onRemove
}: {
  watchlist: WatchlistItem[];
  onOpenStock: (candidate: Candidate) => void;
  onRemove: (candidate: Pick<Candidate, "ticker" | "market" | "name">) => void;
}) {
  return (
    <section className="page-panel terminal-panel">
      <header className="page-header">
        <div>
          <h1>观察清单</h1>
        </div>
      </header>
      {watchlist.length ? (
        <div className="watchlist-preview">
          {watchlist.map((candidate) => {
            const stock = normalizeStockRef(candidate);
            return (
              <article className="asset-row" key={candidateKey(candidate)}>
                <div className="company-heading">
                  <CompanyIcon company={candidate} />
                  <div>
                  <strong>{candidate.name}</strong>
                  <span>{stock.market} · {stock.ticker}</span>
                  <small className="watchlist-theme"><b>主题</b>{summarizeWatchTheme(candidate.theme || candidate.signal)}</small>
                  <small className="watchlist-reason">{candidate.reason || candidate.why || "尚未记录加入原因"}</small>
                  {candidate.signal && (
                    <details className="watchlist-source">
                      <summary>查看来源分析</summary>
                      <p>{candidate.signal}</p>
                    </details>
                  )}
                  </div>
              </div>
              <div className="watchlist-meta">
                <em className="watchlist-status">{candidate.maturity ? `成熟度：${candidate.maturity}` : "继续跟踪"}</em>
                <small>加入时间 · {formatTime(candidate.added_at)}</small>
              </div>
              <div className="asset-actions">
                <button className="mini-action" onClick={() => onOpenStock(watchlistToCandidate(candidate))}>
                  <ChartLine size={14} /> 查看行情
                </button>
                  <button className="mini-action danger" onClick={() => onRemove(candidate)}>
                    <Trash size={14} /> 移出观察
                  </button>
                </div>
              </article>
            );
          })}
              </div>
      ) : (
        <EmptyState icon={<ListChecks size={28} />} title="观察清单为空" text="从本轮候选公司中加入需要继续跟踪的标的。" />
      )}
    </section>
  );
}

function SettingsPage({
  modelConnected,
  modelConfig,
  theme,
  onOpenPreferences
}: {
  modelConnected: boolean;
  modelConfig: ModelConfig;
  theme: "light" | "dark";
  onOpenPreferences: () => void;
}) {
  return (
    <section className="page-panel terminal-panel">
      <header className="page-header">
        <div>
          <span>系统配置</span>
          <h1>设置</h1>
          <p>模型与数据源配置入口。密钥优先由后端环境变量承接，前端不要求用户重复填写。</p>
        </div>
        <button className="primary-action" onClick={onOpenPreferences}><GearSix size={18} />打开设置面板</button>
      </header>
      <div className="settings-summary">
        <MetricCard label="模型状态" value={modelConnected ? "已配置" : "待配置"} note={modelConfig.model || "未选择模型"} />
        <MetricCard label="数据源" value="真实源" note="Vibe Research 数据层已迁入部分能力" />
        <MetricCard label="主题" value={theme === "light" ? "浅色" : "深色"} note="中文终端优先" />
      </div>
    </section>
  );
}

function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-symbol">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function BriefCanvas({
  sections,
  maturity,
  candidates,
  status,
  runId,
  compact = false,
  onOpenStock,
  onAddToWatchlist,
  isInWatchlist
}: {
  sections: BriefSection[];
  maturity?: Maturity;
  candidates: Candidate[];
  status: string;
  runId: string | null;
  compact?: boolean;
  onOpenStock?: (candidate: Candidate) => void;
  onAddToWatchlist?: (candidate: Candidate) => void;
  isInWatchlist?: (candidate: Candidate) => boolean;
}) {
  const sectionMap = new Map(sections.map((section) => [section.id, section]));
  return (
    <section className={`brief-canvas terminal-panel focus-panel ${compact ? "compact-panel" : ""}`}>
      <header className="canvas-header">
        <div>
          <span>消费机会简报</span>
          <h1>{sections.length ? "消费机会简报" : "从一个消费信号开始"}</h1>
        </div>
        <div className={maturityClass(maturity)}>{translateMaturity(maturity)}</div>
      </header>
      {!sections.length ? (
        <div className="empty-brief">
          <div className="empty-symbol"><Sparkle size={28} weight="duotone" /></div>
          <h2>发现消费品背后的上市公司线索。</h2>
          <p>输入产品、品牌或消费行为后，系统会流式返回真实行情、证据、风险和研究简报。</p>
          {status === "error" && <div className="inline-warning">上次运行失败，请检查设置或后端服务状态。</div>}
        </div>
      ) : (
        <div className="brief-body">
          {sectionOrder.map((id, index) => {
            const section = sectionMap.get(id);
            if (!section) return null;
            return (
              <motion.article
                className="brief-section"
                key={section.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", bounce: 0, duration: 0.34, delay: index * 0.025 }}
              >
                <span>{section.title}</span>
                <p>{section.body}</p>
              </motion.article>
            );
          })}
          <CandidateMap candidates={candidates} onOpenStock={onOpenStock} onAddToWatchlist={onAddToWatchlist} isInWatchlist={isInWatchlist} />
        </div>
      )}
      <div className="run-footnote">{runId ? `运行 ${runId}` : "等待运行"}</div>
    </section>
  );
}

function CandidateMap({
  candidates,
  onOpenStock,
  onAddToWatchlist,
  isInWatchlist
}: {
  candidates: Candidate[];
  onOpenStock?: (candidate: Candidate) => void;
  onAddToWatchlist?: (candidate: Candidate) => void;
  isInWatchlist?: (candidate: Candidate) => boolean;
}) {
  if (!candidates.length) return null;
  const groups: Array<[Candidate["exposure"], string]> = [
    ["direct", "直接相关"],
    ["adjacent", "相邻相关"],
    ["weak", "弱相关 / 观察"]
  ];
  return (
    <div className="candidate-map">
      {groups.map(([key, label]) => {
        const items = candidates.filter((candidate) => candidate.exposure === key);
        if (!items.length) return null;
        return (
          <section className="candidate-group" key={key}>
            <h3>{label}</h3>
            <div className="candidate-grid">
              {items.map((candidate) => {
                const stock = normalizeStockRef(candidate);
                return (
                  <motion.article
                    className="candidate-card"
                    key={candidate.id}
                    whileHover={{ y: -4, scale: 1.02 }}
                    whileTap={{ scale: 0.99 }}
                    transition={{ type: "spring", stiffness: 420, damping: 30, mass: 0.65 }}
                  >
                    <div className="ticker-line">
                      <CompanyIcon company={candidate} size="small" />
                      <strong>{stock.ticker}</strong>
                      <span>{stock.market}</span>
                      {candidate.debate?.decision && <em className={`decision-badge mini ${candidate.debate.decision}`}>{decisionLabel(candidate.debate.decision)}</em>}
                    </div>
                    <p>{candidate.name}</p>
                    <small>{candidate.why}</small>
                    {candidate.debate?.decision_reason && <small className="candidate-decision">{candidate.debate.decision_reason}</small>}
                    <div className="quote-line">
                      <span>{candidate.quote?.price ?? "—"}</span>
                      <span>{candidate.quote?.change_pct ?? "—"}%</span>
                    </div>
                    <div className="asset-actions">
                      <button className="mini-action" onClick={() => onOpenStock?.(candidate)} disabled={!candidate.ticker}>
                        <ChartLine size={14} /> 查看行情
                      </button>
                      {onAddToWatchlist && (
                        <button className="mini-action" onClick={() => onAddToWatchlist(candidate)} disabled={!candidate.ticker || Boolean(isInWatchlist?.(candidate))}>
                          <BookmarkSimple size={14} /> {isInWatchlist?.(candidate) ? "已观察" : "加入观察"}
                        </button>
                      )}
                    </div>
                  </motion.article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function EvidenceInspector({
  evidence,
  allEvidence,
  currentEvidence,
  activeKind,
  setActiveKind,
  candidates,
  status,
  onSaveEvidence,
  onRemoveEvidence,
  onOpenStock,
  isEvidenceSaved
}: {
  evidence: SavedEvidenceItem[];
  allEvidence: SavedEvidenceItem[];
  currentEvidence: EvidenceItem[];
  activeKind: string;
  setActiveKind: (kind: string) => void;
  candidates: Candidate[];
  status: string;
  onSaveEvidence: (item: EvidenceItem) => void;
  onRemoveEvidence: (id: string) => void;
  onOpenStock: (candidate: Candidate) => void;
  isEvidenceSaved: (item: EvidenceItem) => boolean;
}) {
  const kinds = ["all", "company", "report", "announcement", "financial", "market", "news", "risk"];
  const kindLabels: Record<string, string> = {
    all: "全部",
    company: "公司",
    report: "研报",
    announcement: "公告",
    financial: "财务",
    market: "行情",
    news: "新闻",
    risk: "风险"
  };
  return (
    <aside className="evidence-inspector terminal-panel">
      <header className="panel-title">
        <div>
          <span>证据库</span>
        <strong>{allEvidence.length ? `${allEvidence.length} 条已保存证据` : "暂无保存证据"}</strong>
        </div>
        <MagnifyingGlass size={18} />
      </header>
      {!allEvidence.length ? (
        <div className="source-status">
          <p>{status === "running" ? "正在生成本轮证据。" : "从本轮结果中保存值得留档的证据。"}</p>
        </div>
      ) : (
        <>
          <div className="evidence-tabs">
            {kinds.map((kind) => (
              <button className={activeKind === kind ? "active" : ""} key={kind} onClick={() => setActiveKind(kind)}>
                {kindLabels[kind]}
              </button>
            ))}
          </div>
          <div className="evidence-list">
            {evidence.map((item) => (
              <details className="evidence-item" key={item.id}>
                <summary><span>{item.kind}</span><strong>{item.title}</strong><CaretDown size={14} /></summary>
                <p>{item.relevance}</p>
                <small>{item.source}{item.timestamp ? ` · ${item.timestamp}` : ""}</small>
                <blockquote>{item.snippet}</blockquote>
                <EvidenceActions item={savedEvidenceToEvidence(item)} candidates={candidates} onOpenStock={onOpenStock} onRemove={() => onRemoveEvidence(item.id)} />
              </details>
            ))}
          </div>
        </>
      )}
      {currentEvidence.length > 0 && (
        <section className="current-evidence-tray">
          <strong>本轮证据</strong>
          {currentEvidence.slice(0, 6).map((item) => (
            <div className="source-row" key={item.id}>
              <span>{item.title}</span>
              <button className="mini-action" onClick={() => onSaveEvidence(item)} disabled={isEvidenceSaved(item)}>
                <BookmarkSimple size={14} /> {isEvidenceSaved(item) ? "已保存" : "保存"}
              </button>
            </div>
          ))}
        </section>
      )}
    </aside>
  );
}

function EvidenceActions({
  item,
  candidates,
  onOpenStock,
  onRemove
}: {
  item: EvidenceItem | SavedEvidenceItem;
  candidates: Candidate[];
  onOpenStock: (candidate: Candidate) => void;
  onRemove: () => void;
}) {
  const relatedCandidate = findCandidateByTicker(candidates, item.relatedTicker);
  return (
    <div className="asset-actions">
      {item.url && (
        <a className="mini-action" href={item.url} target="_blank" rel="noreferrer">
          打开来源
        </a>
      )}
      {relatedCandidate && (
        <button className="mini-action" onClick={() => onOpenStock(relatedCandidate)}>
          <ChartLine size={14} /> 查看行情
        </button>
      )}
      <button className="mini-action danger" onClick={onRemove}>
        <Trash size={14} /> 删除证据
      </button>
    </div>
  );
}

function TimelineRail({ steps }: { steps: AnalysisStep[] }) {
  return (
    <footer className="timeline-rail">
      {steps.map((step) => (
        <div className={`timeline-step ${step.status}`} key={step.id}>
          <div className="step-dot">
            {step.status === "done" ? <CheckCircle size={15} weight="fill" /> : step.status === "failed" ? <SealWarning size={15} /> : null}
          </div>
          <div><strong>{step.label}</strong><span>{step.messages.at(-1) || step.status}</span></div>
        </div>
      ))}
    </footer>
  );
}

function ResearchRoomPulse({ steps, briefReady, onOpenRoom, onOpenBrief }: { steps: AnalysisStep[]; briefReady: boolean; onOpenRoom: () => void; onOpenBrief: () => void }) {
  const active = steps.find((step) => step.status === "running");
  return (
    <section className="research-room-pulse terminal-panel">
      <header className="research-room-head"><div><strong>{briefReady ? "简报已经生成" : "研讨室正在讨论中"}</strong><span>{briefReady ? "研究结论已汇总，可以查看完整机会简报" : (active?.messages.at(-1) || "多空观点、风险与验证路径正在汇总")}</span></div></header>
      <div className="research-room-lottie" aria-label="研讨室会议动画"><DotLottieReact src="/animations/meeting.lottie" loop autoplay /></div>
      <div className="research-room-insights"><div><ChartLine size={16} /><span><b>趋势信号正在汇总</b><small>分析消费市场变化与机会</small></span></div><div><Sparkle size={16} /><span><b>多空观点持续碰撞</b><small>从产品、渠道、品牌多维度拆解</small></span></div><div><Database size={16} /><span><b>证据链路同步中</b><small>新兴市场需求与竞争格局分析</small></span></div></div>
      <div className="research-room-actions"><button className="primary-action" onClick={onOpenRoom}>进入研讨室 <ArrowRight size={16} /></button><button className="secondary-action" onClick={onOpenBrief}><FileText size={16} /> 查看机会简报</button></div>
    </section>
  );
}

function PreferencesSheet({
  modelConfig,
  setModelConfig,
  theme,
  setTheme,
  accent,
  setAccent,
  background,
  setBackground,
  language,
  setLanguage,
  onClose
}: {
  modelConfig: ModelConfig;
  setModelConfig: (config: ModelConfig) => void;
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
  accent: string;
  setAccent: (accent: string) => void;
  background: string | null;
  setBackground: (background: string | null) => void;
  language: "zh" | "en";
  setLanguage: (language: "zh" | "en") => void;
  onClose: () => void;
}) {
  const selectBackground = (color: string) => {
    setBackground(color);
    const [red, green, blue] = hexToRgb(color);
    const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
    setTheme(luminance < 0.42 ? "dark" : "light");
  };

  return (
    <motion.div className="sheet-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.section
        className="preferences-sheet"
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 14, scale: 0.98 }}
        transition={{ type: "spring", bounce: 0, duration: 0.34 }}
      >
        <header>
          <div><span>{uiText("设置", language)}</span><h2>{uiText("模型与终端配置", language)}</h2></div>
          <button className="icon-button" onClick={onClose}><X size={18} /></button>
        </header>
        <div className="settings-grid">
          <section>
            <h3>{uiText("模型", language)}</h3>
            <label>服务商<input value={modelConfig.provider} onChange={(e) => setModelConfig({ ...modelConfig, provider: e.target.value })} /></label>
            <label>接口地址<input value={modelConfig.baseURL} onChange={(e) => setModelConfig({ ...modelConfig, baseURL: e.target.value })} /></label>
            <label>API Key <small>如果后端 .env 已配置，这里可留空</small><input value={modelConfig.apiKey} type="password" onChange={(e) => setModelConfig({ ...modelConfig, apiKey: e.target.value })} /></label>
            <label>模型名称<input value={modelConfig.model} onChange={(e) => setModelConfig({ ...modelConfig, model: e.target.value })} /></label>
          </section>
          <section>
            <h3>{uiText("数据源", language)}</h3>
            {["A 股公开行情", "港股 / 美股公开行情", "资讯雷达 RSS", "研报与公告"].map((item) => (
              <div className="source-row" key={item}><span>{item}</span><em>可用</em></div>
            ))}
            <h3>{uiText("外观", language)}</h3>
            <div className="color-settings-title"><span>{uiText("语言 / Language", language)}</span></div>
            <div className="segmented wide">
              <button className={language === "zh" ? "active" : ""} onClick={() => setLanguage("zh")}>{uiText("中文", language)}</button>
              <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>English</button>
            </div>
            <div className="segmented wide">
              <button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}>{uiText("浅色", language)}</button>
              <button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}>{uiText("深色", language)}</button>
            </div>
            <div className="color-settings">
              <div className="color-settings-title"><span>强调色</span><code>{accent.toUpperCase()}</code></div>
              <div className="color-presets" aria-label="强调色预设">
                {accentPresets.map((color) => (
                  <button
                    key={color}
                    className={accent.toLowerCase() === color ? "active" : ""}
                    style={{ "--swatch": color } as CSSProperties}
                    onClick={() => setAccent(color)}
                    aria-label={`选择颜色 ${color}`}
                  />
                ))}
                <label className="custom-color" aria-label="自定义强调色">
                  <input type="color" value={accent} onChange={(event) => setAccent(event.target.value)} />
                  <span>自定义</span>
                </label>
              </div>
              <button className="reset-color" onClick={() => setAccent(defaultAppearance.accent)}>{uiText("恢复默认蓝色", language)}</button>
            </div>
            <div className="color-settings">
              <div className="color-settings-title"><span>背景色</span><code>{background ? background.toUpperCase() : "跟随主题"}</code></div>
              <div className="color-presets" aria-label="背景色预设">
                {backgroundPresets.map((color) => (
                  <button
                    key={color}
                    className={background?.toLowerCase() === color ? "active" : ""}
                    style={{ "--swatch": color } as CSSProperties}
                    onClick={() => selectBackground(color)}
                    aria-label={`选择背景 ${color}`}
                  />
                ))}
                <label className="custom-color" aria-label="自定义背景色">
                  <input
                    type="color"
                    value={background || (theme === "dark" ? "#0b0f16" : "#f3f5f8")}
                    onChange={(event) => selectBackground(event.target.value)}
                  />
                  <span>自定义</span>
                </label>
              </div>
              <button className="reset-color" onClick={() => setBackground(null)}>恢复原网站背景</button>
            </div>
            <p className="privacy-note">设置只保存在当前浏览器，并随分析请求发送给后端。</p>
          </section>
        </div>
      </motion.section>
    </motion.div>
  );
}
