"""
Core probabilistic risk engine. Loads the trained gradient-boosted
classifiers and turns a proposed action, in the context of everything
that happened before it in the current task, into a risk score. The
AutonomyController then turns that score into one of four execution
decisions.
"""
import pickle
import json
import os
import pandas as pd

from governance.features import (
    encode_action, extract_features, LOOKAHEAD_FEATURES,
)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
FEATURE_CONFIG = os.path.join(MODELS_DIR, "feature_config.json")

DECISION_AUTONOMOUS = "AUTONOMOUS"
DECISION_RESTRICTED = "RESTRICTED"
DECISION_HUMAN_APPROVAL = "HUMAN_APPROVAL"
DECISION_BLOCKED = "BLOCKED"


def load_feature_list(model_name, config_path=None):
    """The exact feature list a saved model was trained on, written by
    models/train_models.py next to the model files."""
    with open(config_path or FEATURE_CONFIG, "r") as f:
        return json.load(f)[model_name]


class RiskEngine:
    """Computes P(unsafe | action, context) using either only the
    candidate action's own features ("action" mode) or the full
    trajectory prefix as well ("trajectory" mode, the PrivAgent default)."""

    def __init__(self, model_type="trajectory", model_path=None,
                 thresholds_path=None, features=None):
        self.model_type = model_type
        thresholds_path = thresholds_path or os.path.join(MODELS_DIR, "thresholds.json")

        if model_type in ("trajectory", "action"):
            name = "trajectory_level" if model_type == "trajectory" else "action_level"
            path = model_path or os.path.join(MODELS_DIR, f"{name}_model.pkl")
            with open(path, "rb") as f:
                self.model = pickle.load(f)
            self.features = features or load_feature_list(name)
            lookahead = [f for f in self.features if f in LOOKAHEAD_FEATURES]
            if lookahead:
                raise ValueError(
                    f"Model needs {lookahead}, which depends on the run's total "
                    f"length and can't be computed while the run is in progress"
                )
        else:
            self.model = None
            self.features = None

        with open(thresholds_path, "r") as f:
            self.thresholds = json.load(f)

    def compute_risk(self, trajectory_prefix, candidate_action, task_type, agent_count):
        """trajectory_prefix: list of action dicts already executed in this
        task. candidate_action: dict with agent_role, tool_name, action_type,
        data_sensitivity, destination_category (all as the raw string/int
        values used elsewhere in this codebase)."""
        if self.model_type == "none":
            return 0.0
        if self.model_type == "static":
            if (candidate_action["data_sensitivity"] == 1 and
                    candidate_action["destination_category"] == "external"):
                return 0.9
            return 0.1

        feats = extract_features(
            [encode_action(a) for a in trajectory_prefix],
            encode_action(candidate_action), task_type, agent_count,
        )
        X = pd.DataFrame([[feats[f] for f in self.features]], columns=self.features)
        return float(self.model.predict_proba(X)[0][1])


class AutonomyController:
    """Maps a risk probability to one of four graduated execution modes."""

    def __init__(self, thresholds_path=None, thresholds=None):
        if thresholds is not None:
            self.thresholds = thresholds
        else:
            thresholds_path = thresholds_path or os.path.join(MODELS_DIR, "thresholds.json")
            with open(thresholds_path, "r") as f:
                self.thresholds = json.load(f)

    def decide(self, risk_score):
        t1 = self.thresholds["autonomous_max"]
        t2 = self.thresholds["restricted_max"]
        t3 = self.thresholds["approval_max"]
        if risk_score < t1:
            return DECISION_AUTONOMOUS
        elif risk_score < t2:
            return DECISION_RESTRICTED
        elif risk_score < t3:
            return DECISION_HUMAN_APPROVAL
        else:
            return DECISION_BLOCKED
