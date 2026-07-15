class TaskMemory:
    """
    Short-term scratchpad for a single agent task/run.

    Deliberately NOT a MemoryStore - it never touches disk and does
    not survive past the process, unlike TrendMemory, CompanyMemory,
    and MarketMemory. Each agent run should construct its own
    instance rather than share one across tasks.
    """

    def __init__(self):
        self._data: dict = {}

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def get(self, key: str):
        return self._data.get(key)

    def query(self, **filters) -> list:
        return [
            value
            for value in self._data.values()
            if all(value.get(k) == v for k, v in filters.items())
        ]

    def clear(self) -> None:
        self._data.clear()
