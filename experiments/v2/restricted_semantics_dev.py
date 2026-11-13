"""
V2_PLAN.md WP3.3, development only: how often the v2 RESTRICTED semantics
fire on benign VALIDATION runs (seeds 42, 7, 1234). Nothing confirmatory:
no test, held-out or variant-B data is generated beyond what the
generator draws in one stream, and that is discarded unread (as in
precedence_ablation.py, whose data path and frozen model this reuses).

Per step, the v2 decision is the max_severity combination of the frozen
model and the rules; then the WP3 semantics are applied:
  restricted_external  final RESTRICTED and destination external
  restricted_lineage   an allowed external step after an earlier executed
                       RESTRICTED step in the same run

Offline there is no item-level provenance, so "lineage" assumes every
earlier RESTRICTED step's output reaches the sending agent. The lineage
count is therefore an UPPER BOUND on what the live monitor (which follows
actual refs) would escalate.

    python experiments/v2/restricted_semantics_dev.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from precedence_ablation import (  # noqa: E402
    OUT_DIR, SEEDS, build_sets, decide_all, load_frozen,
)
from governance.policy_engine import PolicyEngine  # noqa: E402
from governance.risk_engine import AutonomyController  # noqa: E402
from governance.trajectory_monitor import ALLOWED_DECISIONS  # noqa: E402
from governance.features import DESTINATION_CATEGORIES  # noqa: E402
from models.train_models import GROUP_COL, LABEL_COL  # noqa: E402

EXTERNAL = DESTINATION_CATEGORIES["external"]


def apply_restricted(df, finals):
    """Returns per-step escalation labels (None / restricted_external /
    restricted_lineage) under the WP3 semantics."""
    out, seen_restricted, current = [], False, None
    for run_id, dest, final in zip(df[GROUP_COL], df["destination_category"], finals):
        if run_id != current:
            current, seen_restricted = run_id, False
        external = int(dest) == EXTERNAL
        if external and final == "RESTRICTED":
            label = "restricted_external"
        elif external and final in ALLOWED_DECISIONS and seen_restricted:
            label = "restricted_lineage"
        else:
            label = None
        if final == "RESTRICTED" and not external:
            seen_restricted = True        # executed RESTRICTED step (internal / cross_agent)
        out.append(label)
    return out


def summarise(df, labels, finals):
    names = {v: k for k, v in DESTINATION_CATEGORIES.items()}
    is_benign = df["attack_type"] == "benign"
    restricted = [f == "RESTRICTED" for f in finals]
    context = {f"restricted_steps_{'benign' if b else 'attack'}_{names[int(d)]}":
               sum(1 for r, bb, dd in zip(restricted, is_benign, df["destination_category"])
                   if r and bb == b and int(dd) == d)
               for b in (True, False) for d in names}
    out = _summarise(df, labels)
    out["restricted_steps"] = context
    return out


def _summarise(df, labels):
    benign = (df["attack_type"] == "benign").to_numpy()
    runs = df[GROUP_COL].to_numpy()
    benign_runs = set(runs[benign])
    fired = {k: {r for r, lab, b in zip(runs, labels, benign) if b and lab == k}
             for k in ("restricted_external", "restricted_lineage")}
    any_fired = fired["restricted_external"] | fired["restricted_lineage"]
    unsafe = (df[LABEL_COL] == 1).to_numpy()
    return {
        "benign_runs": len(benign_runs),
        "benign_runs_escalated_any": len(any_fired),
        "benign_runs_escalated_external": len(fired["restricted_external"]),
        "benign_runs_escalated_lineage_upper_bound": len(fired["restricted_lineage"]),
        "benign_rate_any": len(any_fired) / len(benign_runs),
        "benign_steps_escalated": int(sum(1 for lab, b in zip(labels, benign) if b and lab)),
        "unsafe_steps_newly_escalated": int(sum(1 for lab, u in zip(labels, unsafe) if u and lab)),
    }


def main():
    model, features, thresholds = load_frozen()
    controller, policy = AutonomyController(thresholds=thresholds), PolicyEngine()
    report = {"mode": "development", "set": "val", "seeds": SEEDS,
              "decision": "max_severity (v2) then WP3 RESTRICTED semantics",
              "lineage_note": "offline upper bound: every earlier RESTRICTED output assumed to reach the sender",
              "per_seed": {}}
    for seed in SEEDS:
        val = build_sets(seed, confirmatory=False)["val"].reset_index(drop=True)
        res = decide_all(val, model, features, controller, policy)
        labels = apply_restricted(val, res["max_severity"].tolist())
        report["per_seed"][str(seed)] = summarise(val, labels, res["max_severity"].tolist())
        print(f"seed {seed}: {report['per_seed'][str(seed)]}")
    tot = lambda k: sum(report["per_seed"][str(s)][k] for s in SEEDS)  # noqa: E731
    report["pooled"] = {k: tot(k) for k in ("benign_runs", "benign_runs_escalated_any",
                                             "benign_runs_escalated_external",
                                             "benign_runs_escalated_lineage_upper_bound",
                                             "benign_steps_escalated",
                                             "unsafe_steps_newly_escalated")}
    report["pooled"]["benign_rate_any"] = (report["pooled"]["benign_runs_escalated_any"]
                                           / report["pooled"]["benign_runs"])
    os.makedirs(OUT_DIR, exist_ok=True)
    stem = os.path.join(OUT_DIR, "restricted_semantics_dev")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    p = report["pooled"]
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write("# RESTRICTED semantics on benign validation runs (DEVELOPMENT)\n\n"
                "**Development run: validation splits only (seeds 42, 7, 1234).** Not confirmatory.\n\n"
                "Decision: frozen model + rules under max_severity, then the WP3 semantics. "
                "The lineage count is an offline upper bound (no item-level provenance offline).\n\n"
                "| Seed | Benign runs | Escalated (any) | via RESTRICTED+external | via lineage (upper bound) "
                "| Benign steps escalated | Unsafe steps newly escalated |\n|---|---|---|---|---|---|---|\n")
        for s in SEEDS:
            r = report["per_seed"][str(s)]
            f.write(f"| {s} | {r['benign_runs']} | {r['benign_runs_escalated_any']} "
                    f"({r['benign_rate_any']:.1%}) | {r['benign_runs_escalated_external']} | "
                    f"{r['benign_runs_escalated_lineage_upper_bound']} | {r['benign_steps_escalated']} | "
                    f"{r['unsafe_steps_newly_escalated']} |\n")
        f.write(f"| **pooled** | {p['benign_runs']} | {p['benign_runs_escalated_any']} "
                f"({p['benign_rate_any']:.1%}) | {p['benign_runs_escalated_external']} | "
                f"{p['benign_runs_escalated_lineage_upper_bound']} | {p['benign_steps_escalated']} | "
                f"{p['unsafe_steps_newly_escalated']} |\n")
        keys = sorted(report["per_seed"][str(SEEDS[0])]["restricted_steps"])
        f.write("\n## Where RESTRICTED occurs (steps per seed)\n\n"
                "Context for the counts above: the semantics can only fire where the v2 decision "
                "is RESTRICTED. External steps are never RESTRICTED here, and the few benign "
                "RESTRICTED steps are cross_agent steps with no later allowed external send.\n\n"
                "| Seed | " + " | ".join(k.replace("restricted_steps_", "") for k in keys) + " |\n|"
                + "---|" * (1 + len(keys)) + "\n")
        for s in SEEDS:
            rs = report["per_seed"][str(s)]["restricted_steps"]
            f.write(f"| {s} | " + " | ".join(str(rs[k]) for k in keys) + " |\n")
    print("wrote", stem + ".json and .md")


if __name__ == "__main__":
    main()
