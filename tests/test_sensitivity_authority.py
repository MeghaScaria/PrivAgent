"""
Tests that provenance, not agent self-report, is the authoritative
sensitivity signal (shadow mode), that unknown provenance and
unassessed user input are never treated as safe, and that logs hold
references and metadata rather than raw content.

Run with pytest, or directly: python tests/test_sensitivity_authority.py
"""
import hashlib
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.test_handoff_instrumentation as h
from agents import tools
from governance.audit_logger import AuditLogger
from governance.provenance import ProvenanceRegistry, fingerprint, item_sensitivity
from governance.sensitivity import assess_text, authoritative_label
from governance.trajectory_monitor import TrajectoryMonitor

h.SCENARIOS.update({
    "benign_send": dict(plan=h.plan(["research"]), analysis=h.analysis(False),
                        writer=h.writer(True)),
    "benign_send_overdeclared": dict(plan=h.plan(["research"]), analysis=h.analysis(True),
                                     writer=h.writer(True)),
})


def run(scenario, task=None, **kwargs):
    """Like the instrumentation tests' run(), optionally with a custom task text."""
    logger = AuditLogger(os.path.join(tempfile.mkdtemp(), "audit_log.jsonl"))
    monitor = TrajectoryMonitor(run_id=f"sens_{scenario}", audit_logger=logger, **kwargs)
    llm = h.FakeLLM(**h.SCENARIOS[scenario])
    app = h.build_graph(monitor, llm=llm)
    state = app.invoke(h.new_state(task=task or f"Task for {scenario}", run_id=monitor.run_id))
    return state, monitor, llm, logger


def send_decision(monitor):
    return [d for d in monitor.decisions if d.action["tool_name"] == "send_result"][0]


def test_misreported_sensitivity_is_flagged_and_shadow_scored():
    _, monitor, _, logger = run("sensitive_send_misreported")
    d = send_decision(monitor)
    s = d.sensitivity
    assert s["declared"] == 0 and s["provenance"]["value"] == 1
    assert s["authoritative"] == 1 and s["enforced"] == 0 and s["mode"] == "shadow"
    assert s["provenance"]["sensitive_refs"]
    assert "declared_lower_than_provenance" in d.flags
    # Enforced decision is unchanged (the model saw 0); the shadow
    # decision shows what the authoritative label gives.
    assert d.action["data_sensitivity"] == 0
    assert d.shadow["data_sensitivity"] == 1
    assert d.shadow["risk_score"] > d.risk_score
    with open(logger.log_file) as f:
        logged = [json.loads(l) for l in f if '"send_result"' in l][0]
    assert logged["sensitivity"]["authoritative"] == 1
    assert "declared_lower_than_provenance" in logged["flags"]
    assert logged["shadow"]["data_sensitivity"] == 1


def test_enforce_mode_scores_the_authoritative_label():
    _, shadow_monitor, _, _ = run("sensitive_send_misreported")
    _, monitor, _, _ = run("sensitive_send_misreported", sensitivity_mode="enforce")
    d = send_decision(monitor)
    assert d.action["data_sensitivity"] == 1 and d.sensitivity["enforced"] == 1
    assert d.shadow is None
    # Shadow risk scores are stored rounded to 4 places.
    assert abs(d.risk_score - send_decision(shadow_monitor).shadow["risk_score"]) < 1e-4


def test_enforce_mode_requires_provenance():
    try:
        TrajectoryMonitor(handoff_mode="off", sensitivity_mode="enforce",
                          audit_logger=AuditLogger(os.path.join(tempfile.mkdtemp(), "a.jsonl")))
    except ValueError:
        return
    raise AssertionError("enforce mode accepted without provenance")


def test_unknown_provenance_is_treated_as_sensitive():
    monitor = TrajectoryMonitor(audit_logger=AuditLogger(os.path.join(tempfile.mkdtemp(), "a.jsonl")))
    result = tools.send_result(monitor, "writer", "payload with no recorded inputs",
                               contains_sensitive_data=False)
    s = result["decision"]["sensitivity"]
    assert s["provenance"] == {"value": None, "basis": "no_recorded_inputs", "refs": []}
    assert s["authoritative"] == 1
    assert "provenance_unknown_treated_as_sensitive" in result["decision"]["flags"]
    assert "declared_lower_than_provenance" in result["decision"]["flags"]


def test_declaration_can_only_raise_sensitivity():
    _, monitor, _, _ = run("benign_send_overdeclared")
    d = send_decision(monitor)
    assert d.sensitivity["provenance"]["value"] == 0 and d.sensitivity["declared"] == 1
    assert d.sensitivity["authoritative"] == 1
    assert d.sensitivity["authoritative_basis"] == "agent_declaration_stricter_than_provenance"
    assert "declared_higher_than_provenance" in d.flags
    label, flags = authoritative_label({"value": 1, "basis": "x"}, declared=0)
    assert label["value"] == 1 and flags == ["declared_lower_than_provenance"]


def test_agreement_raises_no_flags():
    _, monitor, _, _ = run("benign_send")
    d = send_decision(monitor)
    assert d.sensitivity["provenance"]["value"] == 0 and d.sensitivity["authoritative"] == 0
    assert d.flags == [] and d.shadow is None
    for ev in monitor.handoffs:
        assert ev["flags"] == [], ev


def test_user_input_is_assessed():
    cases = {
        "Email the report to jane.doe@example.com": ["email"],
        "Check SSN 123-45-6789": ["us_ssn"],
        "Pay into GB29NWBK60161331926819": ["iban"],
        "Card 4111 1111 1111 1111 was charged": ["payment_card"],
        "Call +1 415-555-0134 tomorrow": ["phone"],
    }
    for text, expected in cases.items():
        label = assess_text(text, "user_input")
        assert label["value"] == 1 and label["basis"] == "user_input_pii_detected", (text, label)
        assert set(expected) <= set(label["detectors"]), (text, label)
        assert all(part not in json.dumps(label) for part in text.split() if len(part) > 6)
    clean = assess_text("Summarise recent public research on market trends", "user_input")
    assert clean["value"] == 0 and clean["basis"] == "user_input_no_pii_detected"
    assert clean["assessor"]
    assert assess_text(None, "user_input")["value"] is None
    # A number that fails the card checksum isn't reported as a card.
    assert "payment_card" not in assess_text("Order 4111 1111 1111 1112", "x").get("detectors", [])


def test_sensitive_user_input_propagates():
    _, monitor, _, _ = run("benign_send", task="Send the summary to jane.doe@example.com")
    task_ref = monitor.handoffs[0]["payload"]["task"][0]
    assert monitor.provenance.refs[task_ref]["sensitivity"]["value"] == 1
    d = send_decision(monitor)
    assert d.sensitivity["provenance"]["value"] == 1
    assert "declared_lower_than_provenance" in d.flags


def test_payload_echo_tools_are_not_labelled_safe():
    for tool in ("send_result", "get_transmission_log"):
        assert item_sensitivity(tool, {}, {"payload_preview": "x"})["value"] is None


def test_fingerprints_are_keyed_and_private():
    a, b = ProvenanceRegistry(), ProvenanceRegistry()
    item = {"id": 1, "salary": 85000}
    assert a._fp(item) == a._fp(item) and a._fp(item) != b._fp(item)
    ref = a.register_root("task", "user", {"value": 0, "basis": "x"}, content=item)
    assert "fingerprint" in a.refs[ref] and "fingerprint" not in a.snapshot(ref)


def test_logs_hold_no_raw_content_or_fingerprints():
    task = "Email the HR summary to jane.doe@example.com"
    state, monitor, _, logger = run("sensitive_send_misreported", task=task)
    with open(logger.log_file) as f:
        audit = f.read()
    with open(logger.handoff_log_file) as f:
        handoff = f.read()
    text = audit + handoff
    assert '"fingerprint"' not in text
    for ref in monitor.provenance.refs.values():
        if ref.get("fingerprint"):
            assert ref["fingerprint"] not in text
    raw = [task, state["analysis"], state["final_output"], "jane.doe@example.com"]
    for doc in state["retrieved_documents"]:
        raw.append(doc["content"])
        raw += re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", doc["content"])
    for rec in state["retrieved_records"]:
        raw += [str(rec["account"]), rec["vendor"]]
    for value in raw:
        assert value not in text, value
    # Plain (unkeyed) content hashes, as the previous version logged, are absent too.
    for item in state["retrieved_documents"] + state["retrieved_records"]:
        plain = hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest()
        assert plain[:16] not in text
    # References and metadata are still there.
    assert "document_server:search_documents:doc:hr_" in handoff
    assert "database_server:query_database:transactions#" in handoff


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
