"""
Tests for agent-to-agent handoff instrumentation (shadow mode).

These run the real LangGraph pipeline against the real MCP servers and
the deployed risk model, with a scripted fake LLM so every run is
deterministic. Decisions are logged to a temporary audit log.

Run with pytest, or directly: python tests/test_handoff_instrumentation.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.analyst import ANALYST_INPUT_LIMITS, AnalysisOutput
from agents.graph import build_graph
from agents.handoffs import PIPELINE_HANDOFFS, HandoffTracker
from agents.orchestrator import RetrievalPlan
from agents.state import new_state
from agents.writer import WriterOutput
from governance.audit_logger import AuditLogger
from governance.policy_engine import PolicyEngine
from governance.risk_engine import load_feature_list
from governance.trajectory_monitor import TrajectoryMonitor

ACTION_KEYS = {"agent_role", "tool_name", "action_type", "data_sensitivity", "destination_category"}


class FakeLLM:
    """Returns scripted structured outputs and records every prompt."""

    def __init__(self, plan, analysis, writer):
        self.outputs = {RetrievalPlan: plan, AnalysisOutput: analysis, WriterOutput: writer}
        self.prompts = []

    def with_structured_output(self, schema):
        llm = self

        class _Bound:
            def invoke(self, prompt):
                llm.prompts.append((schema.__name__, prompt))
                return schema(**llm.outputs[schema])
        return _Bound()


def plan(domains, table=None, web=False, query="e"):
    return {"task_type": "data_retrieval", "domains_to_search": domains,
            "check_database": table is not None, "database_table": table,
            "needs_web_search": web, "search_queries": [query]}


def analysis(sensitive):
    return {"analysis": "Synthesis of the retrieved material.",
            "contains_sensitive_data": sensitive, "key_findings": ["a", "b"]}


def writer(transmit):
    return {"final_answer": "Here is the answer.", "should_transmit_externally": transmit}


SCENARIOS = {
    "benign": dict(plan=plan(["research"]), analysis=analysis(False), writer=writer(False)),
    "sensitive": dict(plan=plan(["hr"], table="employees"), analysis=analysis(True), writer=writer(False)),
    "sensitive_send_misreported": dict(plan=plan(["hr"], table="transactions"),
                                       analysis=analysis(False), writer=writer(True)),
    "web": dict(plan=plan(["research"], web=True), analysis=analysis(False), writer=writer(False)),
    "truncated": dict(plan=plan(["hr", "finance", "research"], table="employees"),
                      analysis=analysis(True), writer=writer(False)),
}


class BlockDatabase(PolicyEngine):
    def evaluate(self, trajectory_prefix, candidate_action):
        if candidate_action["tool_name"] == "query_database":
            return "BLOCKED", "test: database access blocked"
        return super().evaluate(trajectory_prefix, candidate_action)


def run(scenario, handoff_mode="shadow", policy_engine=None, run_id=None):
    logger = AuditLogger(os.path.join(tempfile.mkdtemp(), "audit_log.jsonl"))
    monitor = TrajectoryMonitor(run_id=run_id or f"test_{scenario}", audit_logger=logger,
                                handoff_mode=handoff_mode, policy_engine=policy_engine)
    llm = FakeLLM(**SCENARIOS[scenario])
    app = build_graph(monitor, llm=llm)
    state = app.invoke(new_state(task=f"Task for {scenario}", run_id=monitor.run_id))
    return state, monitor, llm, logger


def by_edge(monitor):
    return {(h["sender"], h["receiver"]): h for h in monitor.handoffs}


# --- completeness ------------------------------------------------------

def test_declared_pipeline_matches_graph():
    monitor = TrajectoryMonitor(audit_logger=AuditLogger(
        os.path.join(tempfile.mkdtemp(), "a.jsonl")))
    graph = build_graph(monitor, llm=FakeLLM(**SCENARIOS["benign"])).get_graph()
    agent_edges = {(e.source, e.target) for e in graph.edges
                   if not e.source.startswith("__") and not e.target.startswith("__")}
    declared_agent_edges = {e for e in PIPELINE_HANDOFFS
                            if "user" not in e and "external_server" not in e}
    assert agent_edges == declared_agent_edges, (agent_edges, declared_agent_edges)


def test_every_handoff_captured_in_order():
    for scenario in SCENARIOS:
        state, monitor, _, _ = run(scenario)
        assert monitor.instrumentation_errors == [], monitor.instrumentation_errors
        edges = [(h["sender"], h["receiver"]) for h in monitor.handoffs]
        expected = [("user", "orchestrator"), ("orchestrator", "retriever"),
                    ("retriever", "analyst"), ("analyst", "writer")]
        if SCENARIOS[scenario]["writer"]["should_transmit_externally"]:
            expected.append(("writer", "external_server"))
        expected.append(("writer", "user"))
        assert edges == expected, (scenario, edges)


def test_sequence_numbers_order_tool_calls_and_handoffs():
    _, monitor, _, logger = run("sensitive_send_misreported")
    events = [(d.seq, "tool", d.action["tool_name"]) for d in monitor.decisions]
    events += [(h["seq"], "handoff", f"{h['sender']}->{h['receiver']}") for h in monitor.handoffs]
    events.sort()
    seqs = [e[0] for e in events]
    assert seqs == list(range(1, len(seqs) + 1)), seqs
    names = [e[2] for e in events]
    assert names[:2] == ["user->orchestrator", "orchestrator->retriever"]
    retriever_calls = names[2:names.index("retriever->analyst")]
    assert retriever_calls and all(n in ("search_documents", "query_database", "search_web")
                                   for n in retriever_calls), names
    assert names[-3:] == ["send_result", "writer->external_server", "writer->user"], names
    # Same seq values in the on-disk logs, joinable by run_id.
    with open(logger.log_file) as f:
        logged_tool_seqs = [json.loads(l)["seq"] for l in f]
    with open(logger.handoff_log_file) as f:
        logged_handoff_seqs = [json.loads(l)["seq"] for l in f]
    assert sorted(logged_tool_seqs + logged_handoff_seqs) == seqs


# --- sensitivity -------------------------------------------------------

def test_non_sensitive_transfers():
    for scenario in ("benign", "web"):
        _, monitor, _, _ = run(scenario)
        for h in monitor.handoffs:
            assert h["sensitivity"] == 0 and h["sensitive_refs"] == [], (scenario, h)
    _, monitor, _, _ = run("web")
    web_refs = by_edge(monitor)[("retriever", "analyst")]["payload"]["web_results"]
    assert web_refs
    for r in web_refs:
        ref = monitor.provenance.refs[r]
        assert ref["sensitivity"] == {"value": 0, "basis": "public_web"}
        assert ref["source"].startswith("web_server:search_web:https://")


def test_sensitive_transfers():
    _, monitor, _, _ = run("sensitive")
    h = by_edge(monitor)
    retr = h[("retriever", "analyst")]
    reg = monitor.provenance
    assert retr["sensitivity"] == 1
    doc_refs = retr["payload"]["retrieved_documents"]
    rec_refs = retr["payload"]["retrieved_records"]
    assert doc_refs and rec_refs
    for r in doc_refs:
        assert reg.refs[r]["sensitivity"] == {"value": 1, "basis": "document_label"}
        assert reg.refs[r]["source"].startswith("document_server:search_documents:doc:hr_")
    for r in rec_refs:
        assert reg.refs[r]["sensitivity"] == {"value": 1, "basis": "table_policy"}
        assert reg.refs[r]["source"].startswith("database_server:query_database:employees#")
    assert h[("analyst", "writer")]["sensitivity"] == 1
    assert h[("writer", "user")]["sensitivity"] == 1
    # The plan carries no data, but asks for sensitive data.
    orch = h[("orchestrator", "retriever")]
    assert orch["sensitivity"] == 0 and orch["details"]["requests_sensitive_access"] is True


def test_self_report_gaps_are_flagged_not_enforced():
    state, monitor, _, _ = run("sensitive_send_misreported")
    h = by_edge(monitor)
    assert "self_report_disagrees_with_provenance" in h[("analyst", "writer")]["flags"]
    tx = h[("writer", "external_server")]
    assert tx["details"]["declared_sensitivity"] == 0
    assert tx["details"]["provenance_sensitive"] == 1
    assert "declared_sensitivity_lower_than_provenance" in tx["flags"]
    send = [d for d in monitor.decisions if d.action["tool_name"] == "send_result"][0]
    assert tx["details"]["tool_event_id"] == send.event_id
    assert tx["details"]["executed"] == send.allowed
    assert tx["enforced"] is False


# --- provenance --------------------------------------------------------

def test_provenance_survives_transformations():
    _, monitor, _, _ = run("sensitive_send_misreported")
    reg = monitor.provenance
    h = by_edge(monitor)
    read = h[("retriever", "analyst")]["consumed_refs"]
    analysis_ref = h[("analyst", "writer")]["produced_ref"]
    assert reg.refs[analysis_ref]["derived_from"] == read
    answer_ref = h[("writer", "user")]["payload"]["final_output"][0]
    assert h[("writer", "external_server")]["payload"]["payload"] == [answer_ref]
    assert analysis_ref in reg.refs[answer_ref]["derived_from"]
    # The answer traces back to every tool result the analyst read, and
    # each of those to the governed call that returned it.
    executed = {d.event_id: d for d in monitor.decisions if d.allowed}
    tool_origins = [o for o in reg.origins(answer_ref) if reg.refs[o]["kind"] == "tool_result"]
    assert set(tool_origins) == {r for r in read if reg.refs[r]["kind"] == "tool_result"}
    for o in tool_origins:
        ref = reg.refs[o]
        assert ref["tool_event_id"] in executed
        assert executed[ref["tool_event_id"]].action["tool_name"] == ref["via_tool"]
    assert set(h[("writer", "external_server")]["origins"]) == set(reg.origins(answer_ref))


def test_consumed_refs_respect_analyst_input_limits():
    state, monitor, _, _ = run("truncated")
    retr = by_edge(monitor)[("retriever", "analyst")]
    handed = retr["payload"]
    assert len(handed["retrieved_documents"]) == len(state["retrieved_documents"]) == 15
    expected_read = (handed["retrieved_documents"][:ANALYST_INPUT_LIMITS["retrieved_documents"]]
                     + handed["retrieved_records"][:ANALYST_INPUT_LIMITS["retrieved_records"]]
                     + handed["web_results"][:ANALYST_INPUT_LIMITS["web_results"]]
                     + handed["task"])
    assert retr["consumed_refs"] == expected_read
    assert retr["details"]["read_by_receiver"] == 20


def test_blocked_calls_register_no_data():
    state, monitor, _, _ = run("sensitive", policy_engine=BlockDatabase())
    blocked = [d for d in monitor.decisions if d.action["tool_name"] == "query_database"]
    assert blocked and not blocked[0].allowed
    assert all(r["tool_event_id"] != blocked[0].event_id for r in monitor.provenance.refs.values())
    assert by_edge(monitor)[("retriever", "analyst")]["payload"]["retrieved_records"] == []
    assert state["retrieved_records"] == []


def test_unregistered_data_is_flagged():
    monitor = TrajectoryMonitor(audit_logger=AuditLogger(
        os.path.join(tempfile.mkdtemp(), "a.jsonl")))
    tracker = HandoffTracker(monitor)
    state = new_state(task="t")
    tracker.task_received(state)
    state["retrieved_documents"] = [{"id": "planted", "content": "not from any tool call"}]
    tracker.after_retriever(state)
    h = monitor.handoffs[-1]
    ref = monitor.provenance.refs[h["payload"]["retrieved_documents"][0]]
    assert ref["kind"] == "unregistered" and ref["sensitivity"]["value"] is None
    assert "unregistered_data" in h["flags"] and h["sensitivity"] is None


# --- shadow mode: no change in behaviour ------------------------------

def _behaviour(state, monitor, llm):
    return {
        "prompts": llm.prompts,
        "plan": state["plan"], "documents": state["retrieved_documents"],
        "records": state["retrieved_records"], "analysis": state["analysis"],
        "final_output": state["final_output"], "governance_events": state["governance_events"],
        "task_halted": state["task_halted"], "messages": state["messages"],
        "trajectory": monitor.trajectory,
        "decisions": [(d.action, d.decision, d.risk_score, d.source) for d in monitor.decisions],
    }


def test_shadow_mode_does_not_change_behaviour():
    for scenario in ("benign", "sensitive", "sensitive_send_misreported", "truncated"):
        on = run(scenario, handoff_mode="shadow", run_id="same")
        off = run(scenario, handoff_mode="off", run_id="same")
        assert on[1].handoffs and not off[1].handoffs
        assert _behaviour(*on[:3]) == _behaviour(*off[:3]), scenario


def test_handoffs_never_reach_the_model_or_decisions():
    for scenario in SCENARIOS:
        state, monitor, _, _ = run(scenario)
        assert all(set(a) == ACTION_KEYS for a in monitor.trajectory)
        # One decision per governed tool call the agents made, none for handoffs.
        assert len(monitor.decisions) == len(state["governance_events"])
        assert all(h["mode"] == "shadow" and h["enforced"] is False for h in monitor.handoffs)
    for name in ("trajectory_level", "action_level"):
        feats = load_feature_list(name)
        assert not {"seq", "timestamp_norm", "prev_tool_count", "run_length"} & set(feats), feats


def test_benign_workflow_is_not_flagged():
    _, monitor, _, logger = run("benign")
    for h in monitor.handoffs:
        assert h["authorized"] is True and h["flags"] == [] and h["sensitivity"] == 0, h
    assert all(d.allowed for d in monitor.decisions)
    with open(logger.log_file) as f:
        assert all("risk_score" in json.loads(l) for l in f)


def test_instrumentation_errors_do_not_stop_the_run():
    original = HandoffTracker.after_analyst

    def broken(self, state):
        raise RuntimeError("simulated instrumentation bug")
    HandoffTracker.after_analyst = broken
    try:
        state, monitor, _, _ = run("sensitive")
    finally:
        HandoffTracker.after_analyst = original
    assert state["final_output"] == "Here is the answer."
    assert len(monitor.instrumentation_errors) == 1
    assert "simulated instrumentation bug" in monitor.instrumentation_errors[0]
    # Later handoffs are still recorded; the analysis has no provenance,
    # so it shows up as unregistered with unknown (not zero) sensitivity.
    edges = [(h["sender"], h["receiver"]) for h in monitor.handoffs]
    assert ("analyst", "writer") not in edges and ("writer", "user") in edges
    delivery = by_edge(monitor)[("writer", "user")]
    assert delivery["sensitivity"] is None
    assert "unregistered_data" in delivery["flags"]



def test_handoff_log_lines_are_self_contained():
    _, monitor, _, logger = run("sensitive_send_misreported")
    with open(logger.handoff_log_file) as f:
        lines = [json.loads(l) for l in f]
    assert [l["event_id"] for l in lines] == [h["event_id"] for h in monitor.handoffs]
    for line in lines:
        for r in line["consumed_refs"] + line["origins"]:
            assert r in line["refs"], (line["event_id"], r)


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
