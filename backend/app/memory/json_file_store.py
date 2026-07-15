import json
import os
from threading import Lock

from app.memory.base import MemoryStore


class JSONFileMemoryStore(MemoryStore):
    """
    Persists memory as a single JSON file on disk, namespaced within
    the file (top-level key = namespace, nested key = record key).

    Every read reloads from disk rather than caching in-process, so
    a freshly constructed store pointed at the same file always sees
    the last write - this is the guarantee the reload-from-disk tests
    depend on.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = Lock()

        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.file_path):
            self._write({})

    def _read(self) -> dict:
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def set(self, namespace: str, key: str, value: dict) -> None:
        with self._lock:
            data = self._read()
            data.setdefault(namespace, {})[key] = value
            self._write(data)

    def get(self, namespace: str, key: str) -> dict:
        data = self._read()
        return data.get(namespace, {}).get(key)

    def query(self, namespace: str, **filters) -> list:
        data = self._read()
        records = data.get(namespace, {})
        return [
            value
            for value in records.values()
            if all(value.get(k) == v for k, v in filters.items())
        ]
