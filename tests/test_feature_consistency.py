"""
Checks that the live risk engine computes exactly the features (and
therefore exactly the scores) that the training data was built with.

Run with pytest, or directly: python tests/test_feature_consistency.py
"""
import json
import os
import pickle
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from data.generate_trajectories import TASK_TYPES, random_attack_run, benign_run, run_rows, TRAIN_ATTACKS
from governance.features import (
    AGENT_ROLES, TOOL_NAMES, ACTION_TYPES, DESTINATION_CATEGORIES, FEATURE_SETS,
)
from governance.risk_engine import RiskEngine
from models.train_models import FINAL_FEATURE_SET

DECODE = {
    "agent_role": {v: k for k, v in AGENT_ROLES.items()},
    "tool_name": {v: k for k, v in TOOL_NAMES.items()},
    "action_type": {v: k for k, v in ACTION_TYPES.items()},
    "destination_category": {v: k for k, v in DESTINATION_CATEGORIES.items()},
}
FEATURES = FEATURE_SETS[FINAL_FEATURE_SET]


def _to_live(action):
    """Encoded generator action -> the string form the tool wrappers pass in."""
    live = {k: DECODE[k][v] for k, v in action.items() if k in DECODE}
    live["data_sensitivity"] = action["data_sensitivity"]
    return live


def _sample_runs(n=40, seed=7):
    rng = np.random.default_rng(seed)
    runs = []
    for i in range(n):
        if i % 2:
            attack_type = TRAIN_ATTACKS[i % len(TRAIN_ATTACKS)]
            runs.append((random_attack_run(rng, attack_type), attack_type))
        else:
            runs.append((benign_run(rng, int(rng.integers(3, 25))), "benign"))
    return runs


def _engine_with_model(rows):
    tmp = tempfile.mkdtemp()
    df = pd.DataFrame(rows)
    model = GradientBoostingClassifier(n_estimators=20, max_depth=3, random_state=0)
    model.fit(df[FEATURES], df["label"])
    model_path = os.path.join(tmp, "model.pkl")
    thresholds_path = os.path.join(tmp, "thresholds.json")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(thresholds_path, "w") as f:
        json.dump({"autonomous_max": 0.39, "restricted_max": 0.4, "approval_max": 0.65}, f)
    return model, RiskEngine(model_path=model_path, thresholds_path=thresholds_path,
                             features=FEATURES)


def test_live_scores_match_training_rows():
    runs = _sample_runs()
    task_type, agent_count = list(TASK_TYPES)[1], 3
    rows = []
    for run_id, (run, attack_type) in enumerate(runs):
        rows += run_rows(run, run_id, attack_type, "A", task_type, agent_count)
    model, engine = _engine_with_model(rows)

    row_iter = iter(rows)
    checked = 0
    for run, _ in runs:
        live_prefix = []
        for action, _, _ in run:
            row = next(row_iter)
            live_action = _to_live(action)
            expected = float(model.predict_proba(
                pd.DataFrame([[row[f] for f in FEATURES]], columns=FEATURES))[0][1])
            got = engine.compute_risk(live_prefix, live_action, task_type, agent_count)
            assert abs(got - expected) < 1e-12, (row, got, expected)
            live_prefix.append(live_action)
            checked += 1
    assert checked == len(rows)


def test_engine_refuses_lookahead_features():
    runs = _sample_runs(n=6)
    rows = []
    for run_id, (run, attack_type) in enumerate(runs):
        rows += run_rows(run, run_id, attack_type, "A", "multi_hop_research", 3)
    df = pd.DataFrame(rows)
    feats = FEATURE_SETS["all_current"]
    tmp = tempfile.mkdtemp()
    model = GradientBoostingClassifier(n_estimators=5, random_state=0).fit(df[feats], df["label"])
    model_path = os.path.join(tmp, "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    try:
        RiskEngine(model_path=model_path, features=feats)
    except ValueError as e:
        assert "timestamp_norm" in str(e)
    else:
        raise AssertionError("RiskEngine accepted a model that needs timestamp_norm")


if __name__ == "__main__":
    test_live_scores_match_training_rows()
    test_engine_refuses_lookahead_features()
    print("ok")
