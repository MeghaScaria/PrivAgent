"""
One step of a recovery or ledger trial, in its own process. Prints one
JSON line per event on stdout.

  start         run the workload to its approval pause, report, then wait to be killed
  review        open the store, recover the pending request, approve or reject it
  resume_again  try to resume after completion: the helper, then a raw Command(resume)

--fault injects a crash (os._exit) in a review step:
  before_approval  inside response validation, before the decision is recorded
  after_approval   after the decision is recorded, before execution is authorized
  after_send       right after the external send returns, before the ledger is updated
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402  (sets up the project path)

import agents.tools as tools_module  # noqa: E402
from agents.approval_flow import NoPendingApproval, pending_review, submit_review  # noqa: E402
from langgraph.types import Command  # noqa: E402

from configurations import CONFIGS, ExperimentStore, minimization  # noqa: E402

FAULT_EXIT = {"before_approval": 70, "after_approval": 71, "after_send": 72}


def emit(**fields):
    print(json.dumps(fields), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["start", "review", "resume_again"])
    p.add_argument("--config", required=True, choices=sorted(CONFIGS))
    p.add_argument("--dir", required=True)
    p.add_argument("--thread", required=True)
    p.add_argument("--seed", required=True)
    p.add_argument("--tx", required=True)
    p.add_argument("--decision", default="approve")
    p.add_argument("--fault", default="none", choices=["none", *FAULT_EXIT])
    args = p.parse_args()

    c = harness.canaries(args.seed)
    harness.install_mcp(c, args.tx)
    log_dir = os.path.join(args.dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    t_open = time.perf_counter()
    store = ExperimentStore(args.config, os.path.join(args.dir, "store"))
    with minimization(CONFIGS[args.config]["minim"]):
        if args.command == "start":
            _, result = harness.run_to_pause(store, c, args.thread, log_dir)
            emit(event="paused" if "__interrupt__" in result else "not_paused",
                 action_id=(result.get("pending_action") or {}).get("action_id"),
                 delivered=harness.count_events(args.tx, "delivered"))
            while True:
                time.sleep(1)

        if args.command == "review":
            t_store = time.perf_counter()
            app = harness.build_app(store, "recovery", log_dir)
            t_app = time.perf_counter()
            request = pending_review(app, args.thread)
            t_read = time.perf_counter()
            emit(event="recovered", found=request is not None,
                 action_id=request and request["action_id"],
                 payload_matches=request and request["payload_matches_gated_action"],
                 store_open_s=t_store - t_open, app_build_s=t_app - t_store,
                 checkpoint_read_s=t_read - t_app, recovery_s=t_read - t_open)
            if request is None:
                return
            if args.fault == "before_approval":
                store.service.resolve = lambda *a, **k: os._exit(FAULT_EXIT["before_approval"])
            elif args.fault == "after_approval":
                store.service.authorize = lambda *a, **k: os._exit(FAULT_EXIT["after_approval"])
            elif args.fault == "after_send":
                original = tools_module.execute_send

                def send_then_crash(*a, **k):
                    original(*a, **k)
                    os._exit(FAULT_EXIT["after_send"])
                tools_module.execute_send = send_then_crash
            result = submit_review(app, args.thread, {
                "action_id": request["action_id"], "action_digest": request["action_digest"],
                "decision": args.decision, "reviewer": "experiment"})
            approval = result.get("approval") or {}
            emit(event="reviewed", approval=approval.get("outcome"),
                 halted=bool(result.get("task_halted")),
                 ledger=store.ledger.status(request["action_id"]),
                 delivered=harness.count_events(args.tx, "delivered"))
            return

        if args.command == "resume_again":
            outcome = {}
            try:
                submit_review(harness.build_app(store, "again", log_dir), args.thread,
                              {"decision": "approve"})
                outcome["helper"] = "accepted"
            except NoPendingApproval:
                outcome["helper"] = "no_pending_approval"
            try:
                harness.build_app(store, "again-raw", log_dir).invoke(
                    Command(resume={"decision": "approve"}),
                    {"configurable": {"thread_id": args.thread}}, durability="exit")
                outcome["raw_resume"] = "returned"
            except Exception as e:
                outcome["raw_resume"] = f"raised {type(e).__name__}"
            emit(event="resumed_again", delivered=harness.count_events(args.tx, "delivered"),
                 **outcome)


if __name__ == "__main__":
    main()
