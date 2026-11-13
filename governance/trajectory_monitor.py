"""
The trajectory monitor is the single point every proposed tool call must
pass through. For each candidate action it:
  1. Extracts features from everything that happened before it in this
     task (the "trajectory prefix").
  2. Asks the risk engine for a probability of unsafe execution.
  3. Asks the policy engine whether any hard rule overrides that score.
  4. Asks the autonomy controller which of the four execution modes
     applies.
  5. Records the decision to the audit log.
  6. Appends the action to the trajectory (only if it was allowed to
     execute) and returns the decision to the caller.

Everything downstream (the MCP tool wrappers) just asks this object
"can I proceed?" and gets back a clear yes/no plus the full reasoning.

The monitor also records handoffs: data passed from one agent to
another (see record_handoff). These run in shadow mode for now: they're
logged with full provenance but never scored, never added to the
trajectory the risk model sees, and never block anything.

Outbound calls (send_result) also get a sensitivity check: the
authoritative label comes from provenance (what the sending agent
actually received), never from what the agent declares, and unknown
provenance counts as sensitive. In sensitivity_mode="shadow" (the
default) the enforced decision is unchanged; the decision the
authoritative label would give is recorded next to it, with mismatch
flags. sensitivity_mode="enforce" scores the authoritative label.

Every event in a run (tool decisions and handoffs) gets the next value
of one per-run sequence counter, so the full order of a run can be
rebuilt from the logs. The sequence number is log metadata only and is
never a model feature.

Decision combination (V2_PLAN.md WP1). governance_version="v1" (the
default) reproduces v1 exactly: precedence "first_fire_v1", where the
first firing rule REPLACES the ML decision, so R2 can turn an ML BLOCKED
into HUMAN_APPROVAL. governance_version="v2" defaults to precedence
"max_severity": final = the most severe of the ML decision and every
firing rule (AUTONOMOUS < RESTRICTED < HUMAN_APPROVAL < BLOCKED), so a
rule can only escalate. Both versions compute the same combination
record (ML score and decision, rules fired, final decision, the v1
decision for comparison); only v2 exports it, in to_dict() and the
audit log, so v1 output is unchanged. v2 monitors log to logs/v2/ by
default.
"""
import uuid
from datetime import datetime, timezone
from governance.risk_engine import RiskEngine, AutonomyController
from governance.policy_engine import PolicyEngine
from governance.audit_logger import get_audit_logger
from governance.provenance import ProvenanceRegistry
from governance.sensitivity import authoritative_label

HANDOFF_MODES = ("shadow", "off")
SENSITIVITY_MODES = ("shadow", "enforce")
ALLOWED_DECISIONS = ("AUTONOMOUS", "RESTRICTED")
GOVERNANCE_VERSIONS = ("v1", "v2")
PRECEDENCES = ("first_fire_v1", "max_severity")
DEFAULT_PRECEDENCE = {"v1": "first_fire_v1", "v2": "max_severity"}
SEVERITY = {"AUTONOMOUS": 0, "RESTRICTED": 1, "HUMAN_APPROVAL": 2, "BLOCKED": 3}


def combine_decisions(ml_decision, fired, precedence):
    """The final decision from the ML decision and the rules that fired
    (fired: PolicyEngine.evaluate_all output, in rule order).

    first_fire_v1: the first firing rule replaces the ML decision.
    max_severity: the most severe of the ML decision and all fired rules.

    Returns (final_decision, rule_index or None, decided_by). rule_index
    points into fired at the rule whose decision (and reason) is final;
    None means the ML decision stands."""
    if precedence == "first_fire_v1":
        if fired:
            return fired[0]["decision"], 0, "policy_engine"
        return ml_decision, None, "ml_model"
    if not fired:
        return ml_decision, None, "ml_model"
    top = max(range(len(fired)), key=lambda i: (SEVERITY[fired[i]["decision"]], -i))
    rule_decision = fired[top]["decision"]
    if SEVERITY[rule_decision] > SEVERITY[ml_decision]:
        return rule_decision, top, "policy_engine"
    if SEVERITY[rule_decision] == SEVERITY[ml_decision]:
        return ml_decision, None, "ml_model+policy_engine"
    return ml_decision, None, "ml_model"


def _ref_order(ref_id):
    return int(ref_id[3:])


class GovernanceDecision:
    def __init__(self, allowed, decision, risk_score, source, reason, action,
                 event_id=None, seq=None, sensitivity=None, flags=None, shadow=None,
                 combination=None, export_combination=False):
        self.allowed = allowed
        self.combination = combination
        self._export_combination = export_combination
        self.decision = decision
        self.risk_score = risk_score
        self.source = source
        self.reason = reason
        self.action = action
        self.event_id = event_id
        self.seq = seq
        self.sensitivity = sensitivity
        self.flags = flags or []
        self.shadow = shadow

    def to_dict(self):
        d = self._to_dict_v1()
        if self._export_combination:
            d["combination"] = self.combination
        return d

    def _to_dict_v1(self):
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "risk_score": round(self.risk_score, 4),
            "source": self.source,
            "reason": self.reason,
            "action": self.action,
            "event_id": self.event_id,
            "seq": self.seq,
            "sensitivity": self.sensitivity,
            "flags": self.flags,
            "shadow": self.shadow,
        }


class TrajectoryMonitor:
    def __init__(self, model_type="trajectory", run_id=None, task_type="multi_hop_research",
                 agent_count=3, policy_engine=None, audit_logger=None,
                 handoff_mode="shadow", sensitivity_mode="shadow",
                 governance_version="v1", precedence=None):
        if governance_version not in GOVERNANCE_VERSIONS:
            raise ValueError(f"governance_version must be one of {GOVERNANCE_VERSIONS}")
        precedence = precedence or DEFAULT_PRECEDENCE[governance_version]
        if precedence not in PRECEDENCES:
            raise ValueError(f"precedence must be one of {PRECEDENCES}")
        self.governance_version = governance_version
        self.precedence = precedence
        if handoff_mode not in HANDOFF_MODES:
            raise ValueError(f"handoff_mode must be one of {HANDOFF_MODES}")
        if sensitivity_mode not in SENSITIVITY_MODES:
            raise ValueError(f"sensitivity_mode must be one of {SENSITIVITY_MODES}")
        if sensitivity_mode == "enforce" and handoff_mode == "off":
            raise ValueError("sensitivity_mode='enforce' needs provenance (handoff_mode='shadow')")
        self.risk_engine = RiskEngine(model_type=model_type)
        self.controller = AutonomyController()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_logger = audit_logger or get_audit_logger(governance_version)
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.task_type = task_type
        self.agent_count = agent_count
        self.trajectory = []       # executed actions only
        self.decisions = []        # every decision, executed or not
        self.handoff_mode = handoff_mode
        self.sensitivity_mode = sensitivity_mode
        self.handoffs = []         # agent-to-agent transfers (shadow mode)
        self.provenance = ProvenanceRegistry()
        self._seq = 0

    def _next_event(self, prefix):
        self._seq += 1
        return f"{self.run_id}:{prefix}{self._seq}", self._seq

    def _decide(self, candidate_action):
        risk_score = self.risk_engine.compute_risk(
            self.trajectory, candidate_action, self.task_type, self.agent_count
        )
        ml_decision = self.controller.decide(risk_score)
        ml_reason = f"Trajectory-aware risk model scored this action at {risk_score:.3f}"
        # The v1 decision, computed exactly as in v1 (evaluate() unchanged).
        policy_override, policy_reason = self.policy_engine.evaluate(
            self.trajectory, candidate_action
        )
        if policy_override is not None:
            v1 = (policy_override, "policy_engine", policy_reason)
        else:
            v1 = (ml_decision, "ml_model", ml_reason)

        fired = self.policy_engine.evaluate_all(self.trajectory, candidate_action)
        if self.precedence == "first_fire_v1":
            final, source, reason = v1
            rule_decision = fired[0]["decision"] if fired else None
            decided_by = source
        else:
            final, idx, decided_by = combine_decisions(ml_decision, fired, self.precedence)
            source = "policy_engine" if idx is not None else "ml_model"
            reason = fired[idx]["reason"] if idx is not None else ml_reason
            rule_decision = (max((f["decision"] for f in fired), key=SEVERITY.get)
                             if fired else None)
        record = {
            "ml_score": round(float(risk_score), 4),
            "ml_decision": ml_decision,
            "rules_fired": [{"rule_id": f["rule_id"], "decision": f["decision"]} for f in fired],
            "rule_decision": rule_decision,
            "final_decision": final,
            "decided_by": decided_by,
            "precedence": self.precedence,
            "v1_decision": v1[0],
            "would_differ_under_v1": final != v1[0],
            "downgraded_ml": SEVERITY[final] < SEVERITY[ml_decision],
        }
        return risk_score, final, source, reason, record

    def outbound_provenance(self, agent_role):
        if self.handoff_mode == "off":
            return {"value": None, "basis": "instrumentation_off", "refs": []}
        return self.provenance.agent_label(agent_role)

    def evaluate(self, agent_role, tool_name, action_type, data_sensitivity,
                 destination_category, check_sensitivity=False):
        """Evaluate a proposed action against the current trajectory.
        Returns a GovernanceDecision. Does NOT execute the tool; the
        caller (the tool wrapper) is responsible for actually invoking
        the MCP tool only if decision.allowed is True.

        check_sensitivity: data_sensitivity is what the acting agent
        declared about the data it's sending. The authoritative label is
        worked out from provenance and recorded alongside it (see the
        module docstring for shadow vs enforce)."""
        sensitivity, flags, shadow = None, [], None
        enforced_sensitivity = data_sensitivity
        if check_sensitivity:
            authoritative, flags = authoritative_label(
                self.outbound_provenance(agent_role), declared=data_sensitivity)
            sensitivity = {
                "declared": data_sensitivity,
                "provenance": authoritative.pop("provenance"),
                "authoritative": authoritative["value"],
                "authoritative_basis": authoritative["basis"],
                "mode": self.sensitivity_mode,
            }
            if self.sensitivity_mode == "enforce":
                enforced_sensitivity = authoritative["value"]
            sensitivity["enforced"] = enforced_sensitivity

        candidate_action = {
            "agent_role": agent_role,
            "tool_name": tool_name,
            "action_type": action_type,
            "data_sensitivity": enforced_sensitivity,
            "destination_category": destination_category,
        }
        risk_score, final_decision, source, reason, combination = self._decide(candidate_action)
        export = self.governance_version == "v2"
        allowed = final_decision in ALLOWED_DECISIONS

        if sensitivity and sensitivity["authoritative"] != enforced_sensitivity:
            # What governance would have decided with the authoritative
            # label. Recorded only: nothing here changes the trajectory.
            s_risk, s_decision, s_source, s_reason, _ = self._decide(
                {**candidate_action, "data_sensitivity": sensitivity["authoritative"]})
            shadow = {"data_sensitivity": sensitivity["authoritative"],
                      "risk_score": round(s_risk, 4), "decision": s_decision,
                      "source": s_source, "reason": s_reason,
                      "would_change_outcome": (s_decision in ALLOWED_DECISIONS) != allowed}

        event_id, seq = self._next_event("t")
        decision = GovernanceDecision(
            allowed=allowed, decision=final_decision, risk_score=risk_score,
            source=source, reason=reason, action=candidate_action,
            event_id=event_id, seq=seq, sensitivity=sensitivity, flags=flags, shadow=shadow,
            combination=combination, export_combination=export,
        )
        self.decisions.append(decision)

        self.audit_logger.record(
            run_id=self.run_id, agent_role=agent_role, tool_name=tool_name,
            risk_score=risk_score, decision=final_decision, source=source,
            reason=reason, trajectory_length=len(self.trajectory),
            task_type=self.task_type, event_id=event_id, seq=seq,
            sensitivity=sensitivity, flags=flags, shadow=shadow,
            combination=combination if export else None,
        )

        if allowed:
            self.trajectory.append(candidate_action)

        return decision

    def register_tool_result(self, decision, tool_name, args, result):
        """Called by the tool wrappers after an allowed call returns.
        Blocked calls return nothing, so nothing is registered for them."""
        if self.handoff_mode == "off":
            return []
        return self.provenance.register_tool_result(
            tool_name, args, result, decision.event_id, decision.action["agent_role"])

    def record_handoff(self, event_type, sender, receiver, payload, consumed=None,
                       produced_ref=None, authorized=True, flags=None, details=None):
        """Records data passing from sender to receiver, in shadow mode.

        payload: {state field: [ref ids]} of everything handed over.
        consumed: the ref ids the receiver actually reads (defaults to all
          of payload). Sensitivity and origins are computed from these.
        produced_ref: for a transformation (e.g. the analysis), the ref
          of what the sender produced from its inputs.
        authorized: whether sender -> receiver is an edge of the declared
          pipeline. Recorded, never enforced in shadow mode.

        Returns the event, or None when handoff_mode is "off"."""
        if self.handoff_mode == "off":
            return None
        handed_over = [r for refs in payload.values() for r in refs]
        consumed = handed_over if consumed is None else consumed
        reg = self.provenance
        reg.note_received(receiver, consumed)
        values = [reg.refs[r]["sensitivity"]["value"] for r in consumed]
        sensitivity = 1 if 1 in values else (None if None in values else 0)
        origins = sorted({o for r in consumed for o in reg.origins(r)}, key=_ref_order)
        flags = list(flags or [])
        if any(reg.refs[r]["kind"] == "unregistered" for r in set(handed_over) | set(origins)):
            flags.append("unregistered_data")
        if not authorized:
            flags.append("unexpected_edge")

        event_id, seq = self._next_event("h")
        event = {
            "event_id": event_id,
            "run_id": self.run_id,
            "seq": seq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "sender": sender,
            "receiver": receiver,
            "payload": payload,
            "consumed_refs": consumed,
            "produced_ref": produced_ref,
            "sensitivity": sensitivity,
            "sensitive_refs": [r for r in consumed if reg.refs[r]["sensitivity"]["value"] == 1],
            "origins": origins,
            "authorized": authorized,
            "flags": flags,
            "details": details or {},
            "mode": self.handoff_mode,
            "enforced": False,
        }
        self.handoffs.append(event)
        mentioned = set(handed_over) | set(consumed) | set(origins)
        if produced_ref:
            mentioned.add(produced_ref)
        self.audit_logger.record_handoff(
            event, refs={r: reg.snapshot(r) for r in sorted(mentioned, key=_ref_order)})
        return event

    def summary(self):
        total = len(self.decisions)
        blocked = sum(1 for d in self.decisions if d.decision == "BLOCKED")
        restricted = sum(1 for d in self.decisions if d.decision == "RESTRICTED")
        approval = sum(1 for d in self.decisions if d.decision == "HUMAN_APPROVAL")
        autonomous = sum(1 for d in self.decisions if d.decision == "AUTONOMOUS")
        return {
            "run_id": self.run_id,
            "total_actions_proposed": total,
            "autonomous": autonomous,
            "restricted": restricted,
            "human_approval": approval,
            "blocked": blocked,
            "trajectory_length": len(self.trajectory),
        }
