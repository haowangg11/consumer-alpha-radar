from app.evaluation.trace import EvaluationTrace
from app.memory.json_file_store import JSONFileMemoryStore

DEFAULT_FILE_PATH = "data/evaluation/traces.json"
NAMESPACE = "traces"


class TraceLogger:
    """
    Persists EvaluationTrace records via JSONFileMemoryStore, reusing
    the Memory Layer's on-disk persistence rather than rolling a
    second file format just for the harness.
    """

    def __init__(self, store: JSONFileMemoryStore = None):
        self.store = store or JSONFileMemoryStore(DEFAULT_FILE_PATH)

    def log(self, trace: EvaluationTrace) -> None:
        self.store.set(NAMESPACE, trace.case_id, trace.to_dict())

    def get(self, case_id: str) -> dict:
        return self.store.get(NAMESPACE, case_id)

    def all_traces(self) -> list:
        return self.store.query(NAMESPACE)
