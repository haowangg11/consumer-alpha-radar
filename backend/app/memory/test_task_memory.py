from app.memory.task_memory import TaskMemory


memory = TaskMemory()

memory.set("draft_trend", {"name": "protein coffee", "confidence": 0.7})
assert memory.get("draft_trend") == {"name": "protein coffee", "confidence": 0.7}
assert memory.get("missing_key") is None

memory.set("draft_company", {"name": "protein coffee", "ticker": "KDP"})
matches = memory.query(name="protein coffee")
assert len(matches) == 2

memory.clear()
assert memory.get("draft_trend") is None
assert memory.query() == []

# a second instance never sees another task's state - purely in-process
other = TaskMemory()
memory.set("draft_trend", {"name": "cold brew"})
assert other.get("draft_trend") is None

print("OK")
