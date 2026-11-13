"""
V2_PLAN.md WP2, DEVELOPMENT ONLY: shadow vs score on the live replay
scenarios, plus pseudo-action coverage against the synthetic training data.

Live replays (real MCP servers; nothing confirmatory, no held-out data):
  - Attack Lab: governance/attack_scenarios.py, 7 attacks + 1 benign. These
    replay scripted actions through tools._governed_call; no LangGraph run,
    so no handoff events are produced. They are included to show that.
  - E5: the 8 scenarios of experiments/approval_evaluation.py, run through
    the real graph with the scripted LLM, default graph ("current" config).

Modes compared, all governance_version="v2" (max_severity precedence,
RESTRICTED semantics), so the only difference is handoff handling:
  shadow         handoffs logged only (v1 behaviour for handoffs)
  score          handoffs scored as pseudo-actions, not enforced
  score_enforce  handoffs scored; BLOCKED / HUMAN_APPROVAL halts the run

Coverage: every live pseudo-action (role, tool, action_type, sensitivity,
destination) is looked up in the train split (seed 42) of the synthetic
generator. Combinations the frozen model never saw are flagged.

Writes experiments/v2/results/handoff_scoring_dev.{json,md}. Logs go to a
temporary directory (never logs/).

    PRIVAGENT_MCP_START_TIMEOUT=180 python experiments/v2/handoff_scoring_dev.py
"""
import collections
import json
import os
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import tests.test_handoff_instrumentation as h  # noqa: E402
from agents.graph import build_graph  # noqa: E402
from agents.mcp_client import get_mcp_manager  # noqa: E402
from agents.state import new_state  # noqa: E402
from agents.approval_flow import pending_review, start, submit_review  # noqa: E402
from experiments.approval_evaluation import SCENARIOS as E5_SCENARIOS  # noqa: E402
from governance.approval import SENSITIVE_CROSSED_TO_EXTERNAL, ApprovalService, ExecutionLedger  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from governance.attack_scenarios import SCENARIOS as LAB_SCENARIOS, run_scenario  # noqa: E402
from governance.audit_logger import AuditLogger  # noqa: E402
from governance.trajectory_monitor import ALLOWED_DECISIONS, TrajectoryMonitor  # noqa: E402
from precedence_ablation import OUT_DIR, build_sets, decode  # noqa: E402

# "v1" is the reference (v1 defaults); every other mode is governance_version="v2".
MODES = {"v1": None,
         "shadow": dict(handoff_mode="shadow"),
         "score": dict(handoff_mode="score"),
         "score_r1off": dict(handoff_mode="score", r1_counts_handoffs=False),
         "score_enforce": dict(handoff_mode="score", handoff_enforce=True),
         "score_enforce_r1off": dict(handoff_mode="score", handoff_enforce=True,
                                     r1_counts_handoffs=False)}
LOGDIR = tempfile.mkdtemp(prefix="handoff_dev_")


def monitor(run_id, mode):
    logger = AuditLogger(os.path.join(LOGDIR, "audit_log.jsonl"))
    if MODES[mode] is None:
        return TrajectoryMonitor(run_id=run_id, audit_logger=logger)
    return TrajectoryMonitor(run_id=run_id, governance_version="v2", audit_logger=logger,
                             **MODES[mode])


def combo(a):
    return (a["agent_role"], a["tool_name"], a["action_type"], int(a["data_sensitivity"]),
            a["destination_category"])


def decisions(m):
    return [{"tool": d.action["tool_name"], "role": d.action["agent_role"],
             "kind": "handoff" if any(e.get("score", {}).get("tool_event_id") == d.event_id
                                      for e in m.handoffs) else "tool",
             "decision": d.decision, "source": d.source, "risk": round(d.risk_score, 4)}
            for d in m.decisions]


def pseudo(m):
    return [e["score"]["pseudo_action"] for e in m.handoffs if "score" in e]


def run_lab(key, mode):
    m = monitor(f"lab_{mode}_{key}", mode)
    steps = run_scenario(key, m)
    caught = any(s.get("blocked") for s in steps)
    return {"outcome": ("caught" if caught else "MISSED") if LAB_SCENARIOS[key]["is_attack"]
            else ("false alarm" if caught else "clean"),
            "decisions": decisions(m), "pseudo_actions": pseudo(m), "handoff_events": len(m.handoffs)}


def sent_count(marker):
    log = get_mcp_manager().call_tool("get_transmission_log", {})
    return sum(1 for t in log if t["payload_preview"].startswith(marker))


def run_e5_approval(name, mode):
    """The same scenario through the approval graph (E5's flow rule
    enabled) with an approve-everything reviewer: was a review offered, and
    would approving it have executed the send?"""
    label, domains, table, declared, send = E5_SCENARIOS[name]
    marker = f"DEVA-{uuid.uuid4().hex[:12]}"
    m = monitor(f"e5a_{mode}_{name}", mode)
    llm = h.FakeLLM(plan=h.plan(domains, table=table), analysis=h.analysis(declared),
                    writer={"final_answer": marker, "should_transmit_externally": send})
    service = ApprovalService(ExecutionLedger(os.path.join(LOGDIR, f"{marker}.sqlite")),
                              flow_rules=[SENSITIVE_CROSSED_TO_EXTERNAL])
    app = build_graph(m, llm=llm, approvals=service, checkpointer=InMemorySaver())
    thread = f"t-{marker}"
    result = start(app, new_state(task=f"Scenario {name}", run_id=m.run_id), thread)
    offered = "__interrupt__" in result
    if offered:
        request = pending_review(app, thread)
        result = submit_review(app, thread, {"action_id": request["action_id"],
                                             "action_digest": request["action_digest"],
                                             "decision": "approve", "reviewer": "approve_all"})
    pending = result.get("pending_action") or {}
    return {"final_decision": pending.get("final_decision"), "decided_by": pending.get("decided_by"),
            "review_offered": offered, "sent_after_approve_all": sent_count(marker),
            "halted_before_send": bool(result.get("task_halted")) and not pending}


def run_e5(name, mode):
    label, domains, table, declared, send = E5_SCENARIOS[name]
    marker = f"DEV-{uuid.uuid4().hex[:12]}"
    m = monitor(f"e5_{mode}_{name}", mode)
    llm = h.FakeLLM(plan=h.plan(domains, table=table), analysis=h.analysis(declared),
                    writer={"final_answer": marker, "should_transmit_externally": send})
    state = build_graph(m, llm=llm).invoke(new_state(task=f"Scenario {name}", run_id=m.run_id))
    sent = sent_count(marker)
    send_dec = next((d for d in m.decisions if d.action["tool_name"] == "send_result"), None)
    return {"label": label, "send_requested": send, "transmitted": sent,
            "halted": bool(state.get("task_halted")), "halt_reason": state.get("halt_reason"),
            "send_decision": send_dec.decision if send_dec else None,
            "send_rules": [r["rule_id"] for r in send_dec.combination["rules_fired"]] if send_dec else [],
            "send_reason": send_dec.reason if send_dec else None,
            "decisions": decisions(m), "pseudo_actions": pseudo(m),
            "approval_graph": run_e5_approval(name, mode)}


def training_combos():
    train = build_sets(42, confirmatory=False)["train"]
    counts = collections.Counter()
    for row in train[["agent_role", "tool_name", "action_type", "data_sensitivity",
                      "destination_category"]].itertuples(index=False):
        counts[combo(decode(row._asdict()))] += 1
    return counts, len(train)


def main():
    report = {"mode": "development", "modes": list(MODES), "attack_lab": {}, "e5": {}}
    for key in LAB_SCENARIOS:
        report["attack_lab"][key] = {mode: run_lab(key, mode) for mode in MODES}
        print("lab", key, {m: r["outcome"] for m, r in report["attack_lab"][key].items()})
    for name in E5_SCENARIOS:
        report["e5"][name] = {mode: run_e5(name, mode) for mode in MODES}
        print("e5", name, {m: (r["send_decision"], r["transmitted"], r["halted"])
                           for m, r in report["e5"][name].items()})

    train_counts, train_rows = training_combos()
    coverage = {}
    for family in ("attack_lab", "e5"):
        for name, modes in report[family].items():
            for p in modes["score"]["pseudo_actions"]:  # same pseudo-actions in every score mode
                c = combo(p)
                entry = coverage.setdefault(json.dumps(c), {"combo": c, "live_count": 0, "scenarios": []})
                entry["live_count"] += 1
                if name not in entry["scenarios"]:
                    entry["scenarios"].append(f"{family}:{name}")
    for entry in coverage.values():
        entry["train_rows"] = train_counts.get(tuple(entry["combo"]), 0)
        entry["seen_in_training"] = entry["train_rows"] > 0
    report["coverage"] = {"train_split": "seed 42 train", "train_rows": train_rows,
                          "combinations": sorted(coverage.values(), key=lambda e: e["combo"])}

    os.makedirs(OUT_DIR, exist_ok=True)
    stem = os.path.join(OUT_DIR, "handoff_scoring_dev")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(render(report))
    print("wrote", stem + ".json and .md")


def render(r):
    modes = r["modes"]

    def reviewable(x):
        a = x["approval_graph"]
        if a["halted_before_send"]:
            return "no (halted before send)"
        if not x["send_requested"]:
            return "– (no send)"
        if a["review_offered"]:
            return f"**yes** ({a['decided_by']}); approve-all sent {a['sent_after_approve_all']}"
        return f"no ({a['final_decision']}, {a['decided_by']}); sent {a['sent_after_approve_all']}"

    out = ["# Handoff scoring: shadow vs score, R1 ablation (DEVELOPMENT)", "",
           "**Development run on the live replay scenarios only** (Attack Lab and E5, real MCP "
           "servers, scripted LLM). Nothing confirmatory. `v1` is the v1 reference; every other mode "
           "is governance_version=v2 (max_severity, RESTRICTED semantics) and differs only in handoff "
           "handling: `score` scores handoffs as pseudo-actions, `_enforce` halts on a BLOCKED or "
           "HUMAN_APPROVAL handoff, `_r1off` stops R1 from counting sensitive pseudo-actions.", "",
           "Columns: **Final decision / sent** come from the default graph (no approval workflow). "
           "**Reviewer could approve** comes from the same scenario run through the approval graph "
           "(E5's flow rule on) with an approve-everything reviewer: whether a review was offered, "
           "and how many transmissions approving it produced.", "",
           "## E5 scenarios", ""]
    for name, by_mode in r["e5"].items():
        first = next(iter(by_mode.values()))
        out += [f"### `{name}` ({first['label']}, send requested: {'yes' if first['send_requested'] else 'no'})", "",
                "| Mode | Handoff pseudo-actions | Final send decision (rules) | Sent | Halted | Reviewer could approve |",
                "|---|---|---|---|---|---|"]
        for mode in modes:
            x = by_mode[mode]
            ps = [d for d in x["decisions"] if d["kind"] == "handoff"]
            pcell = ", ".join(f"{d['role']}:{d['decision']}" for d in ps) or "–"
            send = (f"{x['send_decision']} ({','.join(x['send_rules']) or 'ML'})" if x["send_decision"]
                    else ("halted before send" if x["halted"] and x["send_requested"] else "– (no send)"))
            out.append(f"| {mode} | {pcell} | {send} | {x['transmitted']} | {'yes' if x['halted'] else 'no'} | "
                       f"{reviewable(x)} |")
        out.append("")
    out += ["## Changes relative to v2 shadow", ""]
    keys = ("send_decision", "transmitted", "halted")
    any_change = False
    for name, by_mode in r["e5"].items():
        base = by_mode["shadow"]
        for mode in modes:
            if mode in ("v1", "shadow"):
                continue
            x = by_mode[mode]
            diffs = [f"{k} {base[k]} → {x[k]}" for k in keys if x[k] != base[k]]
            if x["approval_graph"]["review_offered"] != base["approval_graph"]["review_offered"]:
                diffs.append(f"review offered {base['approval_graph']['review_offered']} → "
                             f"{x['approval_graph']['review_offered']}")
            if diffs:
                any_change = True
                out.append(f"- `{name}` / `{mode}`: " + "; ".join(diffs))
    if not any_change:
        out.append("- none")
    out += ["", "## Attack Lab", "",
            "| Scenario | " + " | ".join(modes) + " | Handoff events (score) | Decisions identical across modes |",
            "|---|" + "---|" * (len(modes) + 2)]
    for key, by_mode in r["attack_lab"].items():
        same = all(by_mode[m]["decisions"] == by_mode["shadow"]["decisions"] for m in modes if m != "v1")
        out.append(f"| {key} | " + " | ".join(by_mode[m]["outcome"] for m in modes)
                   + f" | {by_mode['score']['handoff_events']} | {'yes (v2 modes)' if same else 'NO'} |")
    cov = r["coverage"]
    out += ["", f"## Pseudo-action coverage in the synthetic training data ({cov['train_split']}, "
            f"{cov['train_rows']:,} rows)", "",
            "| (role, tool, action_type, sensitivity, destination) | Live pseudo-actions (score) | "
            "Scenarios | Training rows | Seen by the model |", "|---|---|---|---|---|"]
    for e in cov["combinations"]:
        flag = "yes" if e["seen_in_training"] else "**NO: never seen in training**"
        out.append(f"| {tuple(e['combo'])} | {e['live_count']} | {len(e['scenarios'])} | "
                   f"{e['train_rows']:,} | {flag} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
