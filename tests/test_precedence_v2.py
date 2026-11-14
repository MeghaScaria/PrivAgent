"""
V2_PLAN.md WP1: escalation-only decision combination.

Runs the governance layer directly (TrajectoryMonitor.evaluate with the
saved model and the real PolicyEngine); no MCP servers or LLM needed.
Every monitor here logs to a temporary directory, never to logs/.

    python tests/test_precedence_v2.py
"""
import itertools
import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from governance.audit_logger import LOG_FILE, LOG_FILE_V2, AuditLogger  # noqa: E402
from governance.policy_engine import PolicyEngine  # noqa: E402
from governance.trajectory_monitor import (  # noqa: E402
    SEVERITY, TrajectoryMonitor, combine_decisions,
)

DECISIONS = list(SEVERITY)
ROLES = ["orchestrator", "retriever", "analyst", "writer"]
TOOLS = {"search_documents": "read", "retrieve_document": "read", "query_database": "query",
         "search_web": "read", "send_result": "transmit"}
DESTS = ["internal", "cross_agent", "external"]


def _monitor(version="v1", **kw):
    logger = AuditLogger(os.path.join(tempfile.mkdtemp(), "audit_log.jsonl"))
    return TrajectoryMonitor(run_id="t", audit_logger=logger, governance_version=version, **kw), logger


def _demo_9e6a8ae2_pattern(monitor):
    """The persisted demo run demo_9e6a8ae2: one sensitive HR read, then
    the writer sends a declared-sensitive answer externally. R1 does not
    fire (fewer than 2 prior sensitive actions), R2 does."""
    monitor.evaluate("retriever", "search_documents", "read", 1, "internal")
    return monitor.evaluate("writer", "send_result", "transmit", 1, "external")


def test_demo_9e6a8ae2_pattern_blocked_under_max_severity_approval_under_v1():
    v1, _ = _monitor("v1")
    d1 = _demo_9e6a8ae2_pattern(v1)
    v2, _ = _monitor("v2")
    d2 = _demo_9e6a8ae2_pattern(v2)

    assert d1.combination["ml_decision"] == "BLOCKED", d1.combination
    assert d1.combination["ml_score"] >= 0.85
    assert [r["rule_id"] for r in d1.combination["rules_fired"]] == ["R2"]

    assert d1.decision == "HUMAN_APPROVAL" and d1.source == "policy_engine"
    assert d2.decision == "BLOCKED" and not d2.allowed
    assert d2.combination["precedence"] == "max_severity"
    assert d2.combination["v1_decision"] == "HUMAN_APPROVAL"
    assert d2.combination["would_differ_under_v1"] is True
    assert d2.combination["downgraded_ml"] is False
    assert d1.combination["downgraded_ml"] is True
    assert d1.risk_score == d2.risk_score


def test_no_v2_decision_less_severe_than_ml_exhaustive():
    """combine_decisions over every ML decision and every ordered subset
    of rule outcomes."""
    rule_options = [("R1", "BLOCKED"), ("R2", "HUMAN_APPROVAL"), ("R3", "BLOCKED")]
    for ml in DECISIONS:
        for n in range(len(rule_options) + 1):
            for subset in itertools.combinations(rule_options, n):
                fired = [{"rule_id": r, "decision": d, "reason": r} for r, d in subset]
                final, _, _ = combine_decisions(ml, fired, "max_severity")
                assert SEVERITY[final] >= SEVERITY[ml], (ml, subset, final)
                for f in fired:
                    assert SEVERITY[final] >= SEVERITY[f["decision"]]


def test_no_v2_decision_less_severe_than_ml_live_monitor():
    """Random runs through the live monitor (saved model + real rules)."""
    rng = random.Random(0)
    downgrades_v1 = 0
    for run in range(150):
        v2, _ = _monitor("v2")
        for _ in range(rng.randint(1, 10)):
            tool = rng.choice(list(TOOLS))
            dest = "external" if tool == "send_result" else rng.choice(DESTS)
            d = v2.evaluate(rng.choice(ROLES), tool, TOOLS[tool], rng.randint(0, 1), dest)
            c = d.combination
            assert SEVERITY[d.decision] >= SEVERITY[c["ml_decision"]], c
            assert not c["downgraded_ml"]
            downgrades_v1 += SEVERITY[c["v1_decision"]] < SEVERITY[c["ml_decision"]]
    assert downgrades_v1 > 0, "the sweep should include v1 downgrade cases"


def test_reviewable_arm_relaxes_only_ml_only_external_blocks_exhaustive():
    """max_severity_reviewable differs from max_severity in exactly one case:
    external action, final BLOCKED, and no fired rule says BLOCKED. Then it is
    HUMAN_APPROVAL. Never allowed, never relaxes a rule's BLOCKED."""
    rule_options = [("R1", "BLOCKED"), ("R2", "HUMAN_APPROVAL"), ("R3", "BLOCKED")]
    for ml in DECISIONS:
        for n in range(len(rule_options) + 1):
            for subset in itertools.combinations(rule_options, n):
                fired = [{"rule_id": r, "decision": d, "reason": r} for r, d in subset]
                for external in (False, True):
                    strict, _, _ = combine_decisions(ml, fired, "max_severity", external=external)
                    rev, _, by = combine_decisions(ml, fired, "max_severity_reviewable",
                                                   external=external)
                    relax = (external and strict == "BLOCKED"
                             and not any(f["decision"] == "BLOCKED" for f in fired))
                    if relax:
                        assert rev == "HUMAN_APPROVAL" and by == "ml_model_made_reviewable"
                    else:
                        assert rev == strict, (ml, subset, external, rev, strict)
                    assert rev not in ("AUTONOMOUS", "RESTRICTED") or ml in ("AUTONOMOUS", "RESTRICTED")
                    if any(f["decision"] == "BLOCKED" for f in fired):
                        assert rev == "BLOCKED"


def test_reviewable_arm_on_live_monitor():
    # demo_9e6a8ae2 pattern: ML BLOCKED (0.9952), only R2 (HUMAN_APPROVAL) fires
    m, _ = _monitor("v2", precedence="max_severity_reviewable")
    d = _demo_9e6a8ae2_pattern(m)
    assert d.combination["ml_decision"] == "BLOCKED"
    assert d.decision == "HUMAN_APPROVAL" and not d.allowed
    assert d.combination["reviewable_relaxation"] is True
    assert "made reviewable" in d.reason
    # a rule's BLOCKED (R1: two prior sensitive reads) is not relaxed
    m, _ = _monitor("v2", precedence="max_severity_reviewable")
    m.evaluate("retriever", "search_documents", "read", 1, "internal")
    m.evaluate("retriever", "query_database", "query", 1, "internal")
    d = m.evaluate("writer", "send_result", "transmit", 1, "external")
    assert d.decision == "BLOCKED" and "R1" in [r["rule_id"] for r in d.combination["rules_fired"]]
    assert d.combination["reviewable_relaxation"] is False
    # an ML-only BLOCKED on an internal action is not relaxed
    m, _ = _monitor("v2", precedence="max_severity_reviewable")
    m.risk_engine.compute_risk = lambda *a: 0.99
    d = m.evaluate("analyst", "analyze", "write", 1, "cross_agent")
    assert d.decision == "BLOCKED"


def test_evaluate_equals_first_of_evaluate_all():
    pe = PolicyEngine()
    actions = [{"tool_name": t, "data_sensitivity": s, "destination_category": d}
               for t in TOOLS for s in (0, 1) for d in DESTS]
    rng = random.Random(1)
    for _ in range(3000):
        prefix = [rng.choice(actions) for _ in range(rng.randint(0, 6))]
        cand = rng.choice(actions)
        decision, reason = pe.evaluate(prefix, cand)
        fired = pe.evaluate_all(prefix, cand)
        if decision is None:
            assert fired == []
        else:
            assert (fired[0]["decision"], fired[0]["reason"]) == (decision, reason)


def test_v1_default_output_unchanged():
    """Default monitor: v1 precedence, no combination in to_dict or the log."""
    m, logger = _monitor()
    assert m.governance_version == "v1" and m.precedence == "first_fire_v1"
    d = _demo_9e6a8ae2_pattern(m)
    assert "combination" not in d.to_dict()
    with open(logger.log_file, encoding="utf-8") as f:
        lines = [json.loads(x) for x in f]
    assert all("combination" not in e for e in lines)
    assert lines[-1]["decision"] == "HUMAN_APPROVAL" and lines[-1]["source"] == "policy_engine"


def test_v2_records_carry_full_combination():
    m, logger = _monitor("v2")
    d = _demo_9e6a8ae2_pattern(m)
    keys = {"ml_score", "ml_decision", "rules_fired", "rule_decision", "final_decision",
            "decided_by", "precedence", "v1_decision", "would_differ_under_v1", "downgraded_ml"}
    assert keys <= set(d.to_dict()["combination"])
    with open(logger.log_file, encoding="utf-8") as f:
        last = json.loads(f.readlines()[-1])
    assert keys <= set(last["combination"])
    assert last["decision"] == last["combination"]["final_decision"] == "BLOCKED"


def test_v2_precedence_override_and_validation():
    m, _ = _monitor("v2", precedence="first_fire_v1")
    assert _demo_9e6a8ae2_pattern(m).decision == "HUMAN_APPROVAL"
    for bad in ({"governance_version": "v3"}, {"precedence": "min"}):
        try:
            TrajectoryMonitor(run_id="t", audit_logger=AuditLogger(
                os.path.join(tempfile.mkdtemp(), "a.jsonl")), **bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad}")


def test_v2_default_log_location_is_separate():
    assert os.path.dirname(LOG_FILE_V2) == os.path.join(os.path.dirname(LOG_FILE), "v2")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
