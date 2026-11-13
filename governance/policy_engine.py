"""
Deterministic policy engine. Sits alongside the probabilistic risk model
and enforces hard rules that never depend on model confidence. Even if
the ML model is wrong or uncertain, these rules provide a floor of
guaranteed behaviour.

This is intentionally simple and auditable: every rule here is a plain
if-statement a non-ML-engineer can read and verify.
"""


class PolicyEngine:
    def __init__(self,
                 max_sensitive_reads_before_external=2,
                 max_cross_agent_hops_before_external=3):
        self.max_sensitive_reads_before_external = max_sensitive_reads_before_external
        self.max_cross_agent_hops_before_external = max_cross_agent_hops_before_external

    def evaluate(self, trajectory_prefix, candidate_action):
        """Returns (override_decision, reason) where override_decision is
        None if no hard rule fires, or one of "BLOCKED" / "HUMAN_APPROVAL"
        if a rule overrides the ML model's decision."""

        sensitive_reads = sum(
            1 for a in trajectory_prefix if int(a["data_sensitivity"]) == 1
        )
        cross_agent_hops = sum(
            1 for a in trajectory_prefix if a["destination_category"] == "cross_agent"
        )

        # Hard rule 1: never allow an external transmission after the
        # trajectory has already accumulated more than N sensitive reads,
        # regardless of what the ML model scores this specific action.
        if (candidate_action["tool_name"] == "send_result" and
                candidate_action["destination_category"] == "external" and
                sensitive_reads >= self.max_sensitive_reads_before_external):
            return "BLOCKED", (
                f"Policy rule: external transmission blocked after "
                f"{sensitive_reads} prior sensitive-data reads in this task "
                f"(limit: {self.max_sensitive_reads_before_external})"
            )

        # Hard rule 2: any single action touching sensitive data and
        # transmitting externally in the same step is always at least
        # escalated to human approval, never fully autonomous.
        if (int(candidate_action["data_sensitivity"]) == 1 and
                candidate_action["destination_category"] == "external"):
            return "HUMAN_APPROVAL", (
                "Policy rule: sensitive data proposed for direct external "
                "transmission always requires human approval"
            )

        # Hard rule 3: excessive cross-agent hops before an external step
        # is a permission-laundering pattern regardless of individual
        # action sensitivity.
        if (candidate_action["destination_category"] == "external" and
                cross_agent_hops >= self.max_cross_agent_hops_before_external):
            return "BLOCKED", (
                f"Policy rule: external transmission blocked after "
                f"{cross_agent_hops} cross-agent handoffs in this task "
                f"(limit: {self.max_cross_agent_hops_before_external})"
            )

        return None, None

    def evaluate_all(self, trajectory_prefix, candidate_action):
        """Every rule that fires, in rule order (v2, WP1). evaluate() above
        is unchanged and returns only the first of these; v1 uses it.

        Returns [{"rule_id": "R1", "decision": "BLOCKED", "reason": ...}, ...],
        empty if no rule fires. The conditions and reasons are the same as
        in evaluate(); tests check that evaluate() always equals the first
        entry here."""
        sensitive_reads = sum(
            1 for a in trajectory_prefix if int(a["data_sensitivity"]) == 1
        )
        cross_agent_hops = sum(
            1 for a in trajectory_prefix if a["destination_category"] == "cross_agent"
        )
        external = candidate_action["destination_category"] == "external"
        fired = []
        if (candidate_action["tool_name"] == "send_result" and external and
                sensitive_reads >= self.max_sensitive_reads_before_external):
            fired.append({"rule_id": "R1", "decision": "BLOCKED", "reason": (
                f"Policy rule: external transmission blocked after "
                f"{sensitive_reads} prior sensitive-data reads in this task "
                f"(limit: {self.max_sensitive_reads_before_external})")})
        if int(candidate_action["data_sensitivity"]) == 1 and external:
            fired.append({"rule_id": "R2", "decision": "HUMAN_APPROVAL", "reason": (
                "Policy rule: sensitive data proposed for direct external "
                "transmission always requires human approval")})
        if external and cross_agent_hops >= self.max_cross_agent_hops_before_external:
            fired.append({"rule_id": "R3", "decision": "BLOCKED", "reason": (
                f"Policy rule: external transmission blocked after "
                f"{cross_agent_hops} cross-agent handoffs in this task "
                f"(limit: {self.max_cross_agent_hops_before_external})")})
        return fired
