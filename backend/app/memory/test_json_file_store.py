import os
import tempfile

from app.memory.json_file_store import JSONFileMemoryStore


tmp_dir = tempfile.mkdtemp()
file_path = os.path.join(tmp_dir, "nested", "store.json")

store = JSONFileMemoryStore(file_path)

# set/get
store.set("trends", "protein_coffee", {"momentum_score": 85, "category": "beverage"})
store.set("trends", "cold_brew", {"momentum_score": 40, "category": "beverage"})
assert store.get("trends", "protein_coffee") == {"momentum_score": 85, "category": "beverage"}
assert store.get("trends", "missing_key") is None

# namespaces do not collide
store.set("companies", "protein_coffee", {"ticker": "KDP"})
assert store.get("companies", "protein_coffee") == {"ticker": "KDP"}
assert store.get("trends", "protein_coffee") == {"momentum_score": 85, "category": "beverage"}

# query with filters
beverages = store.query("trends", category="beverage")
assert len(beverages) == 2
high_momentum = store.query("trends", category="beverage", momentum_score=85)
assert high_momentum == [{"momentum_score": 85, "category": "beverage"}]
assert store.query("unknown_namespace") == []

# reload from disk: a fresh instance pointed at the same file sees prior writes
reloaded = JSONFileMemoryStore(file_path)
assert reloaded.get("trends", "protein_coffee") == {"momentum_score": 85, "category": "beverage"}
assert reloaded.get("companies", "protein_coffee") == {"ticker": "KDP"}
assert len(reloaded.query("trends")) == 2

print("OK")
