"""
Experimental configurations A-F for the secure-persistence evaluation.

Each configuration switches four mechanisms on or off:

  enc     AES-GCM checkpoint encryption (StrictEncryptedSerializer)
  strict  strict MsgPack deserialization (no pickle, built-in allowlist only)
  minim   sensitive-state minimization (minimize_state in writer_compose)
  ledger  execution ledger (at-most-once send)

Everything is assembled from the production building blocks in
governance/checkpoint_store.py and governance/approval.py; nothing in
them is modified. Held constant in every configuration: owner-only
file permissions, master-key derivation, exit-only durability,
completed-thread purge, and the single flow rule.

For experiments only. build_store() refuses the deployed store path, and
the weakened configurations are meant for synthetic data in temporary
directories.
"""
import contextlib
import os
import sqlite3

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

import agents.approval_flow as approval_flow
from governance.approval import SENSITIVE_CROSSED_TO_EXTERNAL, ApprovalService, ExecutionLedger
from governance.checkpoint_store import (
    CHECKPOINT_DB, DEFAULT_DIR, LEDGER_DB, AesGcmCipher, StrictEncryptedSerializer, derive_key,
    load_master_key, make_private,
)

CONFIGS = {
    "A": {"enc": False, "strict": False, "minim": False, "ledger": False},
    "B": {"enc": True, "strict": True, "minim": True, "ledger": True},
    "C": {"enc": False, "strict": True, "minim": True, "ledger": True},
    "D": {"enc": True, "strict": False, "minim": True, "ledger": True},
    "E": {"enc": True, "strict": True, "minim": False, "ledger": True},
    "F": {"enc": True, "strict": True, "minim": True, "ledger": False},
}
DESCRIPTIONS = {
    "A": "Baseline: all four off",
    "B": "Full PrivAgent",
    "C": "Full without encryption",
    "D": "Full without strict deserialization",
    "E": "Full without state minimization",
    "F": "Full without execution ledger",
}
FLOW_RULES = [SENSITIVE_CROSSED_TO_EXTERNAL]


class NullLedger:
    """Stand-in when the ledger is off: every claim succeeds, nothing is
    recorded, so nothing stops a second execution."""

    def claim(self, action_id, run_id, tool, action_digest):
        return True

    def finish(self, action_id, status):
        pass

    def status(self, action_id):
        return None


def serializer(flags, key):
    inner = (JsonPlusSerializer(pickle_fallback=False, allowed_json_modules=None,
                                allowed_msgpack_modules=None)
             if flags["strict"] else
             # The library's own permissive default: reconstructs any type
             # named in the data (with a warning).
             JsonPlusSerializer(allowed_msgpack_modules=True))
    if flags["enc"]:
        return StrictEncryptedSerializer(AesGcmCipher(derive_key(key, "checkpoint-aes-gcm")), inner)
    return inner


class ExperimentStore:
    def __init__(self, config_id, directory, master_key=None):
        if os.path.abspath(directory) == os.path.abspath(DEFAULT_DIR):
            raise ValueError("Experiments must not use the deployed approval store")
        self.config_id = config_id
        self.flags = CONFIGS[config_id]
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        make_private(directory)
        self.master_key = master_key or load_master_key(directory)
        self.checkpoint_path = os.path.join(directory, CHECKPOINT_DB)
        self.ledger_path = os.path.join(directory, LEDGER_DB)
        self.conn = sqlite3.connect(self.checkpoint_path, check_same_thread=False)
        make_private(self.checkpoint_path)
        self.checkpointer = SqliteSaver(self.conn, serde=serializer(self.flags, self.master_key))
        self.checkpointer.setup()
        if self.flags["ledger"]:
            self.ledger = ExecutionLedger(self.ledger_path)
            make_private(self.ledger_path)
        else:
            self.ledger = NullLedger()
        self.service = ApprovalService(self.ledger, flow_rules=FLOW_RULES,
                                       key=derive_key(self.master_key, "approval-service"),
                                       purge_completed=True)

    def close(self):
        self.conn.close()


@contextlib.contextmanager
def minimization(enabled):
    """Disables M3 for the duration (a test-only patch of the module-level
    function writer_compose calls); a no-op when enabled."""
    if enabled:
        yield
        return
    original = approval_flow.minimize_state
    approval_flow.minimize_state = lambda state, provenance: None
    try:
        yield
    finally:
        approval_flow.minimize_state = original


def store_files(directory):
    """All persistent artifacts of a store: database, WAL, SHM, journal, ledger."""
    return sorted(os.path.join(directory, f) for f in os.listdir(directory)
                  if f.startswith((CHECKPOINT_DB, LEDGER_DB)))
