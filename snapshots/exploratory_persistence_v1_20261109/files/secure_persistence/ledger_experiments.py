"""
Experiment 5 (in-process part): duplicate-send prevention. The
cross-process scenarios (crash right after the send, retry after a
restart) come from experiment 1's R5 trials.

Scenarios, each on a fresh run paused for approval:
  L1 first_approval      approve once                                     expect 1
  L2 repeated_approval   approve; approve again through the review helper;
                         then resume the raw graph with the same response  expect 1
  L3 double_click        two reviewers' threads approve at the same moment expect 1
  L4 duplicate_resume    approve; then a raw Command(resume) on the thread  expect 1
  L5 reject              reject; then a raw Command(resume)                 expect 0
"""
import os
import shutil
import tempfile
import threading

from langgraph.types import Command

import harness
from agents.approval_flow import NoPendingApproval, pending_review, submit_review
from configurations import CONFIGS, ExperimentStore, minimization

SCENARIOS = {"L1_first_approval": 1, "L2_repeated_approval": 1, "L3_double_click": 1,
             "L4_duplicate_resume": 1, "L5_reject": 0}
FIELDS = ["config", "scenario", "trial", "seed", "status", "error", "paused",
          "attempts", "delivered", "expected", "duplicate", "at_most_once",
          "second_submit", "raw_resume", "thread_errors", "ledger_status"]


def _response(request, decision="approve", reviewer="experiment"):
    return {"action_id": request["action_id"], "action_digest": request["action_digest"],
            "decision": decision, "reviewer": reviewer}


def _raw_resume(app, thread, response):
    try:
        app.invoke(Command(resume=response), {"configurable": {"thread_id": thread}}, durability="exit")
        return "returned"
    except Exception as e:
        return f"raised {type(e).__name__}"


def run_trial(config, scenario, trial, seed):
    base = tempfile.mkdtemp(prefix=f"sp_led_{config}_")
    row = {"config": config, "scenario": scenario, "trial": trial, "seed": seed,
           "status": "complete", "error": "", "expected": SCENARIOS[scenario]}
    store = None
    try:
        c = harness.canaries(seed)
        tx = os.path.join(base, "transmissions.jsonl")
        harness.install_mcp(c, tx)
        store = ExperimentStore(config, os.path.join(base, "store"))
        thread, logs = f"thread-{seed}", os.path.join(base, "logs")
        with minimization(CONFIGS[config]["minim"]):
            app, result = harness.run_to_pause(store, c, thread, logs)
            row["paused"] = "__interrupt__" in result
            request = pending_review(app, thread)
            if scenario == "L3_double_click":
                barrier, errors = threading.Barrier(2), []

                def click():
                    barrier.wait()
                    try:
                        submit_review(harness.build_app(store, "click", logs), thread, _response(request))
                    except NoPendingApproval:
                        errors.append("no_pending")
                    except Exception as e:
                        errors.append(type(e).__name__)
                threads = [threading.Thread(target=click) for _ in range(2)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=120)
                row["thread_errors"] = ";".join(errors)
            else:
                decision = "reject" if scenario == "L5_reject" else "approve"
                submit_review(app, thread, _response(request, decision))
                if scenario == "L2_repeated_approval":
                    try:
                        submit_review(app, thread, _response(request))
                        row["second_submit"] = "accepted"
                    except NoPendingApproval:
                        row["second_submit"] = "no_pending_approval"
                if scenario in ("L2_repeated_approval", "L4_duplicate_resume", "L5_reject"):
                    row["raw_resume"] = _raw_resume(harness.build_app(store, "raw", logs), thread,
                                                    _response(request, decision))
            row["ledger_status"] = store.ledger.status(request["action_id"])
        row["attempts"] = harness.count_events(tx, "attempt")
        row["delivered"] = harness.count_events(tx, "delivered")
        row["duplicate"] = row["delivered"] > 1
        row["at_most_once"] = row["delivered"] <= 1
    except Exception as e:
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if store is not None:
            store.close()
        shutil.rmtree(base, ignore_errors=True)
    return row
