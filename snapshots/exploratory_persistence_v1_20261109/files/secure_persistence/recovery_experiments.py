"""
Experiment 1: crash-recovery reliability (and the cross-process crash
scenarios of experiment 5).

Every trial runs in its own temporary directory with its own store,
synthetic MCP transmission log and audit logs. Process 1 runs the
workload until it pauses for approval and is then hard-killed. Later
processes recover the pending request and decide it, some with an
injected crash (os._exit) at a precise point.

Scenarios (expected deliveries with a working ledger):
  R1 pause_crash_approve     kill at pause; approve; duplicate resume       1
  R2 pause_crash_reject      kill at pause; reject; duplicate resume        0
  R3 crash_before_approval   reviewer process dies validating the response;
                             new process recovers and approves              1
  R4 crash_after_approval    dies after the decision, before execution;
                             new process recovers and approves              1
  R5 crash_after_send        dies right after the external send, before the
                             ledger update; new process recovers and
                             approves again (retry after restart)           1
"""
import os
import random
import shutil
import tempfile

from procs import Proc, run

SCENARIOS = {
    "R1_pause_crash_approve": {"decision": "approve", "fault": None, "expected": 1, "again": True},
    "R2_pause_crash_reject": {"decision": "reject", "fault": None, "expected": 0, "again": True},
    "R3_crash_before_approval": {"decision": "approve", "fault": "before_approval", "expected": 1},
    "R4_crash_after_approval": {"decision": "approve", "fault": "after_approval", "expected": 1},
    "R5_crash_after_send": {"decision": "approve", "fault": "after_send", "expected": 1},
}
FIELDS = ["config", "scenario", "trial", "seed", "status", "error",
          "paused", "pending_recovered", "payload_matches", "first_review_exit",
          "first_review_approval", "second_recovered", "second_review_approval",
          "delivered_total", "attempts_total", "expected_deliveries", "duplicate", "rejected_sent",
          "correct_outcome", "ledger_status", "again_helper", "again_raw",
          "store_open_s", "app_build_s", "checkpoint_read_s", "recovery_s"]


def _count(tx, event):
    import json
    if not os.path.exists(tx):
        return 0
    with open(tx, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip() and json.loads(line)["event"] == event)


def run_trial(config, scenario, trial, seed, keep_dir=False):
    spec = SCENARIOS[scenario]
    base = tempfile.mkdtemp(prefix=f"sp_rec_{config}_")
    tx = os.path.join(base, "transmissions.jsonl")
    thread = f"thread-{seed}"
    common = ["--config", config, "--dir", base, "--thread", thread, "--seed", str(seed), "--tx", tx]
    row = {"config": config, "scenario": scenario, "trial": trial, "seed": seed,
           "status": "complete", "error": "", "expected_deliveries": spec["expected"]}
    try:
        starter = Proc("worker.py", "start", *common)
        first = starter.next_event()
        starter.kill()
        row["paused"] = bool(first and first["event"] == "paused")
        if not row["paused"]:
            raise RuntimeError(f"workload did not pause: {first}")
        fault = ["--fault", spec["fault"]] if spec["fault"] else []
        events, code = run("worker.py", "review", *common, "--decision", spec["decision"], *fault)
        recovered = next((e for e in events if e["event"] == "recovered"), {})
        reviewed = next((e for e in events if e["event"] == "reviewed"), {})
        row.update({
            "pending_recovered": bool(recovered.get("found")) and recovered.get("action_id") == first["action_id"],
            "payload_matches": recovered.get("payload_matches"),
            "first_review_exit": code,
            "first_review_approval": reviewed.get("approval"),
            "store_open_s": recovered.get("store_open_s"), "app_build_s": recovered.get("app_build_s"),
            "checkpoint_read_s": recovered.get("checkpoint_read_s"), "recovery_s": recovered.get("recovery_s"),
            "ledger_status": reviewed.get("ledger"),
        })
        if spec["fault"]:
            events2, _ = run("worker.py", "review", *common, "--decision", spec["decision"])
            rec2 = next((e for e in events2 if e["event"] == "recovered"), {})
            rev2 = next((e for e in events2 if e["event"] == "reviewed"), {})
            row["second_recovered"] = bool(rec2.get("found")) and rec2.get("action_id") == first["action_id"]
            row["second_review_approval"] = rev2.get("approval")
            row["ledger_status"] = rev2.get("ledger", row["ledger_status"])
        if spec.get("again"):
            ev3, _ = run("worker.py", "resume_again", *common)
            again = next((e for e in ev3 if e["event"] == "resumed_again"), {})
            row["again_helper"] = again.get("helper")
            row["again_raw"] = again.get("raw_resume")
        delivered = _count(tx, "delivered")
        row["delivered_total"] = delivered
        row["attempts_total"] = _count(tx, "attempt")
        row["duplicate"] = delivered > 1
        row["rejected_sent"] = delivered if spec["decision"] == "reject" else ""
        recovered_ok = row["pending_recovered"] and (not spec["fault"] or row.get("second_recovered"))
        row["correct_outcome"] = bool(recovered_ok) and delivered == spec["expected"]
    except Exception as e:  # recorded, never dropped
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if not keep_dir:
            shutil.rmtree(base, ignore_errors=True)
    return row


def plan(configs, n, seed=20261109):
    jobs = [(c, s, t) for c in configs for s in SCENARIOS for t in range(n)]
    random.Random(seed).shuffle(jobs)
    return [(c, s, t, f"{seed}-{c}-{s}-{t}") for c, s, t in jobs]
