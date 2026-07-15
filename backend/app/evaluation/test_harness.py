import os
import tempfile

from app.evaluation.cases import MOCK_CASES
from app.evaluation.harness import EvalHarness
from app.evaluation.trace_logger import TraceLogger
from app.memory.json_file_store import JSONFileMemoryStore


file_path = os.path.join(tempfile.mkdtemp(), "traces.json")
trace_logger = TraceLogger(store=JSONFileMemoryStore(file_path))

harness = EvalHarness(trace_logger=trace_logger)
traces = harness.run()
assert len(traces) == len(MOCK_CASES)

by_id = {trace.case_id: trace for trace in traces}
assert by_id["trend_001_pass"].passed is True
assert by_id["trend_002_fail"].passed is False
assert by_id["company_mapping_001_pass"].passed is True
assert by_id["company_mapping_002_fail"].passed is False
assert by_id["financial_001_pass"].passed is True
assert by_id["financial_002_fail"].passed is False

# every run produced a trace with real latency and per-evaluator scores
for trace in traces:
    assert trace.latency_ms >= 0
    assert trace.scores

# traces are saved to disk and survive a reload via a fresh store/logger
reloaded_logger = TraceLogger(store=JSONFileMemoryStore(file_path))
saved = reloaded_logger.get("trend_001_pass")
assert saved["case_id"] == "trend_001_pass"
assert saved["passed"] is True
assert len(reloaded_logger.all_traces()) == len(MOCK_CASES)

print("OK")
