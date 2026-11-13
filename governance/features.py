"""
The one place risk-model features are computed. The training data
generator (data/generate_trajectories.py) and the live risk engine
(governance/risk_engine.py) both call extract_features() here, so a
feature can never be calculated one way in training and another way
at runtime.

Actions are encoded as dicts of small ints (see encode_action). Live
code works with string values ("retriever", "send_result", ...) and
encodes them first.
"""
import numpy as np

AGENT_ROLES = {"orchestrator": 0, "retriever": 1, "analyst": 2, "writer": 3}
TOOL_NAMES = {
    "search_documents": 0, "retrieve_document": 1, "query_database": 2,
    "list_tables": 3, "search_web": 4, "send_result": 5,
    "summarize": 6, "analyze": 7, "get_transmission_log": 8,
}
ACTION_TYPES = {"read": 0, "write": 1, "transmit": 2, "query": 3}
DESTINATION_CATEGORIES = {"internal": 0, "cross_agent": 1, "external": 2}
TASK_TYPES = {
    "multi_hop_research": 0, "comparative_analysis": 1,
    "data_retrieval": 2, "financial_research": 3,
}
EXTERNAL = DESTINATION_CATEGORIES["external"]
CROSS_AGENT = DESTINATION_CATEGORIES["cross_agent"]

ACTION_FEATURES = [
    "agent_role", "tool_name", "action_type", "data_sensitivity",
    "destination_category", "task_type", "agent_count",
]
TRAJECTORY_FEATURES = [
    "mean_sensitivity", "max_sensitivity", "mean_destination",
    "max_destination", "prev_sensitive_reads", "prev_external_transmits",
    "prev_risky_actions", "max_prev_risk", "cumulative_risk",
]

# How sensitive data has moved between agents so far. All are counts or
# flags over the prefix, so inserting harmless steps (non-sensitive,
# internal) never changes them.
#   prev_sensitive_handoffs: earlier sensitive actions sent to another agent
#   prev_cross_agent: earlier actions sent to another agent
#   sensitive_roles: distinct agent roles that have handled sensitive data
#   receiver_differs_from_source: this agent isn't the one that first
#     handled sensitive data in the run (0 if none has yet)
FLOW_FEATURES = [
    "prev_sensitive_handoffs", "prev_cross_agent", "sensitive_roles",
    "receiver_differs_from_source",
]

# Features that say *where* in the run the action is, rather than what
# happened before it. timestamp_norm divides by the run's total length,
# which isn't known until the run ends, so it can only be computed
# offline (training data); the live engine refuses any model that needs it.
POSITIONAL_FEATURES = ["timestamp_norm", "prev_tool_count"]
LOOKAHEAD_FEATURES = ["timestamp_norm"]
# Task context. The synthetic generator assigns these at random,
# independent of the label, so any weight a model puts on them is noise.
CONTEXT_FEATURES = ["task_type", "agent_count"]
# Averages over the whole prefix. Inserting harmless steps anywhere
# earlier in the run lowers them, so they indirectly encode how long the
# run has been going. Counts and maxima don't have this problem.
DILUTED_FEATURES = ["mean_sensitivity", "mean_destination", "cumulative_risk"]

FEATURE_SETS = {
    # The feature list the models were trained on before this change.
    "all_current": ACTION_FEATURES[:5] + ["timestamp_norm"] + ACTION_FEATURES[5:]
                   + TRAJECTORY_FEATURES[:4] + ["prev_tool_count"] + TRAJECTORY_FEATURES[4:],
    "no_timestamp": ACTION_FEATURES + TRAJECTORY_FEATURES[:4] + ["prev_tool_count"]
                    + TRAJECTORY_FEATURES[4:],
    "action_only": ACTION_FEATURES,
    "trajectory_no_position": ACTION_FEATURES + TRAJECTORY_FEATURES,
    "trajectory_no_context": ACTION_FEATURES[:5] + TRAJECTORY_FEATURES,
    # Only features that don't change when harmless steps are inserted
    # into the run: no position, no context noise, no averages.
    "action_core": ACTION_FEATURES[:5],
    "trajectory_invariant": ACTION_FEATURES[:5] + [
        f for f in TRAJECTORY_FEATURES if f not in DILUTED_FEATURES],
    # Phase 3 candidates: the invariant set plus how sensitive data moved
    # between agents, with and without the tool's identity.
    "rich_invariant": ACTION_FEATURES[:5] + [
        f for f in TRAJECTORY_FEATURES if f not in DILUTED_FEATURES] + FLOW_FEATURES,
    "rich_invariant_no_tool": [f for f in ACTION_FEATURES[:5] if f != "tool_name"] + [
        f for f in TRAJECTORY_FEATURES if f not in DILUTED_FEATURES] + FLOW_FEATURES,
    # Diagnostic only: how far position alone gets a classifier.
    "position_only": POSITIONAL_FEATURES,
}


def encode_action(action):
    """String-valued action dict (as used by the tool wrappers) -> the
    int-valued form features are computed from."""
    return {
        "agent_role": AGENT_ROLES[action["agent_role"]],
        "tool_name": TOOL_NAMES[action["tool_name"]],
        "action_type": ACTION_TYPES[action["action_type"]],
        "data_sensitivity": int(action["data_sensitivity"]),
        "destination_category": DESTINATION_CATEGORIES[action["destination_category"]],
    }


def extract_features(prefix, candidate, task_type, agent_count, run_length=None):
    """prefix: encoded actions already executed in this run, in order.
    candidate: the encoded action being scored. task_type: a TASK_TYPES
    key. run_length: total length of the run, known only offline; when
    it's None, timestamp_norm is left out."""
    feats = {
        "agent_role": candidate["agent_role"],
        "tool_name": candidate["tool_name"],
        "action_type": candidate["action_type"],
        "data_sensitivity": candidate["data_sensitivity"],
        "destination_category": candidate["destination_category"],
        "task_type": TASK_TYPES.get(task_type, 0),
        "agent_count": agent_count,
        "prev_tool_count": len(prefix),
    }
    if run_length is not None:
        feats["timestamp_norm"] = round((len(prefix) + 1) / run_length, 4)

    sensitive = [a for a in prefix if a["data_sensitivity"] == 1]
    feats.update({
        "prev_sensitive_handoffs": sum(1 for a in sensitive
                                       if a["destination_category"] == CROSS_AGENT),
        "prev_cross_agent": sum(1 for a in prefix if a["destination_category"] == CROSS_AGENT),
        "sensitive_roles": len({a["agent_role"] for a in sensitive}),
        "receiver_differs_from_source": int(bool(sensitive) and
                                            candidate["agent_role"] != sensitive[0]["agent_role"]),
    })

    if not prefix:
        feats.update({
            "mean_sensitivity": 0.0, "max_sensitivity": 0.0,
            "mean_destination": 0.0, "max_destination": 0.0,
            "prev_sensitive_reads": 0, "prev_external_transmits": 0,
            "prev_risky_actions": 0, "max_prev_risk": 0.0, "cumulative_risk": 0.0,
        })
        return feats

    sens = [a["data_sensitivity"] for a in prefix]
    dests = [a["destination_category"] for a in prefix]
    sensitive_reads = sum(sens)
    external_transmits = sum(1 for d in dests if d == EXTERNAL)
    feats.update({
        "mean_sensitivity": float(np.mean(sens)),
        "max_sensitivity": float(max(sens)),
        "mean_destination": float(np.mean(dests)),
        "max_destination": float(max(dests)),
        "prev_sensitive_reads": sensitive_reads,
        "prev_external_transmits": external_transmits,
        "prev_risky_actions": sensitive_reads + external_transmits,
        "max_prev_risk": float(max(dests)) / 2.0,
        "cumulative_risk": float(sensitive_reads + external_transmits) / len(prefix),
    })
    return feats
