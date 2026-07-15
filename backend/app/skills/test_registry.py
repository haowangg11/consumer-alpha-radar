from app.skills.registry import SkillRegistry


registry = SkillRegistry()

result = registry.get("google_trends").run(
    query_type="keyword_interest",
    payload={"keywords": ["protein coffee"]},
)
assert result["skill"] == "google_trends"

metadata_list = registry.list_metadata()
assert {m.name for m in metadata_list} == {"google_trends", "reddit", "stock_data"}
assert all(m.version for m in metadata_list)

try:
    registry.get("unknown_skill")
    raise AssertionError("expected KeyError for unknown skill")
except KeyError:
    pass

print("registered skills:", [(m.name, m.version) for m in metadata_list])
print("sample result:", result)
print("OK")
