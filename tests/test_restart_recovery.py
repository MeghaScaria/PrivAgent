"""
Restart-recovery tests for the persistent approval store
(governance/checkpoint_store.py). Each step runs in its own Python
process (tests/restart_worker.py): the first one pauses for review and
is then killed outright; later processes recover the pending review
from the SQLite store and answer it.

Run with pytest, or directly: python tests/test_restart_recovery.py
"""
import json
import os
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cryptography.exceptions import InvalidTag
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

import tests.test_handoff_instrumentation as h
from agents.mcp_client import get_mcp_manager
from governance.checkpoint_store import (
    CHECKPOINT_DB, LEDGER_DB, MASTER_KEY_FILE, AesGcmCipher, DevApprovalStore, check_private,
    derive_key, load_master_key, strict_serializer,
)
from tests.restart_worker import TASK

WORKER = os.path.join(ROOT, "tests", "restart_worker.py")
GADGETS_BUILT = []


@dataclass
class Gadget:
    """Stands in for an arbitrary class an attacker might plant in a
    checkpoint. Module-level so a permissive loader can find and build it."""
    x: int = 1

    def __post_init__(self):
        GADGETS_BUILT.append(1)

# How long to wait for a worker event. A worker first starts its own MCP
# servers, which may take up to PRIVAGENT_MCP_START_TIMEOUT (default 30 s),
# so the wait is that plus a margin, and never below the original 120 s.
# Unset: 30 + 90 = 120 s, as before.
MCP_START_WAIT_MARGIN = 90


def _worker_timeout():
    try:
        start = float(os.environ.get("PRIVAGENT_MCP_START_TIMEOUT", 30))
    except ValueError:
        start = 30
    return max(120, (start if start > 0 else 30) + MCP_START_WAIT_MARGIN)


TIMEOUT = _worker_timeout()


class Worker:
    def __init__(self, command, store, thread, marker, *extra):
        env = {k: v for k, v in os.environ.items() if k != "PRIVAGENT_MASTER_KEY"}
        # The worker's stderr goes to a temp log file (not DEVNULL), so a
        # failing test can show why the worker stopped.
        fd, self.stderr_path = tempfile.mkstemp(prefix=f"restart_worker_{command}_", suffix=".log")
        self._stderr = os.fdopen(fd, "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, WORKER, command, "--store", store, "--thread", thread,
             "--marker", marker, *extra],
            stdout=subprocess.PIPE, stderr=self._stderr, text=True, env=env, cwd=ROOT)
        self.lines = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line.startswith("{"):
                self.lines.put(json.loads(line))
        self.lines.put(None)

    def next_event(self):
        event = self.lines.get(timeout=TIMEOUT)
        assert event is not None, (f"worker exited early (code {self.proc.poll()}); "
                                   f"stderr: {self.stderr_path}\n{self.stderr_tail()}")
        return event

    def stderr_tail(self, lines=25):
        """Last lines of the worker's stderr log, warnings left out."""
        self._stderr.flush()
        try:
            with open(self.stderr_path, encoding="utf-8", errors="replace") as f:
                text = [x.rstrip() for x in f if "Warning" not in x and x.strip()]
        except OSError as exc:
            return f"(could not read stderr log: {exc})"
        return "\n".join(text[-lines:])

    def events_until_exit(self):
        events = []
        while True:
            event = self.lines.get(timeout=TIMEOUT)
            if event is None:
                break
            events.append(event)
        self.proc.wait(timeout=TIMEOUT)
        return events

    def kill(self):
        self.proc.kill()
        self.proc.wait(timeout=TIMEOUT)


def paused_run():
    """Starts a run in a separate process, waits for it to pause, then
    kills that process."""
    store, thread, marker = tempfile.mkdtemp(), f"thread-{uuid.uuid4().hex[:8]}", \
        f"RESTART-{uuid.uuid4().hex[:12]}"
    starter = Worker("start", store, thread, marker)
    event = starter.next_event()
    assert event["event"] == "paused" and event["sent"] == 0, event
    starter.kill()
    assert starter.proc.returncode != 0  # killed, not a clean exit
    return store, thread, marker, event["action_id"]


def approval_events(store):
    path = os.path.join(store, "approval_log.jsonl")
    with open(path) as f:
        return [json.loads(l) for l in f]


def thread_rows(store, thread):
    with sqlite3.connect(os.path.join(store, CHECKPOINT_DB)) as conn:
        return conn.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?",
                            (thread,)).fetchone()[0]


def test_store_location_and_access_control():
    directory = tempfile.mkdtemp()
    store = DevApprovalStore(directory)
    try:
        for name in (CHECKPOINT_DB, LEDGER_DB, MASTER_KEY_FILE):
            path = os.path.join(directory, name)
            assert os.path.isfile(path), name
            assert check_private(path) == [], (name, check_private(path))
        assert check_private(directory) == []
        assert all(v == [] for v in store.access_problems().values())
        assert store.checkpoint_path == os.path.join(directory, CHECKPOINT_DB)
    finally:
        store.close()


def test_strict_deserialization_and_encryption():
    key = os.urandom(32)
    serde = strict_serializer(key)
    inner = serde.serde
    assert inner.pickle_fallback is False
    assert not inner._allowed_msgpack_modules  # only the built-in safe types
    value = {"a": [1, "two", None, True]}
    typ, blob = serde.dumps_typed(value)
    assert typ.endswith("+aesgcm") and b"two" not in blob
    assert serde.loads_typed((typ, blob)) == value
    # Unencrypted data is refused.
    plain = JsonPlusSerializer().dumps_typed(value)
    try:
        serde.loads_typed(plain)
    except ValueError:
        pass
    else:
        raise AssertionError("unencrypted checkpoint data was read")
    # Tampered ciphertext is refused.
    try:
        serde.loads_typed((typ, blob[:-1] + bytes([blob[-1] ^ 1])))
    except InvalidTag:
        pass
    else:
        raise AssertionError("tampered checkpoint data was read")
    # A non-allowlisted type, even correctly encrypted, isn't constructed:
    # the permissive default would run its code; strict returns plain data.
    built = GADGETS_BUILT
    permissive = JsonPlusSerializer(allowed_msgpack_modules=True)
    gtyp, gdata = permissive.dumps_typed(Gadget())
    built.clear()
    assert isinstance(permissive.loads_typed((gtyp, gdata)), Gadget) and built == [1]
    built.clear()
    ciphername, ct = AesGcmCipher(key).encrypt(gdata)
    loaded = serde.loads_typed((f"{gtyp}+{ciphername}", ct))
    assert not isinstance(loaded, Gadget) and built == [], (loaded, built)


def test_master_key_persists_and_is_private():
    directory = tempfile.mkdtemp()
    k1, k2 = load_master_key(directory), load_master_key(directory)
    assert k1 == k2 and len(k1) == 32
    assert check_private(os.path.join(directory, MASTER_KEY_FILE)) == []
    assert derive_key(k1, "approval-service") != derive_key(k1, "checkpoint-aes-gcm")


def test_pending_approval_survives_restart_and_executes_once():
    store, thread, marker, action_id = paused_run()
    assert thread_rows(store, thread) > 0  # the pause is on disk
    reviewer = Worker("review", store, thread, marker, "--decision", "approve")
    recovered, reviewed = reviewer.events_until_exit()
    assert recovered["found"] and recovered["action_id"] == action_id
    assert recovered["payload_matches"] is True and recovered["sent_before"] == 0
    assert reviewed["sent"] == 1 and reviewed["approval"] == "approved"
    assert reviewed["halted"] is False and reviewed["ledger"] == "executed"
    assert thread_rows(store, thread) == 0  # completed thread purged
    again = Worker("resume_again", store, thread, marker).events_until_exit()[0]
    assert again["helper"] == "no_pending_approval" and again["sent"] == 0, again
    executions = [e["execution"]["outcome"] for e in approval_events(store)
                  if e["event_type"] == "execution"]
    assert executions == ["executed"], executions


def test_rejection_still_prevents_transmission_after_restart():
    store, thread, marker, action_id = paused_run()
    reviewer = Worker("review", store, thread, marker, "--decision", "reject")
    recovered, reviewed = reviewer.events_until_exit()
    assert recovered["found"] and recovered["action_id"] == action_id
    assert reviewed["sent"] == 0 and reviewed["approval"] == "rejected"
    assert reviewed["halted"] is True and reviewed["ledger"] is None
    again = Worker("resume_again", store, thread, marker).events_until_exit()[0]
    assert again["sent"] == 0 and again["helper"] == "no_pending_approval", again


def test_crash_after_send_is_not_repeated_by_a_later_process():
    store, thread, marker, action_id = paused_run()
    crashing = Worker("review", store, thread, marker, "--decision", "approve", "--crash-after-send")
    events = crashing.events_until_exit()
    assert crashing.proc.returncode == 3
    assert events[-1]["event"] == "crashing" and events[-1]["sent"] == 1
    # The answer never reached a checkpoint, so the review is still pending.
    # Approving again in a new process must not send a second time.
    recovered, reviewed = Worker("review", store, thread, marker, "--decision", "approve").events_until_exit()
    assert recovered["found"] and recovered["action_id"] == action_id
    assert reviewed["sent"] == 0 and reviewed["ledger"] == "executing"
    outcomes = [e["execution"]["outcome"] for e in approval_events(store) if e["event_type"] == "execution"]
    assert outcomes == ["duplicate_prevented"], outcomes


def test_checkpoint_database_holds_no_raw_content():
    store, thread, marker, _ = paused_run()
    raw = b""
    for name in os.listdir(store):
        if name.startswith(CHECKPOINT_DB):
            with open(os.path.join(store, name), "rb") as f:
                raw += f.read()
    docs = get_mcp_manager().call_tool("search_documents", {"query": "e", "domain": "hr"})
    secrets_to_find = [marker, TASK, "jane.doe@example.com", h.analysis(False)["analysis"]]
    secrets_to_find += [d["content"] for d in docs]
    if os.environ.get("GOOGLE_API_KEY"):
        secrets_to_find.append(os.environ["GOOGLE_API_KEY"])
    for s in secrets_to_find:
        assert s.encode() not in raw, s[:40]
    # Decrypted, the paused state holds references, not the documents.
    opened = DevApprovalStore(store)
    try:
        state = opened.checkpointer.get_tuple(
            {"configurable": {"thread_id": thread}}).checkpoint["channel_values"]
        assert state["analysis"] is None
        assert state["retrieved_documents"] and all(
            set(d) == {"ref_id", "source", "sensitivity"} for d in state["retrieved_documents"])
        assert state["final_output"] == marker  # the pending payload, needed for review
    finally:
        opened.close()


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
