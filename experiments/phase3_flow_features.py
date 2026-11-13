"""
Phase 3: does adding flow features (how sensitive data moved between
agents) to the position-invariant model help it detect attacks it hasn't
seen, without bringing back positional shortcuts?

Candidates:
  baseline                trajectory_invariant (the frozen reference model's features)
  rich_invariant          baseline + FLOW_FEATURES
  rich_invariant_no_tool  rich_invariant without tool_name

Data: only the train and validation splits of the randomized main set,
for three data seeds, plus a development-only variant set (variant C:
different tools for sensitive reads, analyst and writer swapped). The
test split, the held-out attack types and the held-out B variants are
never generated into this script's inputs or read.

Checks, all on training/validation data:
  1. Leave-one-attack-type-out: train without one training attack type
     (thresholds tuned on validation runs of the remaining types), then
     score validation benign runs + the left-out type.
  2. Full model per seed: train on the train split, tune thresholds on
     validation, score validation and the variant C set.
  3. Position invariance: each training template after 0-20 neutral
     steps and with neutral steps between its stages; the unsafe-step
     score must not change at all.
  4. The frozen baseline model, on seed 42 validation and variant C, and
     a check that retraining the baseline features on seed 42 reproduces
     the frozen model exactly.

Decision rule (fixed before running): a rich candidate is preferred to
the baseline only if
  a. its position-invariance score range is 0,
  b. its paired leave-one-type-out AUPRC gain over the baseline (one
     pair per seed x left-out type) has mean - 2 * standard error > 0,
  c. its mean variant C AUPRC is at most 0.01 below the baseline's, and
  d. its mean validation benign-run false-alarm rate is at most 2
     points above the baseline's.
If both pass, the one with the higher mean leave-one-type-out AUPRC is
preferred. Otherwise the baseline stays.

This script only reports; it doesn't save models or change any
configuration.

Usage:
    python experiments/phase3_flow_features.py --frozen-dir models/baselines/trajectory_invariant_v1
"""
import argparse
import json
import os
import pickle
import sys
import warnings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from data.generate_trajectories import (
    TRAIN_ATTACKS, build_attack_run, generate_dataset, generate_dev_variants, make_action,
    run_rows, ATTACK_TEMPLATES,
)
from governance.features import FEATURE_SETS
from models.train_models import (
    GROUP_COL, LABEL_COL, evaluate_set, split_by_trajectory, train_model, tune_thresholds,
)

warnings.filterwarnings("ignore", category=UserWarning)
RESULTS_DIR = os.path.join(BASE_DIR, "experiments", "results")
SEEDS = [42, 7, 1234]
CANDIDATES = {
    "baseline": FEATURE_SETS["trajectory_invariant"],
    "rich_invariant": FEATURE_SETS["rich_invariant"],
    "rich_invariant_no_tool": FEATURE_SETS["rich_invariant_no_tool"],
}
PATH_TYPES = ["path_exfiltration", "path_privilege_escalation"]


def dev_data(seed):
    sets = generate_dataset(seed=seed, write_csv=False)
    main = sets["main"]
    del sets  # holdout sets are discarded unread
    train, val, _test_unread = split_by_trajectory(main)
    return train, val, generate_dev_variants(seed)


def scores(df, prob, t2):
    m = evaluate_set(df, prob, t2)
    return {"auprc": m.get("auprc"), "recall": m["recall"], "precision": m["precision"],
            "fpr": m["fpr"], "benign_run_false_alarm": m["benign_run_false_alarm"],
            "per_attack_type": m["per_attack_type"]}


def leave_one_type_out(train, val, features):
    out = {}
    for held in TRAIN_ATTACKS:
        tr = train[train["attack_type"] != held]
        tune = val[val["attack_type"] != held]
        ev = val[val["attack_type"].isin(["benign", held])]
        model = train_model(tr, features)
        t2 = tune_thresholds(tune[LABEL_COL], model.predict_proba(tune[features])[:, 1])["restricted_max"]
        m = scores(ev, model.predict_proba(ev[features])[:, 1], t2)
        out[held] = {"auprc": m["auprc"], "recall": m["recall"],
                     "runs_caught": m["per_attack_type"][held]["runs_caught"], "fpr": m["fpr"]}
    return out


def invariance(model, features):
    """Largest change in any training template's max unsafe-step score
    when neutral steps are added before it and between its stages."""
    neutral = make_action("retriever", "search_documents", "read", 0, "internal")
    worst = 0.0
    for attack_type in TRAIN_ATTACKS:
        n_gaps = len(ATTACK_TEMPLATES[attack_type]) - 1
        scores_seen = []
        for pre in (0, 3, 10, 20):
            for gap in (0, 2):
                run = build_attack_run(attack_type, "A", [neutral] * pre,
                                       [[neutral] * gap] * n_gaps, [])
                df = pd.DataFrame(run_rows(run, 0, attack_type, "A", "multi_hop_research", 3))
                p = model.predict_proba(df[features])[:, 1]
                scores_seen.append(float(p[df[LABEL_COL].to_numpy() == 1].max()))
        worst = max(worst, max(scores_seen) - min(scores_seen))
    return worst


def mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-dir", required=True)
    args = parser.parse_args()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    report = {"seeds": SEEDS, "candidates": CANDIDATES, "per_seed": {}}
    for seed in SEEDS:
        print(f"Seed {seed}: generating train/val and variant C...")
        train, val, dev_c = dev_data(seed)
        seed_report = {}
        for name, features in CANDIDATES.items():
            print(f"  {name}: leave-one-type-out...")
            loto = leave_one_type_out(train, val, features)
            print(f"  {name}: full model...")
            model = train_model(train, features)
            thresholds = tune_thresholds(val[LABEL_COL], model.predict_proba(val[features])[:, 1])
            t2 = thresholds["restricted_max"]
            seed_report[name] = {
                "loto": loto,
                "thresholds": thresholds,
                "val": scores(val, model.predict_proba(val[features])[:, 1], t2),
                "variant_c": scores(dev_c, model.predict_proba(dev_c[features])[:, 1], t2),
                "invariance_score_range": invariance(model, features),
            }
            if seed == 42 and name == "baseline":
                with open(os.path.join(args.frozen_dir, "trajectory_level_model.pkl"), "rb") as f:
                    frozen = pickle.load(f)
                with open(os.path.join(args.frozen_dir, "thresholds.json")) as f:
                    frozen_t = json.load(f)
                same = np.array_equal(frozen.predict_proba(val[features]),
                                      model.predict_proba(val[features]))
                report["frozen_baseline"] = {
                    "retrained_baseline_reproduces_frozen_model": bool(same),
                    "thresholds": frozen_t,
                    "val": scores(val, frozen.predict_proba(val[features])[:, 1],
                                  frozen_t["restricted_max"]),
                    "variant_c": scores(dev_c, frozen.predict_proba(dev_c[features])[:, 1],
                                        frozen_t["restricted_max"]),
                }
        report["per_seed"][str(seed)] = seed_report

    # Aggregate and apply the decision rule.
    summary = {}
    for name in CANDIDATES:
        runs = [report["per_seed"][str(s)][name] for s in SEEDS]
        summary[name] = {
            "loto_auprc": mean(r["loto"][t]["auprc"] for r in runs for t in TRAIN_ATTACKS),
            "loto_recall": mean(r["loto"][t]["recall"] for r in runs for t in TRAIN_ATTACKS),
            "loto_path_auprc": mean(r["loto"][t]["auprc"] for r in runs for t in PATH_TYPES),
            "loto_path_recall": mean(r["loto"][t]["recall"] for r in runs for t in PATH_TYPES),
            "loto_fpr": mean(r["loto"][t]["fpr"] for r in runs for t in TRAIN_ATTACKS),
            "val_auprc": mean(r["val"]["auprc"] for r in runs),
            "val_fpr": mean(r["val"]["fpr"] for r in runs),
            "val_benign_run_false_alarm": mean(r["val"]["benign_run_false_alarm"] for r in runs),
            "variant_c_auprc": mean(r["variant_c"]["auprc"] for r in runs),
            "variant_c_recall": mean(r["variant_c"]["recall"] for r in runs),
            "variant_c_path_recall": mean(
                r["variant_c"]["per_attack_type"][t]["step_recall"] for r in runs for t in PATH_TYPES),
            "invariance_score_range": max(r["invariance_score_range"] for r in runs),
        }
    base = summary["baseline"]
    decision = {}
    for name in ("rich_invariant", "rich_invariant_no_tool"):
        diffs = [report["per_seed"][str(s)][name]["loto"][t]["auprc"]
                 - report["per_seed"][str(s)]["baseline"]["loto"][t]["auprc"]
                 for s in SEEDS for t in TRAIN_ATTACKS]
        se = float(np.std(diffs, ddof=1) / np.sqrt(len(diffs)))
        c = summary[name]
        checks = {
            "a_position_invariant": c["invariance_score_range"] == 0.0,
            "b_loto_gain_mean_minus_2se_positive": float(np.mean(diffs)) - 2 * se > 0,
            "c_variant_c_not_worse": c["variant_c_auprc"] >= base["variant_c_auprc"] - 0.01,
            "d_false_alarms_within_2pts": (c["val_benign_run_false_alarm"]
                                           <= base["val_benign_run_false_alarm"] + 0.02),
        }
        decision[name] = {"loto_auprc_gain_mean": float(np.mean(diffs)), "loto_auprc_gain_se": se,
                          "checks": checks, "passes": all(checks.values())}
    passing = [n for n, d in decision.items() if d["passes"]]
    preferred = max(passing, key=lambda n: summary[n]["loto_auprc"]) if passing else "baseline"
    report.update({"summary": summary, "decision": decision, "preferred": preferred})

    with open(os.path.join(RESULTS_DIR, "phase3_flow_features.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    cols = ["loto_auprc", "loto_recall", "loto_path_auprc", "loto_path_recall", "loto_fpr",
            "val_auprc", "val_fpr", "val_benign_run_false_alarm",
            "variant_c_auprc", "variant_c_recall", "variant_c_path_recall", "invariance_score_range"]
    lines = ["| candidate | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for name, s in summary.items():
        lines.append(f"| {name} | " + " | ".join(f"{s[c]:.3f}" for c in cols) + " |")
    loto_lines = ["| left-out type | " + " | ".join(CANDIDATES) + " |", "|---|" + "---|" * len(CANDIDATES)]
    for t in TRAIN_ATTACKS:
        loto_lines.append(f"| {t} | " + " | ".join(
            f"{mean(report['per_seed'][str(s)][n]['loto'][t]['auprc'] for s in SEEDS):.3f} / "
            f"{mean(report['per_seed'][str(s)][n]['loto'][t]['recall'] for s in SEEDS):.3f}"
            for n in CANDIDATES) + " |")
    md = ["# Phase 3: flow features vs frozen invariant baseline",
          "", "Training and validation data only (3 data seeds). No test or held-out data used.",
          "", "## Summary (means over seeds)", "", *lines,
          "", "## Leave-one-type-out AUPRC / recall (mean over seeds)", "", *loto_lines,
          "", "## Decision rule", "", "```", json.dumps(decision, indent=2), "```",
          "", f"Preferred: **{preferred}**",
          "", "## Frozen baseline (seed 42)", "", "```",
          json.dumps({k: v for k, v in report["frozen_baseline"].items()
                      if k != "val" and k != "variant_c"} | {
              "val": {k: v for k, v in report["frozen_baseline"]["val"].items() if k != "per_attack_type"},
              "variant_c": {k: v for k, v in report["frozen_baseline"]["variant_c"].items()
                            if k != "per_attack_type"}}, indent=2, default=str), "```"]
    with open(os.path.join(RESULTS_DIR, "phase3_flow_features.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
