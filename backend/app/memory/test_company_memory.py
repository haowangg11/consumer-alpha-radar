import os
import tempfile

from app.memory.json_file_store import JSONFileMemoryStore
from app.memory.company_memory import CompanyMemory


file_path = os.path.join(tempfile.mkdtemp(), "company_memory.json")

memory = CompanyMemory(store=JSONFileMemoryStore(file_path))
memory.record_company("KDP", {"name": "Keurig Dr Pepper", "trend_id": "protein_coffee"})
memory.record_company("SBUX", {"name": "Starbucks", "trend_id": "protein_coffee"})

assert memory.get_company("KDP") == {"name": "Keurig Dr Pepper", "trend_id": "protein_coffee"}
assert memory.get_company("missing") is None
assert len(memory.find_companies(trend_id="protein_coffee")) == 2

# reload from disk via a fresh CompanyMemory/store pair pointed at the same file
reloaded = CompanyMemory(store=JSONFileMemoryStore(file_path))
assert reloaded.get_company("SBUX") == {"name": "Starbucks", "trend_id": "protein_coffee"}
assert len(reloaded.find_companies(trend_id="protein_coffee")) == 2

print("OK")
