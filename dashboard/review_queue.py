"""
Backend for the Human Approval page: lists runs paused for review in the
persistent approval store, submits reviewer decisions, and starts
synthetic demo runs (scripted LLM, no API key).

Everything security-relevant stays in the approval workflow
(governance/approval.py, agents/approval_flow.py). This module only
passes a reviewer's approve/reject back for the exact request that's
pending: it never builds or edits the action, so the backend's checks
(action ID and digest binding, signed approvals, the execution ledger)
apply unchanged.
"""
import json
import os
import uuid

from agents.approval_flow import NoPendingApproval, pending_review, start, submit_review
from agents.graph import build_graph
from agents.mcp_client import get_mcp_manager
from agents.state import new_state
from governance.approval import SENSITIVE_CROSSED_TO_EXTERNAL
from governance.audit_logger import get_audit_logger
from governance.checkpoint_store import DevApprovalStore
from governance.trajectory_monitor import TrajectoryMonitor

FLOW_RULES = [SENSITIVE_CROSSED_TO_EXTERNAL]

# Synthetic demo runs: (label, document domains, analyst declares sensitive)
DEMO_SCENARIOS = {
    "public_summary": ("Send a public research summary (no review expected)", ["research"], False),
    "hr_summary_misreported": ("Send an HR summary; analyst says 'not sensitive' (flow rule escalates)",
                               ["hr"], False),
    "hr_summary_declared": ("Send an HR summary; analyst says 'sensitive' (policy rule escalates)",
                            ["hr"], True),
}


class ScriptedLLM:
    """Stands in for Gemini in demo runs: returns fixed structured outputs."""

    def __init__(self, outputs):
        self.outputs = outputs

    def with_structured_output(self, schema):
        outputs = self.outputs

        class _Bound:
            def invoke(self, prompt):
                return schema(**outputs[schema.__name__])
        return _Bound()


def open_store(directory=None):
    return DevApprovalStore(directory, flow_rules=FLOW_RULES)


def _app(store, run_id, llm=None, audit_logger=None):
    monitor = TrajectoryMonitor(run_id=run_id, audit_logger=audit_logger)
    return build_graph(monitor, llm=llm, approvals=store.service, checkpointer=store.checkpointer)


def paused_threads(store):
    """Thread IDs that still have a checkpoint (finished runs are purged)."""
    seen = []
    for item in store.checkpointer.list(None):
        thread_id = item.config["configurable"]["thread_id"]
        if thread_id not in seen:
            seen.append(thread_id)
    return seen


def list_pending(store, audit_logger=None):
    """[(thread_id, review request)] for every run waiting on a reviewer."""
    reader = _app(store, run_id="review-reader", audit_logger=audit_logger)
    pending = []
    for thread_id in paused_threads(store):
        request = pending_review(reader, thread_id)
        if request is not None:
            pending.append((thread_id, request))
    return pending


def decide(store, thread_id, decision, reviewer, audit_logger=None):
    """Approves or rejects whatever is pending on this thread right now.
    Returns a summary of what happened; never raises for a request that
    was already decided."""
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be 'approve' or 'reject'")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("A reviewer name is required")
    reader = _app(store, run_id="review-reader", audit_logger=audit_logger)
    request = pending_review(reader, thread_id)
    if request is None:
        return {"status": "no_pending", "thread_id": thread_id}
    app = _app(store, run_id=request["run_id"], audit_logger=audit_logger)
    try:
        result = submit_review(app, thread_id, {
            "action_id": request["action_id"], "action_digest": request["action_digest"],
            "decision": decision, "reviewer": reviewer,
        })
    except NoPendingApproval:
        return {"status": "no_pending", "thread_id": thread_id}
    approval = result.get("approval") or {}
    send_event = next((e for e in reversed(result.get("governance_events", []))
                       if e["tool_name"] == "send_result"), {})
    return {
        "status": "decided",
        "thread_id": thread_id,
        "action_id": request["action_id"],
        "approval": approval.get("outcome"),
        "reason": approval.get("reason"),
        "executed": send_event.get("blocked") is False,
        "ledger": store.ledger.status(request["action_id"]),
        "halt_reason": result.get("halt_reason"),
    }


def start_demo(store, scenario_key, audit_logger=None):
    """Runs a synthetic task until it finishes or pauses for review."""
    label, domains, declared = DEMO_SCENARIOS[scenario_key]
    thread_id = f"demo-{uuid.uuid4().hex[:12]}"
    run_id = f"demo_{thread_id[-8:]}"
    llm = ScriptedLLM({
        "RetrievalPlan": {"task_type": "data_retrieval", "domains_to_search": domains,
                          "check_database": False, "database_table": None,
                          "needs_web_search": False, "search_queries": ["e"]},
        "AnalysisOutput": {"analysis": "Synthesis of the retrieved material.",
                           "contains_sensitive_data": declared, "key_findings": ["a", "b"]},
        "WriterOutput": {"final_answer": f"Summary for the partner team ({run_id}).",
                         "should_transmit_externally": True},
    })
    result = start(_app(store, run_id, llm=llm, audit_logger=audit_logger),
                   new_state(task=label, run_id=run_id), thread_id)
    return {"thread_id": thread_id, "run_id": run_id, "paused": "__interrupt__" in result,
            "halted": result.get("task_halted"), "halt_reason": result.get("halt_reason")}


def recent_decisions(limit=20, audit_logger=None):
    """Latest reviewer responses and executions from the approval log
    (metadata only: the log holds digests and IDs, never payloads)."""
    path = (audit_logger or get_audit_logger()).approval_log_file
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    rows = []
    for e in events:
        if e["event_type"] not in ("approval_response", "execution"):
            continue
        rows.append({
            "time": e["timestamp"][:19].replace("T", " "),
            "run": e["run_id"],
            "action": e["action_id"][:8],
            "event": e["event_type"],
            "outcome": (e.get("approval") or {}).get("outcome") if e["event_type"] == "approval_response"
            else (e.get("execution") or {}).get("outcome"),
            "reviewer": (e.get("approval") or {}).get("reviewer"),
        })
    return rows[-limit:][::-1]


def external_transmissions():
    """What the (synthetic) external MCP server has received: count and
    destinations only, no payload text."""
    log = get_mcp_manager().call_tool("get_transmission_log", {})
    return [{"time": t["timestamp"][:19].replace("T", " "), "destination": t["destination"],
             "payload_length": t["payload_length"]} for t in log]
