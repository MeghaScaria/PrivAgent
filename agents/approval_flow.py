"""
Graph nodes and run helpers for the human-approval pipeline (see
governance/approval.py for the guarantees). In the approval graph, the
writer's single node becomes four, so that nothing with side effects
sits before the interrupt in the node that pauses:

  writer_compose        the writer's LLM step only
  transmission_gate     governance + flow rules, once; logs the request
  human_approval        interrupt() and response validation, nothing else
  transmission_execute  re-checks the approval, claims the action in the
                        ledger, then calls the tool at most once

LangGraph restarts a node from the top when it resumes, so the code in
human_approval before interrupt() must stay side-effect free.

What gets checkpointed: runs use durability="exit", so state is only
written when a run pauses or finishes, never after the retriever while
raw documents are in it. writer_compose also replaces the retrieved
documents, records, web results and the analysis with reference stubs
as soon as the writer has used them, so a paused run's checkpoint holds
only refs, labels, the task and the pending payload. With
purge_completed, a thread's checkpoints are deleted when its run ends.
"""
from langgraph.types import Command, interrupt

from agents import tools
from agents.writer import compose_answer
from governance.approval import ALLOWED_DECISIONS


class NoPendingApproval(Exception):
    """Raised when asked to resume a thread with no review waiting."""


class _DecisionRef:
    """Minimal stand-in for a GovernanceDecision when the run resumes in a
    monitor that didn't make the original decision (e.g. a restarted
    process): enough to register the tool result's provenance."""

    def __init__(self, event_id, agent_role):
        self.event_id = event_id
        self.action = {"agent_role": agent_role}


RETRIEVED_FIELDS = ("retrieved_documents", "retrieved_records", "web_results")
REDACTED = "[redacted before checkpointing]"


def minimize_state(state, provenance):
    """Replaces retrieved content and the analysis with references. Nothing
    after the writer's LLM step reads them."""
    for field in RETRIEVED_FIELDS:
        stubs = []
        for item in state[field]:
            ref = provenance.snapshot(provenance.lookup(item))
            stubs.append({"ref_id": ref["ref_id"], "source": ref["source"],
                          "sensitivity": ref["sensitivity"]["value"]})
        state[field] = stubs
    state["analysis"] = None
    for message in state["messages"]:
        if message["role"] == "analyst":
            message["content"] = f"Analysis complete. {REDACTED}"


def make_nodes(monitor, service, tracker, observe, llm=None):
    def writer_compose(state):
        observe(tracker.before_writer)
        output = compose_answer(state, llm)
        # The tracker reads the analysis to finish its handoff records, so
        # it gets its ref now, before the text is dropped.
        observe(tracker.remember_analysis, state)
        minimize_state(state, monitor.provenance)
        state["transmission_request"] = {
            "requested": bool(output.should_transmit_externally),
            "declared_sensitive": bool(state.get("analysis_contains_sensitive_data", False)),
            "destination": "external",
        }
        return state

    def transmission_gate(state):
        request = state.get("transmission_request") or {}
        if not request.get("requested") or state.get("pending_action"):
            return state
        decision = tools.evaluate_send(monitor, "writer", request["declared_sensitive"])
        pending = service.gate(monitor, decision, state["final_output"], request["destination"])
        state["pending_action"] = pending
        state["governance_events"].append({
            "step": len(state["governance_events"]) + 1,
            "agent_role": "writer",
            "tool_name": "send_result",
            "decision": pending["final_decision"],
            "risk_score": decision.to_dict()["risk_score"],
            "source": pending["decided_by"],
            "reason": decision.reason if pending["decided_by"] != "flow_rule" else
            f"Flow rule(s) escalated for review: {', '.join(pending['flow_rules_fired'])}",
            "blocked": pending["final_decision"] not in ALLOWED_DECISIONS,
        })
        return state

    def human_approval(state):
        pending = state.get("pending_action")
        if not pending or not pending["needs_review"]:
            return state
        approval = state.get("approval")
        if approval and approval.get("action_id") == pending["action_id"]:
            return state
        # Everything above re-runs on resume, so it must stay side-effect free.
        response = interrupt(service.review_request(pending, state["final_output"]))
        state["approval"] = service.resolve(monitor, pending, response, state["final_output"])
        return state

    def transmission_execute(state):
        pending = state.get("pending_action")
        if pending:
            _execute(state, pending)
        state["messages"].append({"role": "writer", "content": "Final answer produced."})
        observe(tracker.after_writer, state)
        return state

    def _execute(state, pending):
        approval = state.get("approval")
        permitted, reason = service.authorize(pending, approval, state["final_output"])
        decision = next((d for d in monitor.decisions if d.event_id == pending["decision_event_id"]),
                        None)
        executed = False
        if not permitted:
            outcome = "refused"
        elif not service.ledger.claim(pending["action_id"], pending["run_id"], pending["tool"],
                                      pending["action_digest"]):
            outcome, reason = "duplicate_prevented", (
                f"already claimed (ledger status: {service.ledger.status(pending['action_id'])})")
        else:
            try:
                tools.execute_send(monitor, decision or _DecisionRef(
                    pending["decision_event_id"], pending["agent_role"]),
                    state["final_output"], pending["destination"])
            except Exception:
                service.ledger.finish(pending["action_id"], "failed")
                service.record_execution(monitor, pending, "failed", "tool_call_raised", approval)
                raise
            service.ledger.finish(pending["action_id"], "executed")
            outcome, executed = "executed", True
            if decision is not None and not decision.allowed:
                # Executed after approval: it's now part of what ran.
                monitor.trajectory.append(decision.action)

        service.record_execution(monitor, pending, outcome, reason, approval)
        if decision is not None:
            decision.execution = {"outcome": outcome, "executed": executed, "reason": reason,
                                  "approval": (approval or {}).get("outcome")}
        state["governance_events"][-1]["blocked"] = not executed
        state["trajectory"] = list(monitor.trajectory)
        if not executed and outcome != "duplicate_prevented":
            state["task_halted"] = True
            state["halt_reason"] = f"External transmission not executed: {reason}"

    return {
        "writer_compose": writer_compose,
        "transmission_gate": transmission_gate,
        "human_approval": human_approval,
        "transmission_execute": transmission_execute,
    }


def _config(thread_id):
    if not thread_id:
        raise ValueError("A thread_id is required to run or resume an approval graph")
    return {"configurable": {"thread_id": thread_id}}


def _finish(app, thread_id, result):
    service = getattr(app, "approval_service", None)
    if "__interrupt__" not in result and service is not None and service.purge_completed:
        app.checkpointer.delete_thread(thread_id)
    return result


def start(app, state, thread_id):
    """Runs until the task finishes or pauses for review. State is only
    checkpointed when it pauses or finishes."""
    return _finish(app, thread_id, app.invoke(state, _config(thread_id), durability="exit"))


def pending_review(app, thread_id):
    """The review request waiting on this thread, or None."""
    snapshot = app.get_state(_config(thread_id))
    interrupts = list(getattr(snapshot, "interrupts", ()) or ())
    if not interrupts:
        for task in snapshot.tasks or ():
            interrupts.extend(task.interrupts or ())
    return interrupts[0].value if interrupts else None


def submit_review(app, thread_id, response):
    """Resumes the paused thread with the reviewer's response. Refuses if
    nothing is waiting: resuming a thread without a pending interrupt
    would start a fresh run of the whole graph instead."""
    if pending_review(app, thread_id) is None:
        raise NoPendingApproval(f"No review is waiting on thread {thread_id!r}")
    if response is None:
        # LangGraph 1.2 fails internally on Command(resume=None); refuse it
        # here so the review simply stays pending.
        raise ValueError("A review response is required")
    return _finish(app, thread_id, app.invoke(Command(resume=response), _config(thread_id),
                                              durability="exit"))
