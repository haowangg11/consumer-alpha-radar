import os
import tempfile

from app.memory.json_file_store import JSONFileMemoryStore
from app.memory.market_memory import MarketMemory


file_path = os.path.join(tempfile.mkdtemp(), "market_memory.json")

memory = MarketMemory(store=JSONFileMemoryStore(file_path))
memory.record_snapshot("KDP_2026Q1", {"ticker": "KDP", "revenue_growth": 0.08})
memory.record_snapshot("SBUX_2026Q1", {"ticker": "SBUX", "revenue_growth": 0.03})

assert memory.get_snapshot("KDP_2026Q1") == {"ticker": "KDP", "revenue_growth": 0.08}
assert memory.get_snapshot("missing") is None
assert len(memory.find_snapshots(ticker="KDP")) == 1

# reload from disk via a fresh MarketMemory/store pair pointed at the same file
reloaded = MarketMemory(store=JSONFileMemoryStore(file_path))
assert reloaded.get_snapshot("SBUX_2026Q1") == {"ticker": "SBUX", "revenue_growth": 0.03}
assert len(reloaded.find_snapshots(ticker="SBUX")) == 1

print("OK")
