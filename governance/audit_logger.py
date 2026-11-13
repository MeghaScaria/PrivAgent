"""
Audit logger. Every governance decision — whether it came from the ML
risk model or the deterministic policy engine — is appended here as one
JSON line, plus kept in memory for the dashboard's live view. This is
intentionally append-only: nothing is ever mutated or deleted, matching
how an audit trail should behave.
"""
import json
import os
import threading
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "audit_log.jsonl")
# Agent-to-agent handoffs go to their own file, next to the audit log:
# the dashboard reads audit_log.jsonl as tool decisions only. The two
# are joined by run_id and the per-run seq number.
HANDOFF_LOG_NAME = "handoff_log.jsonl"
# Human-approval events (requests, reviewer responses, executions).
APPROVAL_LOG_NAME = "approval_log.jsonl"

_lock = threading.Lock()


class AuditLogger:
    def __init__(self, log_file=None):
        self.log_file = log_file or LOG_FILE
        self.handoff_log_file = os.path.join(os.path.dirname(self.log_file), HANDOFF_LOG_NAME)
        self.approval_log_file = os.path.join(os.path.dirname(self.log_file), APPROVAL_LOG_NAME)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._events = []  # in-memory mirror for fast dashboard reads
        self._handoffs = []
        self._approvals = []

    def record(self, run_id, agent_role, tool_name, risk_score, decision,
               source, reason, trajectory_length, task_type=None,
               event_id=None, seq=None, **extra):
        """extra: optional fields (sensitivity check, flags, shadow
        decision); only those that are set are written."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "agent_role": agent_role,
            "tool_name": tool_name,
            "risk_score": round(float(risk_score), 4),
            "decision": decision,
            "source": source,           # "ml_model" or "policy_engine"
            "reason": reason,
            "trajectory_length": trajectory_length,
            "task_type": task_type,
            "event_id": event_id,
            "seq": seq,
            **{k: v for k, v in extra.items() if v},
        }
        with _lock:
            self._events.append(event)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        return event

    def record_handoff(self, event, refs):
        """One handoff event plus a snapshot of every ref it mentions
        (including its origins), so each line can be traced on its own."""
        line = {**event, "refs": refs}
        with _lock:
            self._handoffs.append(line)
            with open(self.handoff_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, default=str) + "\n")
        return line

    def record_approval(self, event):
        with _lock:
            self._approvals.append(event)
            with open(self.approval_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        return event

    def approvals_for_run(self, run_id):
        with _lock:
            return [e for e in self._approvals if e["run_id"] == run_id]

    def handoffs_for_run(self, run_id):
        with _lock:
            return [e for e in self._handoffs if e["run_id"] == run_id]

    def events_for_run(self, run_id):
        with _lock:
            return [e for e in self._events if e["run_id"] == run_id]

    def all_events(self, limit=500):
        with _lock:
            return self._events[-limit:]

    def clear_memory(self):
        """Clears the in-memory mirror only; the on-disk log is never
        truncated, since it is an audit trail."""
        with _lock:
            self._events = []

    def load_from_disk(self, limit=500):
        """Rehydrates the in-memory mirror from the on-disk log, e.g. on
        dashboard restart."""
        if not os.path.exists(self.log_file):
            return
        with _lock:
            self._events = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-limit:]
            for line in lines:
                line = line.strip()
                if line:
                    self._events.append(json.loads(line))


_default_logger = None


def get_audit_logger():
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger
