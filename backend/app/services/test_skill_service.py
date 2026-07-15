from app.services.skill_service import SkillService


service = SkillService()

result = service.run("reddit", "sentiment_scan", {"subreddit": "wallstreetbets", "keywords": ["protein coffee"]})
assert result["skill"] == "reddit"

available = service.list_available_skills()
assert {m.name for m in available} == {"google_trends", "reddit", "stock_data"}

print("available skills:", [(m.name, m.version) for m in available])
print("sample result:", result)
print("OK")
