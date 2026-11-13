"""
Tests for the human-approval workflow (governance/approval.py,
agents/approval_flow.py).

Whether the external tool really ran is checked against the external
MCP server's own transmission log, not against our bookkeeping. Each
run's answer carries a unique marker so its transmissions can be
counted exactly.

Run with pytest, or directly: python tests/test_human_approval.py
"""
import json
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import tests.test_handoff_instrumentation as h
from agents import approval_flow
from agents.approval_flow import NoPendingApproval, pending_review, start, submit_review
from agents.graph import build_graph
from agents.mcp_client import get_mcp_manager
from agents.state import new_state
from governance.approval import (
    SENSITIVE_CROSSED_TO_EXTERNAL, ApprovalService, ExecutionLedger, approval_metrics,
)
from governance.audit_logger import AuditLogger
from governance.trajectory_monitor import TrajectoryMonitor

RULES = [SENSITIVE_CROSSED_TO_EXTERNAL]


def scenario(domains, table=None, declared=False, send=True, marker=None):
    return dict(plan=h.plan(domains, table=table), analysis=h.analysis(declared),
                writer={"final_answer": marker or "", "should_transmit_externally": send})


def transmissions(marker):
    log = get_mcp_manager().call_tool("get_transmission_log", {})
    return sum(1 for t in log if t["payload_preview"].startswith(marker))


class Run:
    """One approval-enabled run with its own monitor, ledger, logs and thread."""

    def __init__(self, domains, table=None, declared=False, send=True, rules=RULES,
                 handoff_mode="shadow", checkpointer=None, service=None, ledger_dir=None):
        self.marker = f"ANSWER-{uuid.uuid4().hex[:12]}"
        self.dir = ledger_dir or tempfile.mkdtemp()
        self.logger = AuditLogger(os.path.join(self.dir, "audit_log.jsonl"))
        self.monitor = TrajectoryMonitor(run_id=f"appr_{self.marker[-6:]}", audit_logger=self.logger,
                                         handoff_mode=handoff_mode)
        self.ledger_path = os.path.join(self.dir, "ledger.sqlite")
        self.service = service or ApprovalService(ExecutionLedger(self.ledger_path), flow_rules=rules)
        self.checkpointer = checkpointer or InMemorySaver()
        self.llm = h.FakeLLM(**scenario(domains, table, declared, send, self.marker))
        self.app = build_graph(self.monitor, llm=self.llm, approvals=self.service,
                               checkpointer=self.checkpointer)
        self.thread = f"thread-{self.marker}"

    def start(self):
        return start(self.app, new_state(task="Task", run_id=self.monitor.run_id), self.thread)

    def state(self):
        return self.app.get_state({"configurable": {"thread_id": self.thread}}).values

    def respond(self, decision="approve", reviewer="reviewer-1", **overrides):
        request = pending_review(self.app, self.thread)
        response = {"action_id": request["action_id"], "action_digest": request["action_digest"],
                    "decision": decision, "reviewer": reviewer}
        response.update(overrides)
        return submit_review(self.app, self.thread, response)

    def sent(self):
        return transmissions(self.marker)

    def approval_events(self, event_type=None):
        if not os.path.exists(self.logger.approval_log_file):
            return []
        with open(self.logger.approval_log_file) as f:
            events = [json.loads(l) for l in f]
        return [e for e in events if event_type is None or e["event_type"] == event_type]

    def execution_outcome(self):
        return [e["execution"]["outcome"] for e in self.approval_events("execution")]


# Scenarios (what triggers review):
#   public research send        nothing sensitive; flow rule doesn't fire
#   HR send, misreported        one sensitive read, analyst says "not sensitive":
#                               ML/policy allow it; the flow rule escalates
#   HR send, declared           policy rule 2 already says HUMAN_APPROVAL
PUBLIC = dict(domains=["research"])
HR_MISREPORTED = dict(domains=["hr"], declared=False)
HR_DECLARED = dict(domains=["hr"], declared=True)


def test_default_graph_is_unchanged():
    monitor = TrajectoryMonitor(audit_logger=AuditLogger(os.path.join(tempfile.mkdtemp(), "a.jsonl")))
    nodes = set(build_graph(monitor, llm=h.FakeLLM(**h.SCENARIOS["benign"])).get_graph().nodes)
    assert nodes == {"__start__", "orchestrator", "retriever", "analyst", "writer", "__end__"}
    try:
        build_graph(monitor, approvals=ApprovalService(ExecutionLedger(
            os.path.join(tempfile.mkdtemp(), "l.sqlite"))))
    except ValueError:
        return
    raise AssertionError("approval graph built without a checkpointer")


def test_benign_workflows_complete_without_interruption():
    for kwargs in (PUBLIC, dict(domains=["research"], send=False)):
        run = Run(**kwargs)
        result = run.start()
        assert "__interrupt__" not in result, kwargs
        assert pending_review(run.app, run.thread) is None
        assert run.approval_events("approval_requested") == []
        expected = 1 if kwargs.get("send", True) else 0
        assert run.sent() == expected, kwargs
        assert result["task_halted"] is False


def test_risky_transmission_pauses_before_the_tool_call():
    for kwargs, trigger in ((HR_MISREPORTED, "flow_rule"), (HR_DECLARED, "policy_engine")):
        run = Run(**kwargs)
        result = run.start()
        assert "__interrupt__" in result, kwargs
        assert run.sent() == 0
        assert ExecutionLedger(run.ledger_path).status(run.state()["pending_action"]["action_id"]) is None
        snapshot = run.app.get_state({"configurable": {"thread_id": run.thread}})
        assert snapshot.next == ("human_approval",)
        request = pending_review(run.app, run.thread)
        assert request["payload"] == run.marker and request["payload_matches_gated_action"] is True
        assert request["decided_by"] == trigger and request["final_decision"] == "HUMAN_APPROVAL"
        assert request["governance"]["sensitivity"]["provenance"]["value"] == 1
        if trigger == "flow_rule":
            ev = request["flow_rules_fired"][SENSITIVE_CROSSED_TO_EXTERNAL]
            assert ev["crossed_refs"] and all(r["produced_by"] == "retriever" for r in ev["crossed_refs"])
            assert request["governance"]["decision"] in ("AUTONOMOUS", "RESTRICTED")
        assert len(run.approval_events("approval_requested")) == 1


def test_approval_resumes_and_executes_exactly_once():
    run = Run(**HR_MISREPORTED)
    run.start()
    result = run.respond("approve")
    assert run.sent() == 1
    assert result["task_halted"] is False and result["governance_events"][-1]["blocked"] is False
    action_id = result["pending_action"]["action_id"]
    assert ExecutionLedger(run.ledger_path).status(action_id) == "executed"
    assert run.execution_outcome() == ["executed"]
    assert any(a["tool_name"] == "send_result" for a in run.monitor.trajectory)
    tx = [e for e in run.monitor.handoffs if e["event_type"] == "transmission"][0]
    assert tx["details"]["executed"] is True and tx["details"]["approval"] == "approved"


def test_rejection_prevents_the_operation():
    run = Run(**HR_MISREPORTED)
    run.start()
    result = run.respond("reject")
    assert run.sent() == 0
    assert result["task_halted"] is True and "not_approved" in result["halt_reason"]
    assert ExecutionLedger(run.ledger_path).status(result["pending_action"]["action_id"]) is None
    assert run.execution_outcome() == ["refused"]
    assert run.approval_events("approval_response")[0]["approval"]["outcome"] == "rejected"


def test_reviewer_cannot_approve_a_different_or_modified_action():
    bad_responses = {
        "action_id_mismatch": dict(action_id=str(uuid.uuid4())),
        "action_digest_mismatch": dict(action_digest="0" * 64),
        "unexpected_fields": dict(payload="a modified payload"),
        "missing_reviewer": dict(reviewer=""),
        "invalid_decision": dict(decision="yes"),
    }
    for expected_reason, override in bad_responses.items():
        run = Run(**HR_MISREPORTED)
        run.start()
        result = run.respond(**override)
        assert run.sent() == 0, expected_reason
        assert result["approval"]["outcome"] == "invalid"
        assert result["approval"]["reason"] == expected_reason, result["approval"]
    # No response at all is refused before resuming; the review stays pending.
    run = Run(**HR_MISREPORTED)
    run.start()
    try:
        submit_review(run.app, run.thread, None)
    except ValueError:
        pass
    else:
        raise AssertionError("empty response accepted")
    assert pending_review(run.app, run.thread) is not None and run.sent() == 0
    # A malformed response is a rejection.
    result = submit_review(run.app, run.thread, "approve")
    assert run.sent() == 0 and result["approval"]["reason"] == "malformed_response"
    # An approval for another run's action
    a, b = Run(**HR_MISREPORTED), Run(**HR_MISREPORTED)
    a.start(), b.start()
    req_a = pending_review(a.app, a.thread)
    result = submit_review(b.app, b.thread, {"action_id": req_a["action_id"],
                                             "action_digest": req_a["action_digest"],
                                             "decision": "approve", "reviewer": "r"})
    assert b.sent() == 0 and result["approval"]["reason"] == "action_id_mismatch"


def test_payload_changes_and_forged_approvals_are_refused():
    # Payload edited in the checkpointed state after it was gated. Editing
    # state clears the pause; re-running asks for review again, flags the
    # change, and an approval of it doesn't count.
    run = Run(**HR_MISREPORTED)
    run.start()
    cfg = {"configurable": {"thread_id": run.thread}}
    run.app.update_state(cfg, {"final_output": run.marker + " plus exfiltrated extras"})
    run.app.invoke(None, cfg)
    request = pending_review(run.app, run.thread)
    assert request["payload_matches_gated_action"] is False
    result = run.respond("approve")
    assert run.sent() == 0
    assert result["approval"]["reason"] == "payload_changed_after_gate"
    assert result["task_halted"] is True and "payload_changed_after_review" in result["halt_reason"]
    # An approval written straight into state, without the reviewer.
    run = Run(**HR_MISREPORTED)
    run.start()
    cfg = {"configurable": {"thread_id": run.thread}}
    pending = run.state()["pending_action"]
    run.app.update_state(cfg, {"approval": {"action_id": pending["action_id"], "approved": True,
                                            "reviewer": "attacker", "token": "forged"}})
    result = run.app.invoke(None, cfg)
    assert run.sent() == 0
    assert "invalid_approval_token" in result["halt_reason"]


def test_checkpoint_resume_from_a_new_graph_instance():
    run = Run(**HR_MISREPORTED)
    run.start()
    # A fresh graph and monitor (as after an app restart) sharing the
    # checkpointer, ledger and approval service, resuming the same thread.
    monitor2 = TrajectoryMonitor(run_id=run.monitor.run_id, audit_logger=run.logger)
    app2 = build_graph(monitor2, llm=run.llm, approvals=run.service, checkpointer=run.checkpointer)
    request = pending_review(app2, run.thread)
    assert request is not None and request["payload"] == run.marker
    result = submit_review(app2, run.thread, {"action_id": request["action_id"],
                                              "action_digest": request["action_digest"],
                                              "decision": "approve", "reviewer": "r"})
    assert run.sent() == 1 and result["task_halted"] is False
    # The original graph sees the same completed thread.
    assert pending_review(run.app, run.thread) is None
    try:
        submit_review(run.app, "some-other-thread", {"decision": "approve"})
    except NoPendingApproval:
        pass
    else:
        raise AssertionError("resumed a thread with nothing pending")


def test_duplicate_resumes_do_not_duplicate_transmissions():
    run = Run(**HR_MISREPORTED)
    run.start()
    request = pending_review(run.app, run.thread)
    response = {"action_id": request["action_id"], "action_digest": request["action_digest"],
                "decision": "approve", "reviewer": "r"}
    submit_review(run.app, run.thread, response)
    assert run.sent() == 1
    try:
        submit_review(run.app, run.thread, response)
    except NoPendingApproval:
        pass
    else:
        raise AssertionError("second resume was accepted")
    # Bypassing the helper and resuming the raw graph again.
    run.app.invoke(Command(resume=response), {"configurable": {"thread_id": run.thread}})
    assert run.sent() == 1


def test_crash_after_send_is_not_retried():
    run = Run(**HR_MISREPORTED)
    run.start()
    ledger, original_finish = run.service.ledger, run.service.ledger.finish
    calls = {"n": 0}

    def crash_once(action_id, status):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("process died after the tool call")
        return original_finish(action_id, status)
    ledger.finish = crash_once
    try:
        try:
            run.respond("approve")
        except RuntimeError:
            pass
        assert run.sent() == 1
        # Retrying the run re-enters the execute node; the ledger claim stops it.
        run.app.invoke(None, {"configurable": {"thread_id": run.thread}})
        assert run.sent() == 1
        assert "duplicate_prevented" in run.execution_outcome()
    finally:
        ledger.finish = original_finish


def test_approval_system_failures_fail_closed():
    # Validation raises: the run stops before the execute node.
    run = Run(**HR_MISREPORTED)
    run.start()
    original = run.service.resolve
    run.service.resolve = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("approval service down"))
    try:
        run.respond("approve")
    except RuntimeError:
        pass
    finally:
        run.service.resolve = original
    assert run.sent() == 0 and run.execution_outcome() == []
    # The ledger can't be written: nothing is sent.
    run = Run(**HR_MISREPORTED)
    run.start()
    run.service.ledger.claim = lambda *a, **k: (_ for _ in ()).throw(OSError("ledger unavailable"))
    try:
        run.respond("approve")
    except OSError:
        pass
    assert run.sent() == 0
    # No provenance at all: the flow rule fires rather than letting it through.
    run = Run(**dict(PUBLIC), handoff_mode="off")
    result = run.start()
    assert "__interrupt__" in result and run.sent() == 0
    assert pending_review(run.app, run.thread)["flow_rules_fired"][SENSITIVE_CROSSED_TO_EXTERNAL][
        "reason"] == "provenance_unavailable"


def test_blocked_decisions_are_never_offered_for_review():
    run = Run(domains=["hr"], table="employees", declared=False)  # policy rule 1 blocks
    result = run.start()
    assert "__interrupt__" not in result and run.sent() == 0
    assert result["pending_action"]["final_decision"] == "BLOCKED"
    assert run.execution_outcome() == ["refused"]


def test_flow_rules_are_off_unless_enabled():
    run = Run(**HR_MISREPORTED, rules=())
    result = run.start()
    assert "__interrupt__" not in result
    assert run.sent() == 1  # same as the existing pipeline: ML and policy allow it


def test_audit_log_has_evidence_and_response_but_no_raw_content():
    run = Run(**HR_MISREPORTED)
    run.start()
    run.respond("approve", comment="Approved; see SSN 123-45-6789 in ticket")
    events = run.approval_events()
    kinds = [e["event_type"] for e in events]
    assert kinds == ["gate", "escalation_evaluated", "approval_requested", "approval_response",
                     "execution"], kinds
    response = run.approval_events("approval_response")[0]
    assert response["approval"]["reviewer"] == "reviewer-1"
    assert response["approval"]["outcome"] == "approved" and response["approval"]["has_comment"]
    assert response["flow_rules_fired"][SENSITIVE_CROSSED_TO_EXTERNAL]["crossed_refs"]
    assert response["governance"]["sensitivity"]["authoritative"] == 1
    text = open(run.logger.approval_log_file).read()
    # The run's state no longer holds raw content, so take it from the source.
    docs = get_mcp_manager().call_tool("search_documents", {"query": "e", "domain": "hr"})
    for raw in [run.marker, "123-45-6789", h.analysis(False)["analysis"], "token"]:
        assert raw not in text, raw
    for doc in docs:
        assert doc["content"] not in text


def test_state_is_minimized_before_checkpointing():
    run = Run(**HR_MISREPORTED)
    run.start()
    state = run.state()
    assert state["analysis"] is None
    assert state["retrieved_documents"] and all(
        set(d) == {"ref_id", "source", "sensitivity"} for d in state["retrieved_documents"])
    assert all(d["source"].startswith("document_server:search_documents:doc:hr_")
               for d in state["retrieved_documents"])
    assert all("[redacted" in m["content"] for m in state["messages"] if m["role"] == "analyst")
    # The pending payload is still there: it's what the reviewer approves.
    assert state["final_output"] == run.marker


def test_metrics_summarise_requests_and_outcomes():
    runs = {}
    events = []
    for label, kwargs, decision in (("benign", PUBLIC, None), ("attack", HR_MISREPORTED, "reject"),
                                    ("benign", HR_DECLARED, "approve")):
        run = Run(**kwargs)
        run.start()
        if decision:
            run.respond(decision)
        runs[run.monitor.run_id] = label
        events += run.approval_events()
    m = approval_metrics(events, runs)
    assert m["approval_requests"] == 2 and m["approved"] == 1 and m["rejected"] == 1
    assert m["benign_runs"] == 2 and m["benign_runs_interrupted"] == 1
    assert m["attack_runs_escalated"] == 1 and m["attack_transmissions_executed"] == 0
    assert m["false_positive_escalation_rate"] == 0.5
    assert m["benign_transmissions_executed"] == 2


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
