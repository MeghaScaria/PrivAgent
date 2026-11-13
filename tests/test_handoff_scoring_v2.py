"""
V2_PLAN.md WP2: handoffs scored as pseudo-actions (handoff_mode="score")
and enforced (handoff_enforce). v2 only; v1 defaults unchanged.

The pipeline tests run the real LangGraph pipeline against the real MCP
servers with the scripted LLM of tests/test_handoff_instrumentation.py.
The R3 test drives the monitor directly (see its docstring for why).
All logs go to temporary directories.

    python tests/test_handoff_scoring_v2.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.test_handoff_instrumentation as h  # noqa: E402
from agents.graph import build_graph  # noqa: E402
from agents.state import new_state  # noqa: E402
from governance.audit_logger import AuditLogger  # noqa: E402
from governance.trajectory_monitor import SCORED_HANDOFFS, TrajectoryMonitor  # noqa: E402

V2_AS_V1 = dict(governance_version="v2", precedence="first_fire_v1", restricted_semantics=False)


def _monitor(**kw):
    return TrajectoryMonitor(run_id=kw.pop("run_id", "t"),
                             audit_logger=AuditLogger(os.path.join(tempfile.mkdtemp(), "a.jsonl")),
                             **kw)


def run(scenario, score_override=None, **kw):
    """Runs a scripted scenario. score_override(candidate) -> score or None
    replaces the model's score for matching candidates (to force a handoff
    decision); everything else is scored by the frozen model."""
    monitor = _monitor(run_id=f"t_{scenario}", **kw)
    if score_override is not None:
        real = monitor.risk_engine.compute_risk

        def compute(prefix, cand, *a):
            forced = score_override(cand)
            return real(prefix, cand, *a) if forced is None else forced
        monitor.risk_engine.compute_risk = compute
    llm = h.FakeLLM(**h.SCENARIOS[scenario])
    state = build_graph(monitor, llm=llm).invoke(
        new_state(task=f"Task for {scenario}", run_id=monitor.run_id))
    return state, monitor, llm


def _pseudo(monitor):
    return [a for a in monitor.trajectory if a.get("kind") == "handoff"]


# -- shadow is v1 -------------------------------------------------------------

def test_shadow_trajectory_byte_identical_to_v1():
    for scenario in ("benign", "sensitive", "sensitive_send_misreported", "truncated"):
        _, v1, _ = run(scenario)                                  # v1 defaults
        _, v2_shadow, _ = run(scenario, handoff_mode="shadow", **V2_AS_V1)
        a = json.dumps(v1.trajectory, sort_keys=True)
        b = json.dumps(v2_shadow.trajectory, sort_keys=True)
        assert a == b, scenario
        assert not _pseudo(v1) and all("score" not in e for e in v1.handoffs)
        assert all(e["enforced"] is False and e["mode"] == "shadow" for e in v1.handoffs)


def test_score_mode_is_v2_only_and_enforce_needs_score():
    for kw in ({"handoff_mode": "score"}, {"handoff_enforce": True},
               {"governance_version": "v2", "handoff_enforce": True}):
        try:
            _monitor(**kw)
        except ValueError:
            continue
        raise AssertionError(f"accepted {kw}")


# -- score --------------------------------------------------------------------

def test_score_adds_tagged_pseudo_actions_from_provenance():
    state, m, _ = run("sensitive_send_misreported", handoff_mode="score", **V2_AS_V1)
    pseudo = _pseudo(m)
    edges = [(e["sender"], e["receiver"]) for e in m.handoffs if "score" in e]
    assert edges == [("retriever", "analyst"), ("analyst", "writer")], edges
    assert len(pseudo) == 2
    by_id = {e["event_id"]: e for e in m.handoffs}
    for p, (sender, receiver) in zip(pseudo, edges):
        role, tool, action_type = SCORED_HANDOFFS[(sender, receiver)]
        assert (p["agent_role"], p["tool_name"], p["action_type"], p["destination_category"]) == \
            (role, tool, action_type, "cross_agent")
        assert by_id[p["event_id"]]["sender"] == sender
        # provenance, not the analyst's declaration (which is False here)
        assert p["data_sensitivity"] == 1
    assert ("orchestrator", "retriever") not in edges
    # pseudo-actions feed the features of later steps: the send now sees cross-agent moves
    send = next(d for d in m.decisions if d.action["tool_name"] == "send_result")
    send_index = next(i for i, a in enumerate(m.trajectory) if a is not None
                      and a.get("tool_name") == "send_result") if send.allowed else len(m.trajectory)
    assert sum(a["destination_category"] == "cross_agent" for a in m.trajectory[:send_index]) == 2


def test_unknown_provenance_counts_as_sensitive():
    m = _monitor(governance_version="v2", handoff_mode="score")
    ref = m.provenance.register_root("unregistered", "retriever", {"value": None, "basis": "test"})
    event = m.record_handoff("handoff", "retriever", "analyst", {"x": [ref]})
    assert event["sensitivity"] is None
    assert event["score"]["pseudo_action"]["data_sensitivity"] == 1


def test_r3_fires_live_under_score_with_three_scored_handoffs():
    """R3 needs >= 3 earlier cross_agent actions. A standard pipeline run
    has only two scored handoffs (checked in the next test), so this drives
    the monitor with three data handoffs of non-sensitive web data (keeping
    R1 and R2 out of it), then an external send."""
    def drive(mode, **kw):
        m = _monitor(governance_version="v2", handoff_mode=mode, **kw)
        read = m.evaluate("retriever", "search_web", "read", 0, "internal")
        refs = m.register_tool_result(read, "search_web", {"query": "q"},
                                      [{"url": "https://example.org/x", "title": "t", "snippet": "s"}])
        m.record_handoff("handoff", "retriever", "analyst", {"web_results": refs})
        for i in range(2):
            out = m.provenance.derive("analysis", "analyst", refs, content=f"analysis {i}")
            m.record_handoff("handoff", "analyst", "writer", {"analysis": [out]}, produced_ref=out)
        return m, m.evaluate("writer", "send_result", "transmit", 0, "external")

    m, send = drive("score")
    assert len(_pseudo(m)) == 3
    assert "R3" in [r["rule_id"] for r in send.combination["rules_fired"]], send.combination
    assert send.decision == "BLOCKED" and not send.allowed
    _, shadow_send = drive("shadow")
    assert "R3" not in [r["rule_id"] for r in shadow_send.combination["rules_fired"]]


def test_standard_pipeline_scores_exactly_two_handoffs():
    """Documents why R3 (>= 3 cross_agent) cannot fire in one standard
    four-agent run even under score: there are two scored handoffs."""
    for scenario in ("benign", "sensitive", "web"):
        _, m, _ = run(scenario, handoff_mode="score", **V2_AS_V1)
        assert len(_pseudo(m)) == 2, scenario


def test_r1_counts_handoffs_ablation():
    """One sensitive read whose data passes through both handoffs. With the
    flag on (default under score), R1 sees 3 sensitive actions and fires;
    off, it sees only the real read (1) and does not. ML features and R3
    are unaffected by the flag."""
    def drive(**kw):
        m = _monitor(governance_version="v2", handoff_mode="score", **kw)
        m.risk_engine.compute_risk = lambda *a: 0.05          # isolate the rules
        read = m.evaluate("retriever", "search_documents", "read", 1, "internal")
        refs = m.register_tool_result(read, "search_documents", {"query": "q", "domain": "hr"},
                                      [{"id": "hr_001", "sensitivity": "high"}])
        m.record_handoff("handoff", "retriever", "analyst", {"retrieved_documents": refs})
        out = m.provenance.derive("analysis", "analyst", refs, content="a")
        m.record_handoff("handoff", "analyst", "writer", {"analysis": [out]}, produced_ref=out)
        return m, m.evaluate("writer", "send_result", "transmit", 0, "external")

    on, send_on = drive()
    assert on.r1_counts_handoffs is True and on.policy_engine.r1_counts_handoffs is True
    assert [p["data_sensitivity"] for p in _pseudo(on)] == [1, 1]
    assert "R1" in [r["rule_id"] for r in send_on.combination["rules_fired"]]
    assert send_on.decision == "BLOCKED"
    off, send_off = drive(r1_counts_handoffs=False)
    assert "R1" not in [r["rule_id"] for r in send_off.combination["rules_fired"]]
    assert send_off.decision == "AUTONOMOUS"
    # The flag changes only R1's count: everything before the send is identical
    # (the send itself is appended only where it was allowed).
    assert json.dumps(on.trajectory[:3], sort_keys=True) == json.dumps(off.trajectory[:3], sort_keys=True)
    assert len(on.trajectory) == 3 and len(off.trajectory) == 4
    for kw in ({"r1_counts_handoffs": False}, {"governance_version": "v2", "r1_counts_handoffs": True}):
        try:
            _monitor(**kw)
        except ValueError:
            continue
        raise AssertionError(f"accepted {kw} without handoff_mode='score'")


# -- enforce ------------------------------------------------------------------

def _force_handoff(score):
    return lambda cand: score if cand["tool_name"] == "analyze" else None


def test_enforce_blocked_handoff_halts_before_receiver():
    state, m, llm = run("sensitive", score_override=_force_handoff(0.95),
                        governance_version="v2", handoff_mode="score", handoff_enforce=True)
    assert state["task_halted"]
    assert "retriever -> analyst BLOCKED" in state["halt_reason"]
    assert "Run halted before analyst" in state["halt_reason"]
    called = [name for name, _ in llm.prompts]
    assert "AnalysisOutput" not in called and "WriterOutput" not in called, called
    assert state["final_output"] in (None, "")
    assert m.handoff_halt["decision"] == "BLOCKED"
    assert not _pseudo(m)                       # never reached the receiver
    assert state["governance_events"][-1]["tool_name"] == "handoff"


def test_enforce_human_approval_handoff_halts_as_blocked():
    state, m, llm = run("sensitive", score_override=_force_handoff(0.6),
                        governance_version="v2", handoff_mode="score", handoff_enforce=True)
    assert state["task_halted"] and m.handoff_halt["decision"] == "HUMAN_APPROVAL"
    assert "HUMAN_APPROVAL is treated as BLOCKED" in state["halt_reason"]
    assert "AnalysisOutput" not in [name for name, _ in llm.prompts]


def test_enforce_halts_at_second_handoff_before_writer():
    calls = {"n": 0}

    def second_only(cand):
        if cand["tool_name"] != "analyze":
            return None
        calls["n"] += 1
        return 0.95 if calls["n"] == 2 else 0.05
    state, m, llm = run("sensitive_send_misreported", score_override=second_only,
                        governance_version="v2", handoff_mode="score", handoff_enforce=True)
    called = [name for name, _ in llm.prompts]
    assert "AnalysisOutput" in called and "WriterOutput" not in called, called
    assert "analyst -> writer BLOCKED" in state["halt_reason"]
    assert not any(d.action["tool_name"] == "send_result" for d in m.decisions)


def test_score_without_enforce_never_halts_but_records():
    state, m, llm = run("sensitive", score_override=_force_handoff(0.95),
                        governance_version="v2", handoff_mode="score")
    assert not state["task_halted"] and m.handoff_halt is None
    assert "WriterOutput" in [name for name, _ in llm.prompts]
    pseudo = _pseudo(m)
    assert len(pseudo) == 2 and all(p.get("executed_despite_decision") for p in pseudo)


def test_enforce_fails_closed_when_scoring_raises():
    def boom(cand):
        if cand["tool_name"] == "analyze":
            raise RuntimeError("scoring unavailable")
        return None
    state, m, llm = run("sensitive", score_override=boom,
                        governance_version="v2", handoff_mode="score", handoff_enforce=True)
    assert state["task_halted"] and "fail closed" in state["halt_reason"]
    assert m.instrumentation_errors
    assert "AnalysisOutput" not in [name for name, _ in llm.prompts]


def test_enforce_halts_approval_graph_before_writer_nodes():
    from governance.approval import ApprovalService, ExecutionLedger
    from langgraph.checkpoint.memory import InMemorySaver
    m = _monitor(run_id="t_approval", governance_version="v2", handoff_mode="score",
                 handoff_enforce=True)
    real = m.risk_engine.compute_risk
    m.risk_engine.compute_risk = lambda p, c, *a: 0.95 if c["tool_name"] == "analyze" else real(p, c, *a)
    service = ApprovalService(ExecutionLedger(os.path.join(tempfile.mkdtemp(), "l.sqlite")))
    llm = h.FakeLLM(**h.SCENARIOS["sensitive_send_misreported"])
    app = build_graph(m, llm=llm, approvals=service, checkpointer=InMemorySaver())
    state = app.invoke(new_state(task="Task", run_id=m.run_id),
                       {"configurable": {"thread_id": "t1"}})
    assert state["task_halted"] and state.get("pending_action") is None
    assert "WriterOutput" not in [name for name, _ in llm.prompts]


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
