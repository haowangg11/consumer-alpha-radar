from app.agents.trend_agent import TrendDiscoveryAgent


agent = TrendDiscoveryAgent()


data = [
    "protein coffee discussions increased",
    "health drink searches rising"
]


result = agent.analyze(data)


print(result)