"""
Human approval for gated actions. Opt-in only: it's used when a graph
is built with build_graph(..., approvals=ApprovalService(...)), and the
default pipeline is unchanged.

Scope (Phase 4): the writer's external transmission (send_result). When
governance decides HUMAN_APPROVAL for it, either from the existing
ML/policy decision or because an enabled flow rule escalated it, the
graph pauses with LangGraph's interrupt() before the MCP call, and the
reviewer approves or rejects that exact action.

Guarantees, and where they come from:
  - Nothing executes before approval: the MCP call is in a later node
    (transmission_execute) than the interrupt (human_approval).
  - The reviewer approves exactly what was presented: the review is
    bound to an action id and a keyed digest of the action and payload;
    the response must echo both and may not add fields. Anything
    malformed or mismatched counts as a rejection.
  - Approvals can't be forged or bypassed: an approval carries a token
    signed by this service; the execute node checks the token and the
    payload digest again before calling the tool.
  - At most one execution: each action id is claimed in a persistent
    SQLite ledger before the call. A duplicate resume, a retry, or a
    re-run after a crash finds the claim and doesn't call again. An
    execution that started but never finished is not retried.
  - Failures don't permit anything: an error in validation, logging or
    the ledger stops the run before the tool is called.

Audit events go to approval_log.jsonl next to the audit log, with
digests, labels, ref ids and reviewer responses, never the payload or
any retrieved content.

Flow rules are escalation-only: they can turn an allowed action into
HUMAN_APPROVAL, never into BLOCKED, and never relax a stricter decision.
None is enabled unless passed to ApprovalService.
"""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone

ALLOWED_DECISIONS = ("AUTONOMOUS", "RESTRICTED")
HUMAN_APPROVAL = "HUMAN_APPROVAL"
BLOCKED = "BLOCKED"
RESPONSE_FIELDS = {"action_id", "action_digest", "decision", "reviewer", "comment"}

SENSITIVE_CROSSED_TO_EXTERNAL = "sensitive_crossed_agent_boundary_to_external"


def _ref_order(ref_id):
    return int(ref_id[3:])


def rule_sensitive_crossed_to_external(monitor, agent_role):
    """Fires when data the agent proposes to send externally traces back
    to sensitive or unknown-sensitivity data that a different agent
    obtained, i.e. it crossed at least one agent boundary on the way.
    The user's own task text isn't an agent, so it doesn't count here.
    Missing provenance fires the rule (fail closed)."""
    if monitor.handoff_mode == "off":
        return True, {"reason": "provenance_unavailable"}
    reg = monitor.provenance
    received = reg.agent_inputs.get(agent_role, [])
    if not received:
        return True, {"reason": "no_recorded_inputs"}
    origins = sorted({o for r in received for o in reg.origins(r)}, key=_ref_order)
    crossed = [o for o in origins
               if reg.refs[o]["sensitivity"]["value"] != 0
               and reg.refs[o]["produced_by"] not in (agent_role, "user")]
    if not crossed:
        return False, {}
    return True, {
        "reason": "sensitive_data_from_other_agents",
        "crossed_refs": [{k: reg.snapshot(o)[k] for k in ("ref_id", "source", "sensitivity", "produced_by")}
                         for o in crossed],
        "boundary_handoffs": [h["event_id"] for h in monitor.handoffs
                              if h["event_type"] == "handoff" and h["sensitivity"] != 0],
    }


FLOW_RULES = {SENSITIVE_CROSSED_TO_EXTERNAL: rule_sensitive_crossed_to_external}


class ExecutionLedger:
    """Persistent record of gated executions, one row per action id."""

    def __init__(self, path):
        self.path = path
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS executions (
                action_id TEXT PRIMARY KEY, run_id TEXT, tool TEXT, action_digest TEXT,
                status TEXT NOT NULL, claimed_at TEXT, finished_at TEXT)""")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def claim(self, action_id, run_id, tool, action_digest):
        """True if this call claimed the action; False if it was already
        claimed (by an earlier attempt, a duplicate resume, or a retry)."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO executions VALUES (?, ?, ?, ?, 'executing', ?, NULL)",
                    (action_id, run_id, tool, action_digest, _now()))
            return True
        except sqlite3.IntegrityError:
            return False

    def finish(self, action_id, status):
        with self._connect() as conn:
            conn.execute("UPDATE executions SET status = ?, finished_at = ? WHERE action_id = ?",
                         (status, _now(), action_id))

    def status(self, action_id):
        with self._connect() as conn:
            row = conn.execute("SELECT status FROM executions WHERE action_id = ?",
                               (action_id,)).fetchone()
        return row[0] if row else None


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical(value):
    return json.dumps(value, sort_keys=True, default=str).encode("utf-8")


class ApprovalService:
    def __init__(self, ledger, flow_rules=(), key=None, purge_completed=False):
        """key: signs approvals and digests. It must be the same in every
        process that resumes a run (see governance/checkpoint_store.py);
        the random default only works within one process.
        purge_completed: delete a thread's checkpoints once its run ends."""
        unknown = set(flow_rules) - set(FLOW_RULES)
        if unknown:
            raise ValueError(f"Unknown flow rules: {sorted(unknown)}")
        self.ledger = ledger
        self.flow_rules = tuple(flow_rules)
        self._key = key or secrets.token_bytes(32)
        self.purge_completed = purge_completed

    # -- digests and tokens -------------------------------------------
    def _digest(self, value):
        return hmac.new(self._key, _canonical(value), hashlib.sha256).hexdigest()

    def _token(self, action_id, action_digest, reviewer):
        return self._digest({"approved": action_id, "digest": action_digest, "by": reviewer})

    # -- gate ---------------------------------------------------------
    def gate(self, monitor, decision, payload, destination):
        """Turns a governance decision for a transmission into a pending
        action. Called once, before any interrupt."""
        started = time.perf_counter()
        fired = {}
        for name in self.flow_rules:
            hit, evidence = FLOW_RULES[name](monitor, decision.action["agent_role"])
            if hit:
                fired[name] = evidence
        final, decided_by = decision.decision, decision.source
        if final in ALLOWED_DECISIONS and fired:
            final, decided_by = HUMAN_APPROVAL, "flow_rule"

        action = {
            "action_id": str(uuid.uuid4()),
            "run_id": monitor.run_id,
            "tool": "send_result",
            "agent_role": decision.action["agent_role"],
            "destination": destination,
            "payload_digest": self._digest(payload),
            "decision_event_id": decision.event_id,
        }
        pending = {
            **action,
            "action_digest": self._digest(action),
            "governance": {
                "decision": decision.decision, "source": decision.source,
                "risk_score": round(decision.risk_score, 4), "reason": decision.reason,
                "data_sensitivity_scored": decision.action["data_sensitivity"],
                "sensitivity": decision.sensitivity, "flags": decision.flags,
                "shadow": decision.shadow,
            },
            "flow_rules_fired": fired,
            "final_decision": final,
            "decided_by": decided_by,
            "needs_review": final == HUMAN_APPROVAL,
            "requested_at": time.time(),
        }
        pending["gate_overhead_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self._record(monitor, "gate", pending)
        if fired:
            self._record(monitor, "escalation_evaluated", pending)
        if pending["needs_review"]:
            self._record(monitor, "approval_requested", pending)
        return pending

    # -- review -------------------------------------------------------
    def review_request(self, pending, payload):
        """What the reviewer sees. Pure: it runs again whenever the
        approval node restarts. This includes the payload, which is
        shown to the reviewer but never logged. If the payload in state
        no longer matches the one gated, the request says so, and an
        approval of it is rejected (see resolve)."""
        return {
            "action_id": pending["action_id"],
            "action_digest": pending["action_digest"],
            "run_id": pending["run_id"],
            "tool": pending["tool"],
            "agent_role": pending["agent_role"],
            "destination": pending["destination"],
            "payload": payload,
            "payload_matches_gated_action": hmac.compare_digest(
                self._digest(payload), pending["payload_digest"]),
            "final_decision": pending["final_decision"],
            "decided_by": pending["decided_by"],
            "governance": pending["governance"],
            "flow_rules_fired": pending["flow_rules_fired"],
            "respond_with": {"action_id": pending["action_id"],
                             "action_digest": pending["action_digest"],
                             "decision": "approve | reject", "reviewer": "<reviewer id>"},
        }

    def resolve(self, monitor, pending, response, payload):
        """Validates the reviewer's response against the pending action and
        the payload currently in state. Only an exact, well-formed approval
        of the unchanged payload approves; everything else is a rejection,
        recorded with the reason."""
        responded_at = time.time()
        reason = None
        if not hmac.compare_digest(self._digest(payload), pending["payload_digest"]):
            reason = "payload_changed_after_gate"
        elif not isinstance(response, dict):
            reason = "malformed_response"
        elif set(response) - RESPONSE_FIELDS:
            reason = "unexpected_fields"
        elif response.get("action_id") != pending["action_id"]:
            reason = "action_id_mismatch"
        elif not hmac.compare_digest(str(response.get("action_digest", "")), pending["action_digest"]):
            reason = "action_digest_mismatch"
        elif response.get("decision") not in ("approve", "reject"):
            reason = "invalid_decision"
        elif not isinstance(response.get("reviewer"), str) or not response["reviewer"].strip():
            reason = "missing_reviewer"

        if reason:
            outcome, approved = "invalid", False
        else:
            approved = response["decision"] == "approve"
            outcome = "approved" if approved else "rejected"
            reason = "reviewer_approved" if approved else "reviewer_rejected"
        reviewer = response.get("reviewer") if isinstance(response, dict) else None
        approval = {
            "action_id": pending["action_id"],
            "approved": approved,
            "outcome": outcome,
            "reason": reason,
            "reviewer": reviewer if isinstance(reviewer, str) else None,
            "has_comment": bool(isinstance(response, dict) and response.get("comment")),
            "responded_at": responded_at,
            "wait_s": round(responded_at - pending["requested_at"], 3),
            "token": self._token(pending["action_id"], pending["action_digest"], reviewer)
            if approved else None,
        }
        self._record(monitor, "approval_response", pending, approval=approval)
        return approval

    # -- execution ----------------------------------------------------
    def authorize(self, pending, approval, payload):
        """Whether the pending action may run now. Checked independently of
        the approval node, so a missing, forged or stale approval, or a
        payload changed after review, can't get through."""
        if not hmac.compare_digest(self._digest(payload), pending["payload_digest"]):
            return False, "payload_changed_after_review"
        if pending["final_decision"] in ALLOWED_DECISIONS:
            return True, "allowed_without_review"
        if pending["final_decision"] != HUMAN_APPROVAL:
            return False, "blocked_by_governance"
        if not approval or approval.get("action_id") != pending["action_id"]:
            return False, "no_approval_for_this_action"
        if not approval.get("approved"):
            return False, f"not_approved:{approval.get('reason')}"
        expected = self._token(pending["action_id"], pending["action_digest"], approval.get("reviewer"))
        if not hmac.compare_digest(str(approval.get("token") or ""), expected):
            return False, "invalid_approval_token"
        return True, "approved_by_reviewer"

    def record_execution(self, monitor, pending, outcome, reason, approval=None):
        executed_at = time.time()
        self._record(monitor, "execution", pending, approval=approval, execution={
            "outcome": outcome, "reason": reason,
            "seconds_since_request": round(executed_at - pending["requested_at"], 3),
        })

    # -- audit --------------------------------------------------------
    def _record(self, monitor, event_type, pending, approval=None, execution=None):
        event = {
            "timestamp": _now(),
            "event_type": event_type,
            "run_id": pending["run_id"],
            "action_id": pending["action_id"],
            "action_digest": pending["action_digest"],
            "payload_digest": pending["payload_digest"],
            "tool": pending["tool"],
            "agent_role": pending["agent_role"],
            "destination": pending["destination"],
            "decision_event_id": pending["decision_event_id"],
            "governance": pending["governance"],
            "flow_rules_fired": pending["flow_rules_fired"],
            "final_decision": pending["final_decision"],
            "decided_by": pending["decided_by"],
            "needs_review": pending["needs_review"],
            "gate_overhead_ms": pending.get("gate_overhead_ms"),
        }
        if approval is not None:
            event["approval"] = {k: v for k, v in approval.items() if k != "token"}
        if execution is not None:
            event["execution"] = execution
        monitor.audit_logger.record_approval(event)
        return event


def approval_metrics(events, run_labels):
    """Summary metrics from approval log events.

    run_labels: {run_id: "benign" | "attack"}, the ground truth for each
    run (from the scenario definition, not from governance). Runs with
    no gated transmission still count toward the run totals."""
    by_run = {}
    for e in events:
        by_run.setdefault(e["run_id"], []).append(e)

    def runs(label):
        return [r for r, lab in run_labels.items() if lab == label]

    def escalated(run_id):
        return any(e["event_type"] == "approval_requested" for e in by_run.get(run_id, []))

    def executed(run_id):
        return any(e["event_type"] == "execution" and e["execution"]["outcome"] == "executed"
                   for e in by_run.get(run_id, []))

    responses = [e["approval"] for e in events if e["event_type"] == "approval_response"]
    requests = [e for e in events if e["event_type"] == "approval_requested"]
    benign, attack = runs("benign"), runs("attack")
    escalated_runs = [r for r in run_labels if escalated(r)]
    waits = [a["wait_s"] for a in responses]
    overheads = [e["gate_overhead_ms"] for e in events
                 if e["event_type"] == "gate" and e.get("gate_overhead_ms") is not None]
    return {
        "approval_requests": len(requests),
        "approved": sum(a["outcome"] == "approved" for a in responses),
        "rejected": sum(a["outcome"] == "rejected" for a in responses),
        "invalid_responses": sum(a["outcome"] == "invalid" for a in responses),
        "requests_by_trigger": {t: sum(e["decided_by"] == t for e in requests)
                                for t in sorted({e["decided_by"] for e in requests})},
        "benign_runs": len(benign),
        "benign_runs_interrupted": sum(escalated(r) for r in benign),
        "benign_interruption_rate": (sum(escalated(r) for r in benign) / len(benign)) if benign else None,
        "attack_runs": len(attack),
        "attack_runs_escalated": sum(escalated(r) for r in attack),
        "false_positive_escalation_rate": (sum(run_labels[r] == "benign" for r in escalated_runs)
                                           / len(escalated_runs)) if escalated_runs else None,
        "attack_transmissions_executed": sum(executed(r) for r in attack),
        "benign_transmissions_executed": sum(executed(r) for r in benign),
        "duplicate_executions_prevented": sum(
            e["event_type"] == "execution" and e["execution"]["outcome"] == "duplicate_prevented"
            for e in events),
        "mean_review_wait_s": (sum(waits) / len(waits)) if waits else None,
        "mean_gate_overhead_ms": (sum(overheads) / len(overheads)) if overheads else None,
    }
