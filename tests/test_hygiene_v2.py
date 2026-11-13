"""
V2_PLAN.md WP3: hash-chained logs, HKDF key separation, RESTRICTED
semantics, send binding. Everything is v2-only; v1 defaults are checked
to be unchanged.

No MCP servers are started: the send-binding tests replace the MCP
manager with a recording fake, so "nothing was sent" is exact. All files
go to temporary directories, never logs/ or runtime/.

    python tests/test_hygiene_v2.py
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import approval_flow, tools  # noqa: E402
from governance import checkpoint_store as cs  # noqa: E402
from governance.approval import ApprovalService, ExecutionLedger  # noqa: E402
from governance.audit_logger import (  # noqa: E402
    LOG_DIR, AuditLogger, ChainedAuditLogger, load_chain_head, verify_chain,
)
from governance.trajectory_monitor import TrajectoryMonitor  # noqa: E402


def _tmp(*parts):
    return os.path.join(tempfile.mkdtemp(), *parts)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# -- 1. hash chain ----------------------------------------------------------

def _chained_log(n=6):
    log = _tmp("v2", "audit_log.jsonl")
    head_db = _tmp("ledger.sqlite")
    logger = ChainedAuditLogger(log, head_db=head_db)
    for i in range(n):
        logger.record(run_id="r", agent_role="retriever", tool_name="search_web", risk_score=0.1 * i,
                      decision="AUTONOMOUS", source="ml_model", reason=f"step {i}",
                      trajectory_length=i, event_id=f"r:t{i}", seq=i)
    return logger, log, head_db


def _lines(path):
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def _write(path, lines):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)


def test_intact_chain_verifies_and_head_is_anchored():
    logger, log, head_db = _chained_log()
    assert verify_chain(log) == (True, None)
    assert verify_chain(log, head_db) == (True, None)
    count, head = load_chain_head(head_db, log)
    assert count == 6 and head == json.loads(_lines(log)[-1])["entry_hash"]
    # every v1 field is still there, plus the two chain fields
    first = json.loads(_lines(log)[0])
    assert {"run_id", "decision", "source", "reason", "prev_hash", "entry_hash"} <= set(first)
    assert first["prev_hash"] == "0" * 64


def test_edited_line_detected():
    _, log, head_db = _chained_log()
    lines = _lines(log)
    entry = json.loads(lines[2])
    entry["decision"] = "BLOCKED"
    lines[2] = json.dumps(entry) + "\n"
    _write(log, lines)
    assert verify_chain(log, head_db) == (False, 3)
    assert verify_chain(log) == (False, 3)


def test_deleted_line_detected():
    _, log, head_db = _chained_log()
    lines = _lines(log)
    del lines[3]
    _write(log, lines)
    assert verify_chain(log, head_db) == (False, 4)


def test_reordered_lines_detected():
    _, log, head_db = _chained_log()
    lines = _lines(log)
    lines[1], lines[2] = lines[2], lines[1]
    _write(log, lines)
    assert verify_chain(log, head_db) == (False, 2)


def test_truncated_tail_detected_against_anchor():
    _, log, head_db = _chained_log()
    _write(log, _lines(log)[:4])                 # two whole lines cut off
    assert verify_chain(log, head_db) == (False, 5)
    # Documented limitation: without the anchor a clean tail cut is a valid chain.
    assert verify_chain(log) == (True, None)


def test_partly_written_last_line_detected():
    _, log, head_db = _chained_log()
    lines = _lines(log)
    lines[-1] = lines[-1][: len(lines[-1]) // 2]  # cut mid-line, no newline
    _write(log, lines)
    assert verify_chain(log) == (False, 6)


def test_missing_anchor_is_reported():
    _, log, _ = _chained_log()
    assert verify_chain(log, _tmp("empty_ledger.sqlite")) == (False, None)


def test_chain_continues_across_logger_instances_and_files():
    logger, log, head_db = _chained_log(3)
    logger.record_approval({"run_id": "r", "event_type": "gate"})
    again = ChainedAuditLogger(log, head_db=head_db)
    again.record(run_id="r", agent_role="writer", tool_name="send_result", risk_score=0.9,
                 decision="BLOCKED", source="ml_model", reason="x", trajectory_length=3)
    assert all(v == (True, None) for v in again.verify().values()), again.verify()


def test_chained_logger_refuses_v1_log_directory():
    try:
        ChainedAuditLogger(os.path.join(LOG_DIR, "audit_log.jsonl"), head_db=None)
    except ValueError:
        return
    raise AssertionError("ChainedAuditLogger accepted logs/audit_log.jsonl")


def test_v1_audit_logger_lines_unchanged():
    log = _tmp("audit_log.jsonl")
    AuditLogger(log).record(run_id="r", agent_role="a", tool_name="t", risk_score=0.5,
                            decision="AUTONOMOUS", source="ml_model", reason="x",
                            trajectory_length=0)
    line = json.loads(_lines(log)[0])
    assert "prev_hash" not in line and "entry_hash" not in line
    assert _lines(log)[0] == json.dumps(line) + "\n"     # plain json.dumps, as in v1


# -- 2. HKDF key separation ---------------------------------------------------

def _v1_store():
    d = _tmp("approvals")
    store = cs.DevApprovalStore(d)
    store.close()
    return d


def test_hkdf_keys_are_distinct_and_never_the_master():
    master = os.urandom(32)
    sign = cs.hkdf_key(master, cs.APPROVAL_SIGN_INFO)
    enc = cs.hkdf_key(master, cs.CHECKPOINT_ENC_INFO)
    assert len({master, sign, enc, cs.derive_key(master, "approval-service"),
                cs.derive_key(master, "checkpoint-aes-gcm")}) == 5
    assert sign == cs.hkdf_key(master, cs.APPROVAL_SIGN_INFO)       # deterministic
    assert cs.APPROVAL_SIGN_INFO == b"privagent/approval-sign/v2"
    assert cs.CHECKPOINT_ENC_INFO == b"privagent/checkpoint-enc/v2"


def test_v2_store_uses_new_files_and_leaves_v1_files_untouched():
    v1_dir = _v1_store()
    before = {f: _sha(os.path.join(v1_dir, f)) for f in sorted(os.listdir(v1_dir))}
    v2_dir = os.path.join(v1_dir, "v2")
    store = cs.DevApprovalStore(v2_dir, governance_version="v2", master_key_dir=v1_dir)
    try:
        assert store.checkpoint_path == os.path.join(v2_dir, "checkpoints.sqlite")
        assert store.ledger_path == os.path.join(v2_dir, "ledger.sqlite")
        assert store.service.binding == "v2"
        assert not os.path.exists(os.path.join(v2_dir, "master.key"))
    finally:
        store.close()
    after = {f: _sha(os.path.join(v1_dir, f)) for f in sorted(os.listdir(v1_dir))
             if os.path.isfile(os.path.join(v1_dir, f))}
    assert after == before


def test_v2_store_never_creates_a_master_key():
    empty = _tmp("no_key")
    os.makedirs(empty)
    try:
        cs.DevApprovalStore(os.path.join(empty, "v2"), governance_version="v2", master_key_dir=empty)
    except FileNotFoundError:
        assert not os.path.exists(os.path.join(empty, "master.key"))
        return
    raise AssertionError("v2 store started without a master key")


def test_v1_and_v2_checkpoint_ciphers_do_not_interoperate():
    master = os.urandom(32)
    v1 = cs.AesGcmCipher(cs.derive_key(master, "checkpoint-aes-gcm"))
    v2 = cs.AesGcmCipher(cs.hkdf_key(master, cs.CHECKPOINT_ENC_INFO), cs._AAD_V2)
    name, blob = v1.encrypt(b"state")
    try:
        v2.decrypt(name, blob)
    except Exception:  # noqa: BLE001  (cryptography's InvalidTag)
        pass
    else:
        raise AssertionError("v2 decrypted a v1 checkpoint blob")
    assert v2.decrypt(*v2.encrypt(b"state")) == b"state"


def test_default_v2_locations():
    assert cs.DEFAULT_DIR_V2 == os.path.join(cs.DEFAULT_DIR, "v2")


# -- 3. RESTRICTED semantics --------------------------------------------------

def _monitor(version, scores):
    """A monitor whose risk model returns the given scores in order
    (0.3 -> RESTRICTED, 0.05 -> AUTONOMOUS with thresholds 0.22/0.50/0.85)."""
    m = TrajectoryMonitor(run_id="r", governance_version=version,
                          audit_logger=AuditLogger(_tmp("a.jsonl")))
    it = iter(scores)
    m.risk_engine.compute_risk = lambda *a, **k: next(it)
    return m


WEB_RESULT = [{"url": "https://example.org/a", "title": "a", "snippet": "s"}]


def test_restricted_external_escalates_in_v2_only():
    d1 = _monitor("v1", [0.3]).evaluate("writer", "send_result", "transmit", 0, "external")
    d2 = _monitor("v2", [0.3]).evaluate("writer", "send_result", "transmit", 0, "external")
    assert d1.decision == "RESTRICTED" and d1.allowed
    assert d2.decision == "HUMAN_APPROVAL" and not d2.allowed and d2.source == "restricted_rule"
    assert d2.combination["restricted_escalation"] == "restricted_external"
    assert d2.combination["v1_decision"] == "RESTRICTED"


def test_restricted_internal_runs_and_lineage_escalates_later_send():
    def run(read_score, version="v2"):
        m = _monitor(version, [read_score, 0.05])
        read = m.evaluate("retriever", "search_web", "read", 0, "internal")
        assert read.allowed
        refs = m.register_tool_result(read, "search_web", {"query": "q"}, WEB_RESULT)
        m.record_handoff("handoff", "retriever", "writer", {"web_results": refs})
        return read, m.evaluate("writer", "send_result", "transmit", 0, "external")

    read, send = run(0.3)
    assert read.decision == "RESTRICTED"
    assert send.decision == "HUMAN_APPROVAL" and send.source == "restricted_rule"
    assert send.combination["restricted_escalation"] == "restricted_lineage"
    assert send.combination["restricted_lineage_refs"]
    _, control = run(0.05)                 # same flow, nothing RESTRICTED
    assert control.decision == "AUTONOMOUS" and control.allowed
    _, v1_send = run(0.3, version="v1")    # v1: RESTRICTED has no effect
    assert v1_send.decision == "AUTONOMOUS" and v1_send.allowed


def test_restricted_semantics_never_relax():
    for score, expected in ((0.6, "HUMAN_APPROVAL"), (0.95, "BLOCKED")):
        d = _monitor("v2", [score]).evaluate("writer", "send_result", "transmit", 0, "external")
        assert d.decision == expected, (score, d.decision)


# -- 4. send binding ----------------------------------------------------------

class _FakeMCP:
    def __init__(self):
        self.calls = []

    def call_tool(self, tool, args, timeout=30):
        self.calls.append((tool, dict(args)))
        return {"status": "sent", "destination": args.get("destination")}


def _approved_send(destination="partner-A"):
    monitor = _monitor("v2", [0.6])                    # HUMAN_APPROVAL
    decision = monitor.evaluate("writer", "send_result", "transmit", 0, "external")
    assert decision.decision == "HUMAN_APPROVAL"
    service = ApprovalService(ExecutionLedger(_tmp("ledger.sqlite")), binding="v2")
    payload = "quarterly summary"
    pending = service.gate(monitor, decision, payload, destination)
    approval = service.resolve(monitor, pending, {
        "action_id": pending["action_id"], "action_digest": pending["action_digest"],
        "decision": "approve", "reviewer": "tester"}, payload)
    assert service.authorize(pending, approval, payload) == (True, "approved_by_reviewer")
    return monitor, decision, service, pending, approval, payload


def _with_fake_mcp(fn):
    fake, original = _FakeMCP(), tools.get_mcp_manager
    tools.get_mcp_manager = lambda: fake
    try:
        fn(fake)
    finally:
        tools.get_mcp_manager = original
    return fake


def test_v2_pending_action_binds_tool_destination_server_and_payload():
    _, _, service, pending, _, payload = _approved_send()
    assert pending["binding"] == "v2"
    assert pending["server"] == {"server": "external",
                                 "script": "mcp_servers/external_server/server.py"}
    ok = service.verify_binding(pending, "send_result", "partner-A", pending["server"], payload)
    assert ok == (True, "binding_verified")
    for changed in (("get_transmission_log", "partner-A", pending["server"], payload),
                    ("send_result", "partner-B", pending["server"], payload),
                    ("send_result", "partner-A", {"server": "web", "script": "x"}, payload),
                    ("send_result", "partner-A", pending["server"], payload + "!")):
        assert service.verify_binding(pending, *changed)[0] is False, changed


def test_execute_send_to_unapproved_destination_is_refused():
    monitor, decision, service, pending, _, payload = _approved_send("partner-A")

    def attempt(fake):
        try:
            tools.execute_send(monitor, decision, payload, "partner-B", binding=(service, pending))
        except tools.SendBindingError:
            return
        raise AssertionError("send to an unapproved destination was not refused")
    fake = _with_fake_mcp(attempt)
    assert fake.calls == []                             # nothing reached the MCP layer

    fake = _with_fake_mcp(lambda f: tools.execute_send(
        monitor, decision, payload, "partner-A", binding=(service, pending)))
    assert fake.calls == [("send_result", {"payload": payload, "destination": "partner-A"})]


def test_approval_flow_refuses_destination_switch_before_ledger_claim():
    """Approve a send to A; the request in state is then changed to B. The
    execute node refuses, sends nothing and leaves the ledger unclaimed."""
    monitor, decision, service, pending, approval, payload = _approved_send("partner-A")

    class _Tracker:
        def after_writer(self, state):
            pass
    nodes = approval_flow.make_nodes(monitor, service, _Tracker(), lambda f, *a: None)

    def state(dest):
        return {"pending_action": pending, "approval": approval, "final_output": payload,
                "transmission_request": {"requested": True, "destination": dest},
                "governance_events": [{"blocked": True}], "messages": [], "trajectory": []}

    s = state("partner-B")
    fake = _with_fake_mcp(lambda f: nodes["transmission_execute"](s))
    assert fake.calls == []
    assert s["task_halted"] and "binding_mismatch" in s["halt_reason"]
    assert service.ledger.status(pending["action_id"]) is None

    s = state("partner-A")
    fake = _with_fake_mcp(lambda f: nodes["transmission_execute"](s))
    assert len(fake.calls) == 1 and fake.calls[0][1]["destination"] == "partner-A"
    assert service.ledger.status(pending["action_id"]) == "executed"


def test_v1_binding_unchanged():
    monitor = _monitor("v1", [0.6])
    decision = monitor.evaluate("writer", "send_result", "transmit", 0, "external")
    service = ApprovalService(ExecutionLedger(_tmp("ledger.sqlite")))
    pending = service.gate(monitor, decision, "p", "external")
    assert service.binding == "v1"
    assert not {"server", "binding", "binding_digest"} & set(pending)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
