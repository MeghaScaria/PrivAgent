"""
Audit logger. Every governance decision — whether it came from the ML
risk model or the deterministic policy engine — is appended here as one
JSON line, plus kept in memory for the dashboard's live view. This is
intentionally append-only: nothing is ever mutated or deleted, matching
how an audit trail should behave.
"""
import hashlib
import json
import os
import sqlite3
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
            # v2 records also carry "combination" (via extra): ML score and
            # decision, every rule fired, precedence, the v1 comparison.
            "reason": reason,
            "trajectory_length": trajectory_length,
            "task_type": task_type,
            "event_id": event_id,
            "seq": seq,
            **{k: v for k, v in extra.items() if v},
        }
        with _lock:
            self._events.append(event)
            self._append(self.log_file, event)
        return event

    def record_handoff(self, event, refs):
        """One handoff event plus a snapshot of every ref it mentions
        (including its origins), so each line can be traced on its own."""
        line = {**event, "refs": refs}
        with _lock:
            self._handoffs.append(line)
            self._append(self.handoff_log_file, line, default=str)
        return line

    def record_approval(self, event):
        with _lock:
            self._approvals.append(event)
            self._append(self.approval_log_file, event, default=str)
        return event

    def _append(self, path, entry, default=None):
        """Writes one JSON line. Called with _lock held. The v1 format is
        exactly json.dumps(entry, default=default); ChainedAuditLogger
        overrides this to add the hash chain."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=default) + "\n")

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


# -- v2: hash-chained logs (V2_PLAN.md WP3.1) --------------------------------
#
# Each line of a chained log carries prev_hash (the previous line's
# entry_hash; GENESIS_HASH for the first line) and
#   entry_hash = SHA-256(canonical_json(line without entry_hash) || prev_hash)
# with one chain per file. verify_chain() detects an edited, deleted,
# reordered or partly written line from the chain alone. A whole-line
# truncation of the tail leaves a valid shorter chain, and so does a
# rewrite of the entire file by someone who rebuilds every hash: those are
# detected only against the anchored head, the latest (line_count,
# entry_hash) per file, which the logger stores in the v2 approval ledger
# SQLite (table chain_heads). Anchoring only helps while the ledger itself
# is out of the attacker's reach; that is a limitation, not a guarantee.

GENESIS_HASH = "0" * 64
_ROOT = os.path.dirname(LOG_DIR)
V2_LEDGER_DB = os.path.join(_ROOT, "runtime", "approvals", "v2", "ledger.sqlite")


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def entry_hash(entry_without_hash, prev_hash):
    return hashlib.sha256(canonical_json(entry_without_hash) + prev_hash.encode("ascii")).hexdigest()


def _head_key(path):
    return os.path.normcase(os.path.abspath(path))


def _head_conn(head_db):
    os.makedirs(os.path.dirname(head_db), exist_ok=True)
    conn = sqlite3.connect(head_db, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS chain_heads (
        log_path TEXT PRIMARY KEY, line_count INTEGER NOT NULL,
        head_hash TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    return conn


def store_chain_head(head_db, log_path, line_count, head_hash):
    with _head_conn(head_db) as conn:
        conn.execute("INSERT INTO chain_heads VALUES (?, ?, ?, ?) ON CONFLICT(log_path) DO UPDATE "
                     "SET line_count = excluded.line_count, head_hash = excluded.head_hash, "
                     "updated_at = excluded.updated_at",
                     (_head_key(log_path), line_count, head_hash,
                      datetime.now(timezone.utc).isoformat()))


def load_chain_head(head_db, log_path):
    """(line_count, head_hash) anchored for this log, or None."""
    if not os.path.exists(head_db):
        return None
    with _head_conn(head_db) as conn:
        row = conn.execute("SELECT line_count, head_hash FROM chain_heads WHERE log_path = ?",
                           (_head_key(log_path),)).fetchone()
    return (row[0], row[1]) if row else None


def verify_chain(path, head_db=None):
    """(ok, first_bad_line). first_bad_line is 1-based: the first line
    that is malformed, partly written, out of chain or altered. With
    head_db, the file must also end exactly at the anchored head; if it
    stops early (tail truncated), first_bad_line is the first missing
    line. (False, None) means the chain is intact but head_db has no
    anchor for this file, so a truncated tail or a full rewrite could not
    be ruled out."""
    prev, count = GENESIS_HASH, 0
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as f:
            for count, raw in enumerate(f, 1):
                if not raw.endswith("\n"):
                    return False, count
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    return False, count
                if not isinstance(entry, dict) or entry.get("prev_hash") != prev:
                    return False, count
                claimed = entry.pop("entry_hash", None)
                if claimed != entry_hash(entry, prev):
                    return False, count
                prev = claimed
    if head_db is None:
        return True, None
    head = load_chain_head(head_db, path)
    if head is None:
        return (True, None) if count == 0 else (False, None)
    head_count, head_hash = head
    if count != head_count or prev != head_hash:
        return False, min(count, head_count) + 1
    return True, None


class ChainedAuditLogger(AuditLogger):
    """v2 audit logger: same records as AuditLogger, plus a hash chain per
    file and an anchored head (see the comment block above). Writes only
    to logs/v2/ (the default) or another directory outside logs/; it
    refuses the v1 log directory."""

    def __init__(self, log_file=None, head_db=V2_LEDGER_DB):
        log_file = log_file or LOG_FILE_V2
        if _head_key(os.path.dirname(log_file)) == _head_key(LOG_DIR):
            raise ValueError("ChainedAuditLogger must not write to the v1 logs in logs/")
        super().__init__(log_file)
        self.head_db = head_db
        self._heads = {}   # path -> (line_count, last entry_hash)

    def _current_head(self, path):
        if path not in self._heads:
            count, last = 0, GENESIS_HASH
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    for count, raw in enumerate(f, 1):
                        last = json.loads(raw)["entry_hash"]
            self._heads[path] = (count, last)
        return self._heads[path]

    def _append(self, path, entry, default=None):
        count, prev = self._current_head(path)
        line = json.loads(json.dumps(entry, default=default))   # exactly what is stored
        line["prev_hash"] = prev
        line["entry_hash"] = entry_hash(line, prev)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        self._heads[path] = (count + 1, line["entry_hash"])
        if self.head_db:
            store_chain_head(self.head_db, path, count + 1, line["entry_hash"])

    def verify(self):
        """verify_chain for each of this logger's three files."""
        return {p: verify_chain(p, self.head_db)
                for p in (self.log_file, self.handoff_log_file, self.approval_log_file)}


_default_logger = None

# v2 (V2_PLAN.md §0): v2 runs never append to the v1 logs in logs/*.jsonl.
LOG_FILE_V2 = os.path.join(LOG_DIR, "v2", "audit_log.jsonl")
_default_logger_v2 = None


def get_audit_logger(governance_version="v1"):
    """The shared logger: logs/ for v1 (unchanged); for v2 a
    ChainedAuditLogger in logs/v2/, anchored in the v2 approval ledger."""
    global _default_logger, _default_logger_v2
    if governance_version == "v2":
        if _default_logger_v2 is None:
            _default_logger_v2 = ChainedAuditLogger(LOG_FILE_V2, head_db=V2_LEDGER_DB)
        return _default_logger_v2
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger
