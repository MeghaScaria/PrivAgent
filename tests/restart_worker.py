"""
One step of an approval run, in its own process, for
tests/test_restart_recovery.py. Each process starts its own MCP
servers, so "sent" is the number of transmissions this process's
external server received.

  start          run until the review pause, report, then wait to be killed
  review         open the store, recover the pending review, answer it
  resume_again   try to resume a thread that's already been answered

Prints one JSON line per event on stdout.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.types import Command

import tests.test_handoff_instrumentation as h
from agents.approval_flow import NoPendingApproval, pending_review, start, submit_review
from agents.graph import build_graph
from agents.mcp_client import get_mcp_manager
from agents.state import new_state
from governance.approval import SENSITIVE_CROSSED_TO_EXTERNAL
from governance.audit_logger import AuditLogger
from governance.checkpoint_store import DevApprovalStore
from governance.trajectory_monitor import TrajectoryMonitor

TASK = "Email the HR summary to our partner jane.doe@example.com"


def emit(**fields):
    print(json.dumps(fields), flush=True)


def sent(marker):
    log = get_mcp_manager().call_tool("get_transmission_log", {})
    return sum(1 for t in log if t["payload_preview"].startswith(marker))


def build(store, run_id, marker):
    monitor = TrajectoryMonitor(run_id=run_id, audit_logger=AuditLogger(
        os.path.join(store.directory, "audit_log.jsonl")))
    llm = h.FakeLLM(plan=h.plan(["hr"]), analysis=h.analysis(False),
                    writer={"final_answer": marker, "should_transmit_externally": True})
    return build_graph(monitor, llm=llm, approvals=store.service, checkpointer=store.checkpointer)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["start", "review", "resume_again"])
    p.add_argument("--store", required=True)
    p.add_argument("--thread", required=True)
    p.add_argument("--marker", required=True)
    p.add_argument("--decision", default="approve")
    p.add_argument("--crash-after-send", action="store_true")
    args = p.parse_args()

    store = DevApprovalStore(args.store, flow_rules=[SENSITIVE_CROSSED_TO_EXTERNAL])
    app = build(store, f"restart_{args.marker[-6:]}", args.marker)

    if args.command == "start":
        result = start(app, new_state(task=TASK, run_id=f"restart_{args.marker[-6:]}"), args.thread)
        emit(event="paused" if "__interrupt__" in result else "finished",
             action_id=(result.get("pending_action") or {}).get("action_id"),
             sent=sent(args.marker), pid=os.getpid())
        while True:  # stay alive until the test kills this process
            time.sleep(1)

    if args.command == "review":
        request = pending_review(app, args.thread)
        emit(event="recovered", found=request is not None,
             action_id=request and request["action_id"],
             payload_matches=request and request["payload_matches_gated_action"],
             sent_before=sent(args.marker))
        if args.crash_after_send:
            def crash(action_id, status):
                emit(event="crashing", sent=sent(args.marker))
                os._exit(3)
            store.service.ledger.finish = crash
        result = submit_review(app, args.thread, {
            "action_id": request["action_id"], "action_digest": request["action_digest"],
            "decision": args.decision, "reviewer": "restart-test"})
        emit(event="reviewed", sent=sent(args.marker), halted=result["task_halted"],
             approval=result["approval"]["outcome"],
             ledger=store.ledger.status(request["action_id"]))
        return

    if args.command == "resume_again":
        outcome = {}
        try:
            submit_review(app, args.thread, {"decision": "approve"})
            outcome["helper"] = "accepted"
        except NoPendingApproval:
            outcome["helper"] = "no_pending_approval"
        try:
            app.invoke(Command(resume={"decision": "approve"}),
                       {"configurable": {"thread_id": args.thread}})
            outcome["raw_resume"] = "returned"
        except Exception as e:
            outcome["raw_resume"] = f"raised {type(e).__name__}"
        emit(event="resumed_again", sent=sent(args.marker), **outcome)


if __name__ == "__main__":
    main()
