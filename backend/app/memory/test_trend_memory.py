import os
import tempfile

from app.memory.json_file_store import JSONFileMemoryStore
from app.memory.trend_memory import TrendMemory


file_path = os.path.join(tempfile.mkdtemp(), "trend_memory.json")

memory = TrendMemory(store=JSONFileMemoryStore(file_path))
memory.record_trend("protein_coffee", {"category": "beverage", "momentum_score": 85})
memory.record_trend("cold_brew", {"category": "beverage", "momentum_score": 40})

assert memory.get_trend("protein_coffee") == {"category": "beverage", "momentum_score": 85}
assert memory.get_trend("missing") is None
assert len(memory.find_trends(category="beverage")) == 2
assert memory.find_trends(momentum_score=85) == [{"category": "beverage", "momentum_score": 85}]

# reload from disk via a fresh TrendMemory/store pair pointed at the same file
reloaded = TrendMemory(store=JSONFileMemoryStore(file_path))
assert reloaded.get_trend("protein_coffee") == {"category": "beverage", "momentum_score": 85}
assert len(reloaded.find_trends(category="beverage")) == 2

print("OK")
