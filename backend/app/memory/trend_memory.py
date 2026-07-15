from app.memory.json_file_store import JSONFileMemoryStore

DEFAULT_FILE_PATH = "data/memory/trend_memory.json"
NAMESPACE = "trends"


class TrendMemory:
    """
    Long-term memory of discovered consumer trends. Thin wrapper over
    JSONFileMemoryStore fixed to the "trends" namespace, so agents
    never have to pass a namespace or a store by hand.
    """

    def __init__(self, store: JSONFileMemoryStore = None):
        self.store = store or JSONFileMemoryStore(DEFAULT_FILE_PATH)

    def record_trend(self, trend_id: str, data: dict) -> None:
        self.store.set(NAMESPACE, trend_id, data)

    def get_trend(self, trend_id: str) -> dict:
        return self.store.get(NAMESPACE, trend_id)

    def find_trends(self, **filters) -> list:
        return self.store.query(NAMESPACE, **filters)
