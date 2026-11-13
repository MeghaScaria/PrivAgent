# Revised evidence map

**What this covers.** This map links the claims of `PrivAgent_Research_Paper_Revised.md` to code, result files, stored logs and verified publications. Claims carried over unchanged from the original paper keep their evidence as listed in `research_paper/PAPER_EVIDENCE_MAP.md`. That original file is preserved unchanged, and this map supersedes it for the revised manuscript.

**Evidence types:**

| Tag | Meaning |
|---|---|
| CODE | source code |
| RESULT | stored experiment output |
| EVID | `research_paper/evidence/` copies of the Stage 0 and Stage 1 metrics |
| LOG | persisted application logs in `logs/` (dashboard synthetic demo runs, 8 Nov 2026) |
| DEVLOG | development session log only (weaker; marked in the text) |
| SNAP | frozen exploratory snapshot |
| LIT | publication, verified 10 Nov 2026 |

## New or changed claims

| Claim (section) | Evidence | Type |
|---|---|---|
| Central statement and RQ1–RQ3 mapping (§1.2–1.3, Table 1) | each cell is traced to the rows below | – |
| Handoffs are **recorded** (§4.9) | `agents/handoffs.py` (`HandoffTracker`, `PIPELINE_HANDOFFS`); `TrajectoryMonitor.record_handoff`; `logs/handoff_log.jsonl` | CODE, LOG |
| Provenance is **propagated** through handoffs (§4.9) | `governance/provenance.py`: `derive` (inherited max), `origins`, `agent_label`; `governance/sensitivity.py`: `combine` | CODE |
| Handoffs are **not in the scored trajectory** (§4.9) | `trajectory_monitor.py`: `trajectory.append` occurs only in `evaluate` for allowed tool actions; `record_handoff` appends to `self.handoffs` only | CODE |
| Live tool actions are never `cross_agent` (§4.2, §4.9) | `agents/tools.py`: every wrapper passes `destination_category="internal"`, except `evaluate_send`, which passes `"external"` | CODE |
| 6/107 is an offline result on trajectories that contain `cross_agent` actions (§4.9, §7.1.2) | `data/generate_trajectories.py` (`path_cross_agent_leak` template: four `cross_agent` stages); `models/training_metrics.json` (`holdout_types.per_attack_type.path_cross_agent_leak.runs_caught` = 0.0561; 321 unsafe steps ÷ 3 unsafe stages per template = 107 runs) | CODE, RESULT |
| "6/107" definition: runs with ≥ 1 unsafe step scored ≥ 0.50 (§7.1.2) | `models/train_models.py:evaluate_set` (`runs_caught`, stop threshold = `restricted_max` = 0.50) | CODE |
| Decision combination: a fired rule replaces ML; rule order R1, R2, R3 (§4.10) | `trajectory_monitor.py:_decide`; `policy_engine.py:evaluate` | CODE |
| ML decision not logged separately (§4.10) | `audit_logger.py:record` fields (`risk_score`, `decision`, `source`); `approval.py:gate` (`governance.decision` = final decision) | CODE |
| The approval graph offers HUMAN_APPROVAL for review, and approval executes it (§4.10) | `approval.py:gate` (`needs_review = final == HUMAN_APPROVAL`), `authorize`; `approval_flow.py:_execute` | CODE |
| Downgrade observed in the Attack Lab (3 scenarios, scores 0.995–0.999) (§4.10, §7.1.3) | `experiments/results/attack_lab_replay.md` | RESULT |
| Downgrade observed in demo `demo_9e6a8ae2`: r = 0.9952, final HUMAN_APPROVAL via `policy_engine`, offered for review, rejected (§4.10) | `logs/approval_log.jsonl` (events `gate`, `approval_requested`, `approval_response`, `execution`) | LOG |
| Experiment 5 does not store ML scores (§4.10, changelog) | `experiments/results/approval_evaluation.json` (`runs[*]` has `send_decision` and `send_decided_by`, no score) | RESULT |
| Proposed invariant and conflict rules (§4.10, §10) | proposal only; `policy_engine.py` unchanged | – |
| Misreporting demonstration ≈0.0000005 against ≈0.9995 (§7.2) | development log (Phase 2/3 report for test scenario `sensitive_send_misreported`); `tests/test_sensitivity_authority.py:test_misreported_sensitivity_is_flagged_and_shadow_scored` asserts shadow > enforced, the flag, and enforced = declared | DEVLOG, CODE |
| Stored misreporting demonstration 0.0 → AUTONOMOUS against shadow 0.9952 → HUMAN_APPROVAL, `would_change_outcome = true` (§7.2) | `logs/audit_log.jsonl`, `send_result` events for runs `demo_cc0f5f9e` and `demo_89c31726` | LOG |
| `*_misreported` sends executed in the current configuration (§7.2, §9 B6) | `experiments/results/approval_evaluation.md` | RESULT |
| Enforce mode exists but is not enabled in the application (§4.8) | `trajectory_monitor.py` default `sensitivity_mode="shadow"`; `enforce` appears only in `tests/test_sensitivity_authority.py` | CODE |
| Step-level against run-level definitions (§6) | `models/train_models.py:evaluate_set` | CODE |
| Row-level split and per-row ID in the original (§7.1.1 A) | development log (code review and fix report); Stage 0 metrics in `research_paper/evidence/stage0_original_training_metrics.json`; thresholds in `stage0_original_thresholds.json` | DEVLOG, EVID |
| Stage 1 held-out F1 0.657, R 0.559, AUROC 0.905 (§7.1.1 A) | `research_paper/evidence/stage1_corrected_eval_training_metrics.json` | EVID |
| Same send ≈0.04 at step 3 against ≈1.0 at step 5 (§7.1.1 B) | development log (Stage 1 report) | DEVLOG |
| Position-only AUROC 0.951; ratio R² 0.72; 1–3 positions; recall 0.84 → 0.00; sweep range 0.000; recall 0.89–1.00 (§7.1.1 B) | `experiments/results/position_ablation.json` (`investigation`, `models[...].test_by_position`, `position_sweep`); `phase3_flow_features.json` (`invariance_score_range`) | RESULT |
| Round 1 against deployed trade-off table (§7.1.1 C) | `experiments/results/position_ablation.md` (summary and per-type tables) | RESULT |
| Wang et al. comparison (§2.3, Table 2) | Wang, Zhu, Li, *Electronics* 15(13):2829, doi:10.3390/electronics15132829, published 27 Jun 2026. Full text read at https://www.mdpi.com/2079-9292/15/13/2829: PEP and intercept(), CapabilityToken, R01–R05 first-match, LabelTracker SI/DS, SHA-256 hash-chained AuditLogger; MVP-30 dataset; 1,050 deepseek-v4-pro runs; ASR 40.0% → 5.0% against 35.0% Spotlighting; ΔFNR(call) 26.4 pp; mock tools in-process; §4.9 preliminary real MCP stdio filesystem server; REQUIRE_CONFIRM treated as blocking | LIT |
| CaMeL, FIDES and Progent still preprints (§2.2, refs) | searches on 10 Nov 2026 found no venue; arXiv listings name none | LIT |

## Unchanged claims (see `PAPER_EVIDENCE_MAP.md`)

The following are unchanged in value and source:

- architecture components;
- feature formulas and thresholds;
- Table 4 split sizes (recomputed in memory from the deterministic generator for the original paper);
- deployed metrics (Table 5, Stage 2 rows);
- Table 6 Wilson intervals;
- Attack Lab table;
- flow-feature Table 8 and the decision-rule values;
- Experiment 5 Table 9 and its latencies;
- the 61 test functions;
- the exploratory persistence numbers;
- the original 27 references.

## Figures

| Figure | Source |
|---|---|
| 1, 2, 4, 5 (new diagrams) | `research_paper/revised/build/make_revised_figures.py`; content from the code rows above |
| 3, 6–11 | copied unchanged from `research_paper/PrivAgent_Figures/` (generated from result files by `research_paper/build/make_figures.py`) |

## Claims deliberately not made

- no exactly-once delivery;
- no complete security;
- no production readiness;
- no novelty for combining mechanisms;
- no claim that recorded handoffs are scored;
- no claim that provenance is enforced;
- no detection-accuracy claim for misreporting;
- no claim that the proposed decision-precedence invariant is implemented;
- no confirmatory persistence claims.
