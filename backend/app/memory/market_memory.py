from app.memory.json_file_store import JSONFileMemoryStore

DEFAULT_FILE_PATH = "data/memory/market_memory.json"
NAMESPACE = "market_snapshots"


class MarketMemory:
    """
    Long-term memory of financial/market snapshots produced by the
    Financial Analysis Agent. Thin wrapper over JSONFileMemoryStore
    fixed to the "market_snapshots" namespace, so agents never have
    to pass a namespace or a store by hand.
    """

    def __init__(self, store: JSONFileMemoryStore = None):
        self.store = store or JSONFileMemoryStore(DEFAULT_FILE_PATH)

    def record_snapshot(self, snapshot_id: str, data: dict) -> None:
        self.store.set(NAMESPACE, snapshot_id, data)

    def get_snapshot(self, snapshot_id: str) -> dict:
        return self.store.get(NAMESPACE, snapshot_id)

    def find_snapshots(self, **filters) -> list:
        return self.store.query(NAMESPACE, **filters)
