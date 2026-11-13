# Claim–evidence ledger: PrivAgent Research Paper (final, editorially audited 11 Nov 2026)

**Verification status:**

| Status | Meaning |
|---|---|
| VERIFIED-RECOMP | recomputed on 11 Nov 2026 from the saved model and the deterministic generator; matches the stored values |
| VERIFIED-FILE | matches a stored result, log or evidence file (checked against the file) |
| VERIFIED-CODE | confirmed by reading the source code |
| DEVLOG-ONLY | recorded only in the development log; labelled as such in the manuscript |
| NOT-RECOMPUTABLE | stored evidence only; the historical generator was not preserved |
| PROPOSAL | stated as future work, not implemented |
| LIT | from a verified publication |

| # | Claim | Manuscript location | Supporting artifact | Verification status | Editorial action |
|---|---|---|---|---|---|
| 1 | Original F1 0.999 (P 0.998, R 1.000, AUROC 1.000), from a row-level split | Abstract; §7.1.1 A; Table 5 | `research_paper/evidence/stage0_original_training_metrics.json` | NOT-RECOMPUTABLE (file matches) | abstract now labels it Stage 0 and states that the stages are not comparable |
| 2 | Stage 1 held-out-types F1 0.657 (P 0.796, R 0.559, AUROC 0.905) on the legacy generator | Abstract; Table 1; §7.1.1 A; Table 5 | `research_paper/evidence/stage1_corrected_eval_training_metrics.json` | NOT-RECOMPUTABLE (file matches) | "fell to … then reaches" wording removed; Table 1 cell labels Stage 0 / Stage 1 |
| 3 | Deployed step-level F1 0.912 / 0.665 / 0.493 (test / held-out types / variants) | Abstract; Table 5; §8; §9; §11 | `models/training_metrics.json` | VERIFIED-RECOMP (0.9115, 0.6649, 0.4928) | abstract states these are Stage 2 and not a continuation of Stage 1 |
| 4 | Deployed P/R/AUROC: test 0.881/0.945/0.998; held-out 0.857/0.543/0.984; variants 0.857/0.346/0.986 | Table 5 | `models/training_metrics.json` | VERIFIED-RECOMP | none |
| 5 | 6/107 `path_cross_agent_leak` runs caught; step recall 0.019 | Abstract; Table 6; §4.9; §7.1.2; §8; §9; §11 | `models/training_metrics.json` (`runs_caught` 0.0561; 321 unsafe steps ÷ 3 = 107 runs; recall 0.0187) | VERIFIED-RECOMP | step recall and run-level definition added to the abstract |
| 6 | 101/101 and 92/92 runs of two held-out direct types caught | Abstract; Table 6; §8 | `models/training_metrics.json` | VERIFIED-RECOMP | abstract now says "at run level" |
| 7 | Variant runs caught 2/48, 6/57; benign false alarms 17/346, 11/300, 16/300; Wilson CIs | Table 6; §4.10 (3.7–5.3%) | `models/training_metrics.json`; Wilson computation | VERIFIED-RECOMP | 3.7–5.3% range cited in the new §4.10 trade-off text (benign-run alarms on held-out and variant sets; test 4.9% lies inside) |
| 8 | Step FPR on test 0.8% | §7.1.2 | `training_metrics.json` (fpr 0.0079) | VERIFIED-RECOMP | none |
| 9 | Position-only AUROC 0.951; ratio R² 0.72; recall 0.84 → 0.00; invariance range 0.000; recall 0.89–1.00 | §7.1.1 B | `experiments/results/position_ablation.json`, `phase3_flow_features.json` | VERIFIED-FILE | none |
| 10 | Same send ≈0.04 at step 3 vs ≈1.0 at step 5 | §7.1.1 B | development log | DEVLOG-ONLY (labelled in text) | none |
| 11 | `trajectory_invariant` selected by validation AUPRC 0.970 vs 0.896 action-only | §7.1.1 B | `position_ablation.md` | VERIFIED-FILE | none |
| 12 | Round 1 vs deployed trade-off table (0.36/0.84; 0.74–0.96; 0.763; 0.667) | §7.1.1 C | `position_ablation.md` | VERIFIED-FILE | none |
| 13 | Permutation importance 0.752 (`data_sensitivity`), 0.330 (`destination_category`) | §7.1.1 C | `position_ablation.json` (`permutation_importance_val_auprc_drop`: 0.7517, 0.3303) | VERIFIED-FILE | none |
| 14 | Prefix-feature importances 0.049 (`prev_sensitive_reads`), 0.025 (`max_sensitivity`) | §8 RQ1 (new) | same field: 0.0492, 0.0251 | VERIFIED-FILE | added to replace the unsupported opening "Trajectory context does change risk assessment" |
| 15 | Legacy-trained invariant model held-out F1 0.804, not selected | §7.1.1 C | `position_ablation.md` | VERIFIED-FILE (carried from previous validation) | none |
| 16 | Attack Lab: 6/7 caught (full and ML-only); path attacks caught by ML only; `path_cross_agent_leak` missed; round 1 caught 4/7; not blind | §7.1.3; Table 7; §8 | `experiments/results/attack_lab_replay.md`, `round1_attack_lab_replay.md`; `experiments/attack_lab_replay.py` | VERIFIED-FILE; replay byte-identical on 11 Nov (TEST-11NOV) | §8 now cites "caught by the model and not by the rules" for the two training-type path attacks |
| 17 | Flow-feature Table 8 values and gains 0.015 (SE 0.026), 0.024 (SE 0.027) | §7.1.4 | `experiments/results/phase3_flow_features.json` / `.md` | VERIFIED-FILE | none |
| 18 | Table 4 split sizes | Table 4 | in-memory regeneration (seed 42) | VERIFIED-RECOMP | none |
| 19 | Thresholds 0.22 / 0.50 / 0.85 tuned on validation only | §4.5 | `models/thresholds.json`; `tune_thresholds` reproduces | VERIFIED-RECOMP | none |
| 20 | 11 features of `trajectory_invariant`; 200 trees, depth 5 | §4.4 | `models/feature_config.json`; saved model | VERIFIED-RECOMP / VERIFIED-CODE | none |
| 21 | Rule order R1, R2, R3; a fired rule replaces the ML decision | §4.6; §4.10 | `policy_engine.py:evaluate`; `trajectory_monitor.py:_decide` | VERIFIED-CODE | none |
| 22 | Downgrade: `demo_9e6a8ae2` ML score 0.9952 ≥ 0.85, final HUMAN_APPROVAL via `policy_engine`, reviewer rejected, nothing sent | §4.10 | `logs/audit_log.jsonl`; `logs/approval_log.jsonl` | VERIFIED-FILE | none |
| 23 | Downgrade in Attack Lab, three scenarios, scores 0.995–0.999 | §4.10 | `attack_lab_replay.md` details | VERIFIED-FILE | none |
| 24 | "Combining a learned classifier with deterministic policy rules does not automatically produce a safer system" | §4.10 (new); §11 | follows from claims 21–23 | interpretation supported by VERIFIED-CODE + VERIFIED-FILE | added as an explicit finding, with trade-off discussion |
| 25 | Proposed invariant "BLOCKED never automatically downgraded" | §4.10; §10 | none (proposal) | PROPOSAL | scoped to sensitive external transmissions; "more restrictive" rule now allows a logged exception; unmeasured cost stated |
| 26 | ML decision not logged as a separate field | §4.10 | `audit_logger.py:record` | VERIFIED-CODE | none |
| 27 | Misreporting demos `demo_cc0f5f9e`, `demo_89c31726`: enforced 0.0 → AUTONOMOUS; shadow 0.9952 → HUMAN_APPROVAL; `would_change_outcome` true; escalated by flow rule, approved, executed | Abstract; §4.8 (new table); §7.2; §8 | `logs/audit_log.jsonl`; `logs/approval_log.jsonl` | VERIFIED-FILE | abstract now states that both sends were approved and executed |
| 28 | Test-scenario misreport ≈0.0000005 vs ≈0.9995 | §7.2 Table 9 | development log; `tests/test_sensitivity_authority.py` asserts shadow > enforced | DEVLOG-ONLY (labelled) | none |
| 29 | Provenance identifies / detects mismatch / records / does not prevent in the default pipeline | §4.8 (new table) | `governance/provenance.py`; `trajectory_monitor.py` (`sensitivity_mode="shadow"`); `governance/approval.py` flow rule | VERIFIED-CODE | added |
| 30 | `enforce` mode exists, tested only, not enabled in the application | §4.8 | `trajectory_monitor.py`; `tests/test_sensitivity_authority.py` | VERIFIED-CODE | none |
| 31 | Handoffs recorded, provenance propagated, handoffs not scored; live actions never `cross_agent` | §4.9 | `agents/handoffs.py`; `trajectory_monitor.py`; `agents/tools.py` | VERIFIED-CODE | none |
| 32 | 6/107 is an offline generalisation failure, separate from the live handoff exclusion | §4.9 | `data/generate_trajectories.py` (`path_cross_agent_leak` contains `cross_agent` actions) | VERIFIED-CODE | none (already separated) |
| 33 | Resumed runs lack the transmission handoff event (0 of 3) | §4.7 | `logs/handoff_log.jsonl` | VERIFIED-FILE | none |
| 34 | E5 totals: attacks executed 2 / 0 / 3 of 4; benign completed 1 / 2 / 2 of 2 | Abstract; §7.3; §8 | `experiments/results/approval_evaluation.json` / `.md` | VERIFIED-FILE | abstract now includes the unmodified-pipeline 2/4 |
| 35 | E5: 4 approval requests; gate 0.18–0.19 ms; non-pausing runs 9.6–31.0 ms longer | §7.3 | `approval_evaluation.md` | VERIFIED-FILE (carried from previous validation) | none |
| 36 | "Human approval is a control point, not an independent security guarantee" | §7.3 (new) | interpretation of claim 34 and the binding limitation (§4.11) | interpretation | added |
| 37 | Ledger: at most one execution attempt per action ID; no exactly-once delivery | §4.11; §7.4 | `governance/approval.py` ledger; persistence snapshot (0/120 vs 30/30) | VERIFIED-CODE; exploratory snapshot (manifests verified) | none |
| 38 | Experiment infrastructure: E1–E3 offline; Attack Lab, E4, E5, approval/restart tests use the real MCP stdio servers with synthetic data and a scripted LLM or scripted action sequence; persistence used an in-process synthetic MCP stand-in | §6 (new) | `tests/test_handoff_instrumentation.py` docstring and `run`; `tests/test_sensitivity_authority.py` reuses it; `experiments/approval_evaluation.py`; `governance/attack_scenarios.py` via `tools._governed_call`; `experiments/secure_persistence/harness.py:51` (`SyntheticMCP`) | VERIFIED-CODE | replaces the blanket "every experiment uses synthetic data and scripted components" sentence |
| 39 | 61/61 tests passed; Attack Lab byte-identical (11 Nov 2026) | Table 3 E6 | `FINAL_RESEARCH_VALIDATION_REPORT.md` §F | TEST-11NOV | none |
| 40 | Wang et al.: single-agent PEP; R01–R05; SI/DS labels; hash chain; 1,050 runs; ASR 40.0% → 5.0% vs 35.0%; ΔFNR 26.4 pp; mock tools plus preliminary real stdio server; REQUIRE_CONFIRM treated as block | §2.3; Table 2 | [28], full text read 10 Nov 2026 | LIT | overlap sentence replaced by a statement of different research questions; explicit no-outperformance statement added |
| 41 | CaMeL, FIDES, Progent have no venue as of 10 Nov 2026; IsolateGPT at NDSS 2025 | §2.2; refs | searches 10 Nov 2026 | LIT | none |
| 42 | Persistence: 2,940 runs; confirmatory study not run; PC1/PC2 unimplemented | §7.4 | `snapshots/exploratory_persistence_v1_20261109/` | VERIFIED-FILE (exploratory) | none |

## Unresolved items

| Item | Why unresolved | Treatment in manuscript |
|---|---|---|
| Whether E5's two policy-escalated scenarios involved an ML BLOCKED | E5 stores no risk score | stated as unverifiable (§4.10, §9) |
| Stage 0 and Stage 1 metrics cannot be recomputed | historical generator versions not preserved | labelled as preserved evidence |
| ≈0.0000005 / ≈0.9995 test values and the ≈0.04 / ≈1.0 positional example | development log only | labelled DEVLOG in the text |
| ~1% of benign steps matching the path rule | development observation, not stored | labelled in §9 A1 |
| Permissive IFA [9] venue | OpenReview not checked | stated in the reference |
