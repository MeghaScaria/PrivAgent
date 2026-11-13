"""
Does the risk model detect malicious behaviour, or does it just learn
*when* in a run attacks happen? This script:

  1. Measures how much position information is in each dataset: how well
     position alone predicts the label, and how well the
     non-positional features recover the step index.
  2. Trains every feature set in governance.features.FEATURE_SETS on both
     the legacy data (fixed templates) and the randomized data (templates
     embedded at random positions), tuning thresholds on validation only.
  3. Picks the final feature set using validation AUPRC only, before any
     test or held-out result is looked at. Candidates are fixed in
     advance by rule: no positional features, no context features (random
     noise in this generator), and no prefix averages (which change when
     harmless steps are inserted, so they encode run length indirectly).
  4. Evaluates every model on the randomized test split, the held-out
     attack types and the held-out template variants.
  5. Position sweep: places each attack template after 0-20 neutral
     benign steps and checks whether the unsafe step is still caught.
  6. Permutation importance of the selected model on validation data.

Usage:
    python experiments/position_ablation.py [--baseline-dir DIR]

--baseline-dir: a folder holding a previously trained
trajectory_level_model.pkl and thresholds.json (trained on the
all_current feature set), evaluated alongside the new models.
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
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, r2_score, roc_auc_score

from data.generate_trajectories import (
    ALL_ATTACKS, build_attack_run, generate_dataset, make_action, run_rows,
)
from governance.features import (
    CONTEXT_FEATURES, DILUTED_FEATURES, FEATURE_SETS, POSITIONAL_FEATURES, TRAJECTORY_FEATURES,
)
from models.train_models import (
    GROUP_COL, LABEL_COL, evaluate_set, fmt, split_by_trajectory, train_model,
    tune_thresholds,
)

warnings.filterwarnings("ignore", category=UserWarning)
RESULTS_DIR = os.path.join(BASE_DIR, "experiments", "results")
EXCLUDED_FROM_SELECTION = set(POSITIONAL_FEATURES) | set(CONTEXT_FEATURES) | set(DILUTED_FEATURES)
CANDIDATE_SETS = [name for name, feats in FEATURE_SETS.items()
                  if not set(feats) & EXCLUDED_FROM_SELECTION]
POSITION_BINS = [0, 5, 10, 15, 20, 1000]
SWEEP_OFFSETS = list(range(0, 21, 2))


def investigate(train, val):
    runs = pd.concat([train, val]).groupby(GROUP_COL).agg(
        run_length=("run_length", "first"), attack_type=("attack_type", "first"))
    is_attack = runs["attack_type"] != "benign"
    out = {"run_length": {
        "attack": runs.loc[is_attack, "run_length"].describe()[["mean", "min", "max"]].round(2).to_dict(),
        "benign": runs.loc[~is_attack, "run_length"].describe()[["mean", "min", "max"]].round(2).to_dict(),
    }}

    unsafe = train[train[LABEL_COL] == 1]
    out["distinct_unsafe_positions"] = {
        a: {"timestamp_norm": int(g["timestamp_norm"].nunique()),
            "step_index": int(g["prev_tool_count"].nunique())}
        for a, g in unsafe.groupby("attack_type")
    }

    out["label_spearman"] = {
        f: round(float(train[[f, LABEL_COL]].corr("spearman").iloc[0, 1]), 3)
        if train[f].nunique() > 1 else None
        for f in FEATURE_SETS["all_current"] + ["run_length"]
    }

    out["position_only_val_auroc"] = {}
    for feats in (["timestamp_norm"], ["prev_tool_count"], POSITIONAL_FEATURES,
                  POSITIONAL_FEATURES + ["run_length"]):
        clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0)
        clf.fit(train[feats], train[LABEL_COL])
        out["position_only_val_auroc"]["+".join(feats)] = round(
            roc_auc_score(val[LABEL_COL], clf.predict_proba(val[feats])[:, 1]), 3)

    ratios = ["mean_sensitivity", "max_sensitivity", "mean_destination",
              "max_destination", "max_prev_risk", "cumulative_risk"]
    counts = ["prev_sensitive_reads", "prev_external_transmits", "prev_risky_actions"]
    out["step_index_recovered_val_r2"] = {}
    for name, feats in (("ratio features", ratios), ("count features", counts),
                        ("all non-positional trajectory features", TRAJECTORY_FEATURES)):
        reg = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=0)
        reg.fit(train[feats], train["prev_tool_count"])
        out["step_index_recovered_val_r2"][name] = round(
            r2_score(val["prev_tool_count"], reg.predict(val[feats])), 3)
    return out


def recall_by_position(df, prob, t2):
    bins = pd.cut(df["prev_tool_count"], POSITION_BINS, right=False)
    stopped = pd.Series(np.asarray(prob) >= t2, index=df.index)
    out = {}
    for b, idx in df.groupby(bins, observed=True).groups.items():
        g = df.loc[idx]
        unsafe, safe = g[LABEL_COL] == 1, g[LABEL_COL] == 0
        out[f"{b.left}-{b.right - 1 if b.right < 1000 else '+'}"] = {
            "unsafe_steps": int(unsafe.sum()),
            "recall": round(float(stopped[idx][unsafe].mean()), 3) if unsafe.any() else None,
            "fpr": round(float(stopped[idx][safe].mean()), 3) if safe.any() else None,
        }
    return out


def position_sweep(model, features, t2):
    """Each template after k neutral steps (non-sensitive internal
    document searches), nothing between or after its stages. Only the
    position changes (and the ratio features get diluted)."""
    neutral = make_action("retriever", "search_documents", "read", 0, "internal")
    out = {}
    for attack_type in ALL_ATTACKS:
        scores = []
        for k in SWEEP_OFFSETS:
            run = build_attack_run(attack_type, "A", [neutral] * k, [[]] * 10, [])
            df = pd.DataFrame(run_rows(run, 0, attack_type, "A", "multi_hop_research", 3))
            prob = model.predict_proba(df[features])[:, 1]
            scores.append(round(float(prob[df[LABEL_COL].to_numpy() == 1].max()), 3))
        out[attack_type] = {
            "max_unsafe_score_by_offset": scores,
            "caught_share": round(float(np.mean([s >= t2 for s in scores])), 3),
            "score_range": round(max(scores) - min(scores), 3),
        }
    out["overall_caught_share"] = round(float(np.mean(
        [v["caught_share"] for v in out.values()])), 3)
    return out


def evaluate_model(model, features, thresholds, eval_sets):
    t2 = thresholds["restricted_max"]
    res = {"thresholds": thresholds}
    for set_name, df in eval_sets.items():
        prob = model.predict_proba(df[features])[:, 1]
        res[set_name] = evaluate_set(df, prob, t2)
        if set_name == "test":
            res["test_by_position"] = recall_by_position(df, prob, t2)
    res["position_sweep"] = position_sweep(model, features, t2)
    return res


def summary_table(results):
    cols = ["model", "val AUPRC", "t2",
            "test F1", "test P", "test R", "test FPR", "test AUROC",
            "types F1", "types R", "types FPR", "types AUROC",
            "variants F1", "variants R", "variants AUROC",
            "benign-run alarm", "sweep caught"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for name, r in results.items():
        t, h, v = r["test"], r["holdout_types"], r["holdout_variants"]
        cells = [name, r.get("val_auprc", "-"), r["thresholds"]["restricted_max"],
                 t["f1"], t["precision"], t["recall"], t["fpr"], t.get("auroc"),
                 h["f1"], h["recall"], h["fpr"], h.get("auroc"),
                 v["f1"], v["recall"], v.get("auroc"),
                 t["benign_run_false_alarm"], r["position_sweep"]["overall_caught_share"]]
        lines.append("| " + " | ".join(
            f"{c:.3f}" if isinstance(c, float) else str(c) for c in cells) + " |")
    return "\n".join(lines)


def per_type_table(results, models):
    attack_types = sorted({a for m in models for s in ("test", "holdout_types", "holdout_variants")
                           for a in results[m][s]["per_attack_type"]})
    lines = ["| attack type (set) | " + " | ".join(models) + " |",
             "|---|" + "---|" * len(models)]
    for s in ("test", "holdout_variants", "holdout_types"):
        for a in attack_types:
            row = [results[m][s]["per_attack_type"].get(a) for m in models]
            if all(r is None for r in row):
                continue
            lines.append(f"| {a} ({s}) | " + " | ".join(
                f"{r['step_recall']:.2f} / {r['runs_caught']:.2f}" if r else "-" for r in row) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", default=None)
    args = parser.parse_args()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Generating data...")
    data = {mode: generate_dataset(mode=mode, write_csv=False) for mode in ("legacy", "randomized")}
    splits = {mode: split_by_trajectory(d["main"]) for mode, d in data.items()}
    # Every model is judged on the randomized evaluation sets.
    eval_sets = {
        "test": splits["randomized"][2],
        "holdout_types": data["randomized"]["holdout_types"],
        "holdout_variants": data["randomized"]["holdout_variants"],
    }

    report = {"investigation": {}, "models": {}}
    for mode in ("legacy", "randomized"):
        print(f"Investigating {mode} data...")
        train, val, _ = splits[mode]
        report["investigation"][mode] = investigate(train, val)

    trained = {}
    for mode in ("legacy", "randomized"):
        train, val, _ = splits[mode]
        for set_name, features in FEATURE_SETS.items():
            name = f"{mode}/{set_name}"
            print(f"Training {name}...")
            model = train_model(train, features)
            val_prob = model.predict_proba(val[features])[:, 1]
            thresholds = tune_thresholds(val[LABEL_COL], val_prob)
            trained[name] = (model, features, thresholds)
            report["models"][name] = {
                "val_auprc": round(float(average_precision_score(val[LABEL_COL], val_prob)), 4),
                "thresholds": thresholds,
            }

    # Selection uses validation results only. Nothing below this line
    # can influence it.
    val_scores = {s: report["models"][f"randomized/{s}"]["val_auprc"] for s in CANDIDATE_SETS}
    selected = max(val_scores, key=val_scores.get)
    report["selection"] = {
        "rule": "highest validation AUPRC, trained on randomized data, among feature sets "
                "with none of: " + ", ".join(sorted(EXCLUDED_FROM_SELECTION)),
        "candidates_val_auprc": val_scores,
        "selected": selected,
    }
    print(f"Selected feature set (validation only): {selected} {val_scores}")

    for name, (model, features, thresholds) in trained.items():
        print(f"Evaluating {name}...")
        report["models"][name].update(evaluate_model(model, features, thresholds, eval_sets))

    if args.baseline_dir:
        print("Evaluating saved baseline model...")
        with open(os.path.join(args.baseline_dir, "trajectory_level_model.pkl"), "rb") as f:
            baseline = pickle.load(f)
        with open(os.path.join(args.baseline_dir, "thresholds.json")) as f:
            baseline_thresholds = json.load(f)
        report["models"]["saved current model"] = evaluate_model(
            baseline, FEATURE_SETS["all_current"], baseline_thresholds, eval_sets)

    model, features, _ = trained[f"randomized/{selected}"]
    val = splits["randomized"][1]
    sample = val.sample(n=min(15000, len(val)), random_state=0)
    imp = permutation_importance(model, sample[features], sample[LABEL_COL],
                                 scoring="average_precision", n_repeats=5, random_state=0)
    report["permutation_importance_val_auprc_drop"] = dict(sorted(
        ((f, round(float(m), 4)) for f, m in zip(features, imp.importances_mean)),
        key=lambda x: -x[1]))

    with open(os.path.join(RESULTS_DIR, "position_ablation.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    focus = list(dict.fromkeys(m for m in (
        "saved current model", "legacy/all_current", "randomized/all_current",
        "randomized/trajectory_no_position", "randomized/action_core",
        f"randomized/{selected}") if m in report["models"]))
    md = ["# Position-shortcut ablation", "",
          f"Selected feature set (validation AUPRC only): **{selected}**", "",
          "Metrics at each model's own validation-tuned stop threshold (t2). "
          "All models are evaluated on the randomized test split and held-out sets.", "",
          summary_table(report["models"]), "",
          "## Per attack type: step recall / runs caught", "",
          per_type_table(report["models"], focus)]
    with open(os.path.join(RESULTS_DIR, "position_ablation.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps(report["investigation"], indent=1))
    print(json.dumps(report["selection"], indent=1))
    print("\n" + summary_table(report["models"]))
    print("\n" + per_type_table(report["models"], focus))
    for name in focus:
        print(f"\n{name} position sweep:",
              {a: v["caught_share"] for a, v in report["models"][name]["position_sweep"].items()
               if isinstance(v, dict)})
        print(f"{name} test recall/FPR by step index:", report["models"][name]["test_by_position"])
    print("\nPermutation importance:", report["permutation_importance_val_auprc_drop"])


if __name__ == "__main__":
    main()
