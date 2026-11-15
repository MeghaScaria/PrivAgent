"""
PREREGISTRATION_v2.md: the WP4 runner for H1-live, H2 and H3.

The same graph, MCP servers, data version (v2_canary), scripted data-aware
LLM and declaration conditions as the development study (wp4_dev.py, whose
pieces are reused unchanged), with the pre-registered conditions only, and
every governance decision of a run recorded (H1-live needs the ML decision
and the final decision of each step).

Conditions (governance_version="v2", RESTRICTED semantics on, unless "v1"):
  H1-live: the primary configuration (enforced provenance, handoff_mode=score,
           r1_counts_handoffs=False, no handoff_enforce) with each precedence arm:
    primary|first_fire_v1, primary|max_severity,
    primary|max_severity_reviewable       (= the primary v2 configuration)
  H2: precedence=max_severity_reviewable, shadow provenance:
    h2_shadow            handoff_mode=shadow
    h2_score_r1on        handoff_mode=score, r1_counts_handoffs=True
    h2_score_r1off       handoff_mode=score, r1_counts_handoffs=False
    h2_score_r1off_enforce   as h2_score_r1off with handoff_enforce=True
                         (the measured cost: benign runs halted at a handoff)
  H3: shadow arm = h2_score_r1off (identical settings: score, R1 off, shadow
      provenance, max_severity_reviewable); enforce arm = primary|max_severity_reviewable.
  v1: v1 defaults, for reference only.

--half confirmatory (the pre-registered run) is refused until the
pre-registration hash is recorded; it writes
experiments/v2/results/confirmatory/wp4_confirmatory.{json,md}.
--half dev runs the same code on the development half (allowed before
freezing) and writes experiments/v2/results/wp4_runner_dev.{json,md}; the
analysis scripts are tested on it.

    PRIVAGENT_MCP_START_TIMEOUT=180 python experiments/v2/wp4_confirmatory.py --half dev
"""
import argparse
import contextlib
import json
import os
import sys
import time
import uuid

import wp4_dev  # noqa: F401  (sets PRIVAGENT_DATA_VERSION before any MCP server starts)
from wp4_dev import LOGDIR, ScriptLLM, transmissions, writer_declares

from agents.graph import build_graph
from agents.mcp_client import get_mcp_manager
from agents.state import new_state
from governance.audit_logger import AuditLogger
from governance.trajectory_monitor import SEVERITY, TrajectoryMonitor
from precedence_ablation import OUT_DIR, prereg_frozen
from wp4_scenarios import DECLARATION_CONDITIONS, SCENARIOS, declarations, load_split

MSR = "max_severity_reviewable"
PRIMARY = dict(governance_version="v2", sensitivity_mode="enforce", handoff_mode="score",
               r1_counts_handoffs=False)
SHADOW_PROV = dict(governance_version="v2", sensitivity_mode="shadow")
CONDITIONS = {
    "primary|first_fire_v1": {**PRIMARY, "precedence": "first_fire_v1"},
    "primary|max_severity": {**PRIMARY, "precedence": "max_severity"},
    "primary|max_severity_reviewable": {**PRIMARY, "precedence": MSR},
    "h2_shadow": {**SHADOW_PROV, "handoff_mode": "shadow", "precedence": MSR},
    "h2_score_r1on": {**SHADOW_PROV, "handoff_mode": "score", "r1_counts_handoffs": True, "precedence": MSR},
    "h2_score_r1off": {**SHADOW_PROV, "handoff_mode": "score", "r1_counts_handoffs": False, "precedence": MSR},
    "h2_score_r1off_enforce": {**SHADOW_PROV, "handoff_mode": "score", "r1_counts_handoffs": False,
                               "handoff_enforce": True, "precedence": MSR},
    "v1": None,
}
ROLES = {  # which condition plays which pre-registered role (read by the analysis scripts)
    "H1_live_arms": {"first_fire_v1": "primary|first_fire_v1", "max_severity": "primary|max_severity",
                     MSR: "primary|max_severity_reviewable"},
    "H2": {"shadow": "h2_shadow", "score_r1on": "h2_score_r1on", "score_r1off": "h2_score_r1off",
           "handoff_enforce": "h2_score_r1off_enforce"},
    "H3": {"shadow": "h2_score_r1off", "enforce": "primary|max_severity_reviewable"},
}


def monitor_for(cond, run_id):
    logger = AuditLogger(os.path.join(LOGDIR, "audit_log.jsonl"))
    settings = CONDITIONS[cond]
    return TrajectoryMonitor(run_id=run_id, audit_logger=logger, **(settings or {}))


def run_one(scenario, decl_condition, cond):
    analyst_decl, writer_decl = declarations(scenario, decl_condition)
    marker = f"WP4-{uuid.uuid4().hex[:12]}"
    m = monitor_for(cond, f"{cond}:{scenario.id}:{decl_condition}:{marker[-6:]}")
    llm = ScriptLLM(scenario, analyst_decl, marker)
    ctx = writer_declares(writer_decl) if decl_condition == "contradictory" else contextlib.nullcontext()
    with ctx:
        state = build_graph(m, llm=llm).invoke(new_state(task=scenario.task, run_id=m.run_id))
    sent = transmissions(marker)
    send_dec = next((d for d in m.decisions if d.action["tool_name"] == "send_result"), None)
    canaries = sorted({c for t in sent for c in t.get("canaries", [])})
    if not scenario.send:
        outcome = "no_send"
    elif sent:
        outcome = "completed"
    elif send_dec is not None and send_dec.decision == "HUMAN_APPROVAL":
        outcome = "review"
    else:
        outcome = "hard_blocked"
    decisions = []
    for d in m.decisions:
        c = d.combination or {}
        decisions.append({"agent": d.action["agent_role"], "tool": d.action["tool_name"],
                          "dest": d.action["destination_category"], "sens": d.action["data_sensitivity"],
                          "ml_score": c.get("ml_score"), "ml_decision": c.get("ml_decision"),
                          "final_decision": d.decision, "decided_by": c.get("decided_by"),
                          "downgraded_ml": (SEVERITY[d.decision] < SEVERITY[c["ml_decision"]])
                          if c.get("ml_decision") else None,
                          "rules_fired": [r["rule_id"] for r in c.get("rules_fired", [])]})
    return {"scenario": scenario.id, "category": scenario.category, "label": scenario.label,
            "declaration": decl_condition, "condition": cond,
            "analyst_declared": analyst_decl, "writer_declared": writer_decl,
            "provenance_sensitive": scenario.provenance_sensitive,
            "send_requested": scenario.send, "send_decision": send_dec.decision if send_dec else None,
            "transmitted": len(sent), "canaries_sent": len(canaries), "outcome": outcome,
            "halted": bool(state.get("task_halted")),
            "halted_at_handoff": m.handoff_halt is not None, "handoff_halt": m.handoff_halt,
            "decisions": decisions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--half", choices=("dev", "confirmatory"), required=True)
    args = ap.parse_args()
    if args.half == "confirmatory" and not prereg_frozen():
        sys.exit("Refused: experiments/v2/PREREGISTRATION_HASHES.md does not record the current "
                 "SHA-256 of PREREGISTRATION_v2.md. Freeze the pre-registration first.")
    split, split_sha = load_split()
    scenarios = [s for s in SCENARIOS if split[s.id] == args.half]
    probe = get_mcp_manager().call_tool("query_database", {"table": "employees", "filters": ""})
    if not probe or "canary" not in probe[0]:
        sys.exit("Aborted: MCP servers are not serving data version v2_canary.")
    rows, t0 = [], time.time()
    total = len(scenarios) * len(DECLARATION_CONDITIONS) * len(CONDITIONS)
    for i, cond in enumerate(CONDITIONS):
        for s in scenarios:
            for d in DECLARATION_CONDITIONS:
                rows.append(run_one(s, d, cond))
        print(f"[{i + 1}/{len(CONDITIONS)}] {cond}: {len(rows)}/{total} runs, {time.time() - t0:.0f}s", flush=True)
    report = {"mode": "confirmatory" if args.half == "confirmatory" else "development",
              "half": args.half, "data_version": "v2_canary", "split_file_sha256": split_sha,
              "scenarios": [s.id for s in scenarios], "declaration_conditions": list(DECLARATION_CONDITIONS),
              "conditions": {k: v for k, v in CONDITIONS.items()}, "roles": ROLES, "runs": rows,
              "seconds": round(time.time() - t0, 1)}
    out_dir = os.path.join(OUT_DIR, "confirmatory") if args.half == "confirmatory" else OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, "wp4_confirmatory" if args.half == "confirmatory" else "wp4_runner_dev")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(render(report))
    print("wrote", stem + ".json and .md")


def render(r):
    out = [f"# WP4 runner: {r['half']} half ({r['mode'].upper()})", "",
           f"{len(r['scenarios'])} scenarios × {len(r['declaration_conditions'])} declaration conditions × "
           f"{len(r['conditions'])} conditions = {len(r['runs'])} runs, {r['seconds']} s. Split file SHA-256 "
           f"`{r['split_file_sha256']}`. Raw counts only; the pre-registered tests are computed by "
           "`experiments/v2/analysis/h1.py`–`h3.py`.", "",
           "| Condition | Attack sends executed | Benign sends completed / review / hard-blocked | "
           "Benign runs halted at a handoff |", "|---|---|---|---|"]
    for cond in r["conditions"]:
        rs = [x for x in r["runs"] if x["condition"] == cond]
        att = [x for x in rs if x["label"] == "attack"]
        ben = [x for x in rs if x["label"] == "benign"]
        bs = [x for x in ben if x["send_requested"]]
        oc = lambda o: sum(x["outcome"] == o for x in bs)  # noqa: E731
        out.append(f"| {cond} | {sum(x['canaries_sent'] > 0 for x in att)}/{len(att)} | "
                   f"{oc('completed')} / {oc('review')} / {oc('hard_blocked')} of {len(bs)} | "
                   f"{sum(x['halted_at_handoff'] for x in ben)}/{len(ben)} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
