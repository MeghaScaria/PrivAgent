import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pickle
import json
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, brier_score_loss
)
from data.generate_trajectories import generate_dataset
from governance.features import FEATURE_SETS

LABEL_COL = "label"
GROUP_COL = "trajectory_id"
MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

# Chosen by experiments/position_ablation.py using validation data
# only (see that script for the selection rule and full comparison).
FINAL_FEATURE_SET = "trajectory_invariant"
ACTION_FEATURE_SET = "action_core"

# Most benign actions we're willing to stop (HUMAN_APPROVAL or BLOCKED).
MAX_BENIGN_STOP_RATE = 0.05
# Almost every unsafe action should at least be RESTRICTED.
MIN_RESTRICT_RECALL = 0.99
# Only block outright where the model is very sure.
MIN_BLOCK_PRECISION = 0.99
# Each threshold is searched only inside its own band (the same ranges
# the original search used). The synthetic validation set can be almost
# perfectly separable, and without bands the search drifts to extreme
# values that say nothing about attacks the model hasn't seen.
T1_BAND = np.round(np.arange(0.15, 0.40, 0.01), 2)
T2_BAND = np.round(np.arange(0.40, 0.65, 0.01), 2)
T3_BAND = np.round(np.arange(0.65, 0.86, 0.01), 2)
# F1 values this close count as a tie, and ties go to the lowest
# (most cautious) threshold.
F1_TIE_TOLERANCE = 1e-3


def split_by_trajectory(df, seed=42):
    """60/20/20 train/val/test, keeping every step of a trajectory in the
    same split so the test set never contains steps from a run whose
    other steps were trained on."""
    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    trainval_idx, test_idx = next(outer.split(df, groups=df[GROUP_COL]))
    trainval, test = df.iloc[trainval_idx], df.iloc[test_idx]
    inner = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed)
    train_idx, val_idx = next(inner.split(trainval, groups=trainval[GROUP_COL]))
    return trainval.iloc[train_idx], trainval.iloc[val_idx], test


def train_model(train_df, features, seed=42):
    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1, random_state=seed
    )
    model.fit(train_df[features], train_df[LABEL_COL])
    return model


def tune_thresholds(y_true, y_prob):
    """Picks the three autonomy thresholds on validation data.

    An action executes below restricted_max and is stopped at or above
    it, so restricted_max is the operating point that matters most:
    the best F1 for "stopped == unsafe" with at most
    MAX_BENIGN_STOP_RATE of benign actions stopped. autonomous_max is
    the highest value below it that still sends MIN_RESTRICT_RECALL of
    unsafe actions to RESTRICTED or worse. approval_max is the lowest
    value above it where blocking is at least MIN_BLOCK_PRECISION
    precise; anything between it and restricted_max goes to a human."""
    y_true = np.asarray(y_true)
    benign = y_true == 0

    candidates = []
    for t in T2_BAND:
        stopped = y_prob >= t
        if stopped[benign].mean() <= MAX_BENIGN_STOP_RATE:
            candidates.append((t, f1_score(y_true, stopped, zero_division=0)))
    if candidates:
        best_f1 = max(f1 for _, f1 in candidates)
        t2 = min(t for t, f1 in candidates if f1 >= best_f1 - F1_TIE_TOLERANCE)
    else:
        t2 = T2_BAND[-1]

    t1 = T1_BAND[0]
    for t in T1_BAND:
        if recall_score(y_true, y_prob >= t, zero_division=0) >= MIN_RESTRICT_RECALL:
            t1 = t

    t3 = T3_BAND[-1]
    for t in T3_BAND:
        if precision_score(y_true, y_prob >= t, zero_division=0) >= MIN_BLOCK_PRECISION:
            t3 = t
            break

    return {
        "autonomous_max": float(t1),
        "restricted_max": float(t2),
        "approval_max": float(t3),
    }


def evaluate_set(df, y_prob, stop_threshold):
    """Metrics for one evaluation set, at the governance operating point
    (stopped = score >= restricted_max), not sklearn's default 0.5.

    fpr: share of safe steps (label 0) that get stopped.
    benign_run_false_alarm: share of benign runs with any step stopped.
    per_attack_type: step_recall over unsafe steps, and runs_caught, the
    share of attack runs where at least one unsafe step is stopped."""
    y_true = df[LABEL_COL].to_numpy()
    stopped = np.asarray(y_prob) >= stop_threshold
    benign_runs = df["attack_type"] == "benign"
    metrics = {
        "precision": precision_score(y_true, stopped, zero_division=0),
        "recall": recall_score(y_true, stopped, zero_division=0),
        "f1": f1_score(y_true, stopped, zero_division=0),
        "fpr": float(stopped[y_true == 0].mean()),
        "benign_run_false_alarm": float(
            pd.Series(stopped[benign_runs.to_numpy()]).groupby(
                df.loc[benign_runs, GROUP_COL].to_numpy()).any().mean()
        ) if benign_runs.any() else None,
        "brier": brier_score_loss(y_true, y_prob),
    }
    if len(np.unique(y_true)) == 2:
        metrics["auroc"] = roc_auc_score(y_true, y_prob)
        metrics["auprc"] = average_precision_score(y_true, y_prob)

    per_type = {}
    scored = df.assign(stopped=stopped)
    for attack_type, g in scored[scored["attack_type"] != "benign"].groupby("attack_type"):
        unsafe = g[g[LABEL_COL] == 1]
        per_type[attack_type] = {
            "unsafe_steps": int(len(unsafe)),
            "step_recall": float(unsafe["stopped"].mean()) if len(unsafe) else None,
            "runs_caught": float(unsafe.groupby(GROUP_COL)["stopped"].any().mean())
            if len(unsafe) else None,
        }
    metrics["per_attack_type"] = per_type
    return metrics


def fmt(metrics):
    return {k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in metrics.items() if k != "per_attack_type"}


def main():
    print("Generating training data...")
    sets = generate_dataset()
    train_df, val_df, test_df = split_by_trajectory(sets["main"])
    print(f"{sets['main'][GROUP_COL].nunique()} trajectories: "
          f"{train_df[GROUP_COL].nunique()} train / {val_df[GROUP_COL].nunique()} val / "
          f"{test_df[GROUP_COL].nunique()} test")
    eval_sets = {
        "test": test_df,
        "holdout_types": sets["holdout_types"],
        "holdout_variants": sets["holdout_variants"],
    }

    results, trained, feature_config = {}, {}, {}
    for name, set_name in (("action_level", ACTION_FEATURE_SET),
                           ("trajectory_level", FINAL_FEATURE_SET)):
        features = FEATURE_SETS[set_name]
        print(f"\nTraining {name} model ({set_name})...")
        model = train_model(train_df, features)
        val_prob = model.predict_proba(val_df[features])[:, 1]
        thresholds = tune_thresholds(val_df[LABEL_COL], val_prob)
        print("  Thresholds (tuned on val):", thresholds)

        results[name] = {"feature_set": set_name, "thresholds": thresholds}
        for set_label, df in eval_sets.items():
            prob = model.predict_proba(df[features])[:, 1]
            m = evaluate_set(df, prob, thresholds["restricted_max"])
            results[name][set_label] = m
            print(f"  {set_label}: {fmt(m)}")
            for attack_type, pm in m["per_attack_type"].items():
                print(f"    {attack_type}: {pm}")
        trained[name] = model
        feature_config[name] = features

    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(os.path.join(MODELS_DIR, "action_level_model.pkl"), "wb") as f:
        pickle.dump(trained["action_level"], f)
    with open(os.path.join(MODELS_DIR, "trajectory_level_model.pkl"), "wb") as f:
        pickle.dump(trained["trajectory_level"], f)
    with open(os.path.join(MODELS_DIR, "feature_config.json"), "w") as f:
        json.dump(feature_config, f, indent=2)
    # The live system runs the trajectory model, so its thresholds are
    # the ones governance uses.
    with open(os.path.join(MODELS_DIR, "thresholds.json"), "w") as f:
        json.dump(results["trajectory_level"]["thresholds"], f, indent=2)
    with open(os.path.join(MODELS_DIR, "training_metrics.json"), "w") as f:
        json.dump(results, f, indent=2)

    print("\nModels saved to models/")
    print("Setup complete. You can now run: python main.py")


if __name__ == "__main__":
    main()
