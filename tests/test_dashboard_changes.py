"""
Tests for the dashboard changes: Attack Lab halt-on-block, the Human
Approval page and its review queue, and the local Streamlit security
settings. Stores and logs live in temporary directories.

Run with pytest, or directly: python tests/test_dashboard_changes.py
"""
import os
import sys
import tempfile
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from streamlit.testing.v1 import AppTest

import agents.tools as tools_module
from agents.mcp_client import get_mcp_manager
from dashboard import review_queue
from governance.attack_scenarios import SCENARIOS, run_scenario
from governance.audit_logger import AuditLogger
from governance.trajectory_monitor import TrajectoryMonitor


def _logger():
    return AuditLogger(os.path.join(tempfile.mkdtemp(), "audit_log.jsonl"))


def _sent_count():
    return len(get_mcp_manager().call_tool("get_transmission_log", {}))


class _CountingManager:
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def call_tool(self, name, args, **kw):
        self.calls.append(name)
        return self.inner.call_tool(name, args, **kw)


# -- Attack Lab --------------------------------------------------------

def test_halt_on_block_runs_nothing_after_the_first_stop():
    real = get_mcp_manager()
    for key in SCENARIOS:
        counter = _CountingManager(real)
        original = tools_module.get_mcp_manager
        tools_module.get_mcp_manager = lambda: counter
        try:
            monitor = TrajectoryMonitor(task_type="financial_research", agent_count=3,
                                        audit_logger=_logger())
            steps = run_scenario(key, monitor, halt_on_block=True)
        finally:
            tools_module.get_mcp_manager = original
        first = next((i for i, s in enumerate(steps) if s["blocked"]), None)
        evaluated = len(steps) if first is None else first + 1
        assert len(monitor.decisions) == evaluated, key
        assert all(not s["not_run"] for s in steps[:evaluated]), key
        assert all(s["not_run"] and s["decision"] is None for s in steps[evaluated:]), key
        # MCP calls happened only for executed steps that have a real tool call.
        executed_tools = [s["decision"]["action"]["tool_name"] for s in steps[:evaluated]
                          if not s["blocked"] and s["decision"]["action"]["tool_name"]
                          not in ("analyze", "summarize")]
        assert counter.calls == executed_tools, (key, counter.calls, executed_tools)


def test_privilege_escalation_step_after_a_stop_no_longer_runs():
    monitor = TrajectoryMonitor(task_type="financial_research", agent_count=3, audit_logger=_logger())
    default = run_scenario("path_privilege_escalation", monitor)
    stop = next(i for i, s in enumerate(default) if s["blocked"])
    after = [s for s in default[stop + 1:] if not s["blocked"]]
    assert after, "expected the default replay to execute a step after the stop"
    halted = run_scenario("path_privilege_escalation", TrajectoryMonitor(
        task_type="financial_research", agent_count=3, audit_logger=_logger()), halt_on_block=True)
    assert all(s["not_run"] for s in halted[stop + 1:])


def test_default_replay_mode_is_unchanged():
    monitor = TrajectoryMonitor(task_type="financial_research", agent_count=3, audit_logger=_logger())
    steps = run_scenario("permission_laundering", monitor)
    assert len(monitor.decisions) == len(steps) == 6
    assert all("not_run" not in s for s in steps)


def test_attack_lab_page_shows_what_actually_ran():
    at = AppTest.from_file(os.path.join(ROOT, "dashboard", "app.py"), default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value("Attack Laboratory").run()
    at.selectbox[0].set_value("permission_laundering").run()
    at.button[0].click().run()
    text = " ".join(m.value for m in at.markdown)
    assert "Attack stopped at step 4 of 6" in text, text[-600:]
    assert "Steps 5 to 6 were not evaluated or executed" in text
    assert text.count("NOT RUN") == 2
    assert not at.exception


# -- Review queue and Human Approval page ------------------------------

def _queue():
    return review_queue.open_store(tempfile.mkdtemp()), _logger()


def test_benign_demo_needs_no_review():
    store, logger = _queue()
    before = _sent_count()
    outcome = review_queue.start_demo(store, "public_summary", audit_logger=logger)
    assert outcome["paused"] is False and not outcome["halted"]
    assert _sent_count() == before + 1
    assert review_queue.list_pending(store, audit_logger=logger) == []


def test_approve_sends_once_and_duplicates_send_nothing():
    store, logger = _queue()
    outcome = review_queue.start_demo(store, "hr_summary_misreported", audit_logger=logger)
    assert outcome["paused"]
    pending = review_queue.list_pending(store, audit_logger=logger)
    assert [t for t, _ in pending] == [outcome["thread_id"]]
    request = pending[0][1]
    assert request["decided_by"] == "flow_rule" and request["destination"] == "external"
    assert request["governance"]["sensitivity"]["provenance"]["value"] == 1
    before = _sent_count()
    result = review_queue.decide(store, outcome["thread_id"], "approve", "alice", audit_logger=logger)
    assert result["executed"] and result["ledger"] == "executed" and result["approval"] == "approved"
    assert _sent_count() == before + 1
    again = review_queue.decide(store, outcome["thread_id"], "approve", "alice", audit_logger=logger)
    assert again["status"] == "no_pending" and _sent_count() == before + 1
    assert review_queue.list_pending(store, audit_logger=logger) == []


def test_reject_sends_nothing():
    store, logger = _queue()
    outcome = review_queue.start_demo(store, "hr_summary_declared", audit_logger=logger)
    request = review_queue.list_pending(store, audit_logger=logger)[0][1]
    assert request["decided_by"] == "policy_engine"
    before = _sent_count()
    result = review_queue.decide(store, outcome["thread_id"], "reject", "bob", audit_logger=logger)
    assert result["approval"] == "rejected" and not result["executed"] and result["ledger"] is None
    assert _sent_count() == before
    rows = review_queue.recent_decisions(audit_logger=logger)
    assert {"rejected", "refused"} <= {r["outcome"] for r in rows}
    assert all("Summary for the partner" not in str(r) for r in rows)


def test_reviewer_is_required_and_modified_payloads_are_refused():
    store, logger = _queue()
    outcome = review_queue.start_demo(store, "hr_summary_misreported", audit_logger=logger)
    try:
        review_queue.decide(store, outcome["thread_id"], "approve", "  ", audit_logger=logger)
    except ValueError:
        pass
    else:
        raise AssertionError("approved without a reviewer name")
    app = review_queue._app(store, run_id="tamper", audit_logger=logger)
    cfg = {"configurable": {"thread_id": outcome["thread_id"]}}
    app.update_state(cfg, {"final_output": "Changed after the gate"})
    app.invoke(None, cfg, durability="exit")
    before = _sent_count()
    result = review_queue.decide(store, outcome["thread_id"], "approve", "alice", audit_logger=logger)
    assert result["reason"] == "payload_changed_after_gate" and not result["executed"]
    assert _sent_count() == before


def test_approval_page_lists_and_approves():
    directory = tempfile.mkdtemp()
    original = review_queue.open_store
    review_queue.open_store = lambda d=None: original(directory)
    try:
        store = original(directory)
        outcome = review_queue.start_demo(store, "hr_summary_misreported", audit_logger=_logger())
        store.close()
        import streamlit as st
        st.cache_resource.clear()
        at = AppTest.from_file(os.path.join(ROOT, "dashboard", "app.py"), default_timeout=120)
        at.run()
        at.sidebar.radio[0].set_value("Human Approval").run()
        assert any("Pending (1)" in m.value for m in at.markdown)
        approve = [b for b in at.button if b.label == "Approve"][0]
        assert approve.disabled  # no reviewer name yet
        assert any(outcome["run_id"] in c.value for c in at.code)
        at.text_input(key="reviewer_name").input("carol").run()
        before = _sent_count()
        [b for b in at.button if b.label == "Approve"][0].click().run()
        assert any("sent once" in s.value for s in at.success), [s.value for s in at.success]
        assert any("Pending (0)" in m.value for m in at.markdown)
        assert _sent_count() == before + 1
        assert not at.exception
    finally:
        review_queue.open_store = original
        import streamlit as st
        st.cache_resource.clear()


# -- Local security settings -------------------------------------------

def test_streamlit_config_is_local_only():
    with open(os.path.join(ROOT, ".streamlit", "config.toml"), "rb") as f:
        server = tomllib.load(f)["server"]
    assert server["address"] == "127.0.0.1"
    assert server["enableCORS"] is True
    assert server["enableXsrfProtection"] is True
    assert set(server["allowedHosts"]) == {"127.0.0.1", "localhost"}
    assert "corsAllowedOrigins" not in server


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
