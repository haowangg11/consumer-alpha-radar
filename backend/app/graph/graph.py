from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.company_mapping_agent import CompanyMappingAgent
from app.agents.consumer_psychology_agent import ConsumerPsychologyAgent
from app.agents.financial_agent import FinancialAnalysisAgent
from app.agents.investment_committee_agent import InvestmentCommitteeAgent
from app.agents.risk_critic_agent import RiskCriticAgent
from app.agents.trend_agent import TrendDiscoveryAgent
from app.graph.edges import route_after_risk_critic
from app.graph.nodes import (
    make_company_mapping_node,
    make_consumer_psychology_node,
    make_financial_analysis_node,
    make_ingest_signals_node,
    make_investment_committee_node,
    make_risk_critic_node,
    make_trend_discovery_node,
)
from app.graph.state import GraphState
from app.memory.company_memory import CompanyMemory
from app.memory.market_memory import MarketMemory
from app.memory.trend_memory import TrendMemory
from app.models.router import ModelType
from app.providers.mock_provider import MockProvider
from app.services.llm_service import LLMService
from app.services.skill_service import SkillService


def default_offline_agents() -> dict:
    """
    Wires every agent to an all-MockProvider LLMService so a graph
    built with these agents never makes an external call - mirrors
    EvalHarness.default_agents() in app.evaluation.harness, kept as
    a separate helper here because graph nodes call each agent's own
    public method directly rather than through a callable adapter.
    """

    mock_llm_service = LLMService(
        providers={
            ModelType.GPT: MockProvider(),
            ModelType.DEEPSEEK: MockProvider(),
            ModelType.QWEN: MockProvider(),
        }
    )
    return {
        "trend_discovery": TrendDiscoveryAgent(llm_service=mock_llm_service),
        "consumer_psychology": ConsumerPsychologyAgent(llm_service=mock_llm_service),
        "company_mapping": CompanyMappingAgent(llm_service=mock_llm_service),
        "financial_analysis": FinancialAnalysisAgent(llm_service=mock_llm_service),
        "risk_critic": RiskCriticAgent(llm_service=mock_llm_service),
        "investment_committee": InvestmentCommitteeAgent(llm_service=mock_llm_service),
    }


def build_graph(
    agents: dict = None,
    skill_service: SkillService = None,
    trend_memory: TrendMemory = None,
    company_memory: CompanyMemory = None,
    market_memory: MarketMemory = None,
):
    """
    Wires the Trend Discovery -> Consumer Psychology -> Company
    Mapping -> Financial Analysis -> Risk Critic -> Investment
    Committee pipeline as a LangGraph StateGraph. Risk Critic can
    send the graph back to Company Mapping for a bounded number of
    revisions before it is forced to synthesize (see edges.py).

    Every dependency is overridable so callers (tests, future
    API wiring) can swap in offline/mock-backed agents and services
    without touching graph structure - the compiled graph never
    imports a concrete provider or skill implementation itself.
    """

    agents = agents or {
        "trend_discovery": TrendDiscoveryAgent(),
        "consumer_psychology": ConsumerPsychologyAgent(),
        "company_mapping": CompanyMappingAgent(),
        "financial_analysis": FinancialAnalysisAgent(),
        "risk_critic": RiskCriticAgent(),
        "investment_committee": InvestmentCommitteeAgent(),
    }
    skill_service = skill_service or SkillService()
    trend_memory = trend_memory or TrendMemory()
    company_memory = company_memory or CompanyMemory()
    market_memory = market_memory or MarketMemory()

    graph = StateGraph(GraphState)
    graph.add_node("ingest_signals", make_ingest_signals_node(skill_service))
    graph.add_node(
        "trend_discovery",
        make_trend_discovery_node(agents["trend_discovery"], trend_memory),
    )
    graph.add_node(
        "consumer_psychology",
        make_consumer_psychology_node(agents["consumer_psychology"]),
    )
    graph.add_node(
        "company_mapping",
        make_company_mapping_node(agents["company_mapping"], company_memory),
    )
    graph.add_node(
        "financial_analysis",
        make_financial_analysis_node(agents["financial_analysis"], market_memory),
    )
    graph.add_node("risk_critic", make_risk_critic_node(agents["risk_critic"]))
    graph.add_node(
        "investment_committee",
        make_investment_committee_node(agents["investment_committee"]),
    )

    graph.add_edge(START, "ingest_signals")
    graph.add_edge("ingest_signals", "trend_discovery")
    graph.add_edge("trend_discovery", "consumer_psychology")
    graph.add_edge("consumer_psychology", "company_mapping")
    graph.add_edge("company_mapping", "financial_analysis")
    graph.add_edge("financial_analysis", "risk_critic")
    graph.add_conditional_edges(
        "risk_critic",
        route_after_risk_critic,
        {"revise": "company_mapping", "synthesize": "investment_committee"},
    )
    graph.add_edge("investment_committee", END)

    return graph.compile(checkpointer=MemorySaver())
