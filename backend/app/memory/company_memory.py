from app.memory.json_file_store import JSONFileMemoryStore

DEFAULT_FILE_PATH = "data/memory/company_memory.json"
NAMESPACE = "companies"


class CompanyMemory:
    """
    Long-term memory of trend-to-company mappings. Thin wrapper over
    JSONFileMemoryStore fixed to the "companies" namespace, so agents
    never have to pass a namespace or a store by hand.
    """

    def __init__(self, store: JSONFileMemoryStore = None):
        self.store = store or JSONFileMemoryStore(DEFAULT_FILE_PATH)

    def record_company(self, ticker: str, data: dict) -> None:
        self.store.set(NAMESPACE, ticker, data)

    def get_company(self, ticker: str) -> dict:
        return self.store.get(NAMESPACE, ticker)

    def find_companies(self, **filters) -> list:
        return self.store.query(NAMESPACE, **filters)
