"""
Replays every Attack Lab scenario against the real MCP servers and
reports, step by step, what the ML risk model decided and whether a
policy rule overrode it.

Each scenario runs twice:
  full     - ML model + policy engine, exactly as the dashboard runs it.
  ml_only  - the policy engine switched off, to show what the model
             catches on its own. (A policy block changes the trajectory,
             since blocked actions aren't added to it, so later ML
             scores can differ between the two modes.)

Decisions go to a temporary audit log, not logs/audit_log.jsonl.

Usage:
    python experiments/attack_lab_replay.py
"""
import os
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from governance.attack_scenarios import SCENARIOS, run_scenario
from governance.audit_logger import AuditLogger
from governance.policy_engine import PolicyEngine
from governance.trajectory_monitor import TrajectoryMonitor

RESULTS_DIR = os.path.join(BASE_DIR, "experiments", "results")
ALLOWED = ("AUTONOMOUS", "RESTRICTED")


class NoPolicy(PolicyEngine):
    def evaluate(self, trajectory_prefix, candidate_action):
        return None, None


def replay(scenario_key, mode, audit_logger):
    monitor = TrajectoryMonitor(
        model_type="trajectory", task_type="financial_research", agent_count=3,
        audit_logger=audit_logger,
        policy_engine=NoPolicy() if mode == "ml_only" else PolicyEngine(),
    )
    steps = run_scenario(scenario_key, monitor)
    out = []
    for step in steps:
        d = step["decision"]
        out.append({
            "description": step["description"],
            "tool": d["action"]["tool_name"],
            "risk": d["risk_score"],
            "ml_decision": monitor.controller.decide(d["risk_score"]),
            "final": d["decision"],
            "source": d["source"],
            "executed": not step["blocked"],
        })
    return out


def caught_by(steps):
    """Which layer stopped at least one step: 'ml', 'policy', 'both' or None."""
    ml = any(s["ml_decision"] not in ALLOWED for s in steps)
    policy = any(s["source"] == "policy_engine" and s["final"] not in ALLOWED for s in steps)
    return {(True, True): "both", (True, False): "ml", (False, True): "policy"}.get((ml, policy))


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    audit_logger = AuditLogger(os.path.join(tempfile.mkdtemp(), "audit_log.jsonl"))
    md = ["# Attack Lab replay (real MCP servers)", "",
          "| scenario | attack? | full: stopped by | full: outcome | ML-only: outcome |",
          "|---|---|---|---|---|"]
    details = []
    for key, scenario in SCENARIOS.items():
        full = replay(key, "full", audit_logger)
        ml_only = replay(key, "ml_only", audit_logger)
        stopped_full = any(not s["executed"] for s in full)
        stopped_ml = any(not s["executed"] for s in ml_only)

        def outcome(stopped):
            if scenario["is_attack"]:
                return "caught" if stopped else "MISSED"
            return "false alarm" if stopped else "clean"

        md.append(f"| {key} | {'yes' if scenario['is_attack'] else 'no'} | "
                  f"{caught_by(full) or '-'} | {outcome(stopped_full)} | {outcome(stopped_ml)} |")
        details += ["", f"## {key}", "",
                    "| # | step | ML-only risk | ML-only decision | full risk | ML decision | final | decided by |",
                    "|---|---|---|---|---|---|---|---|"]
        for i, (f, m) in enumerate(zip(full, ml_only), 1):
            details.append(
                f"| {i} | {f['description']} | {m['risk']:.3f} | {m['ml_decision']} | "
                f"{f['risk']:.3f} | {f['ml_decision']} | {f['final']} | "
                f"{'policy' if f['source'] == 'policy_engine' else 'ML'} |")
    text = "\n".join(md + details) + "\n"
    with open(os.path.join(RESULTS_DIR, "attack_lab_replay.md"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
