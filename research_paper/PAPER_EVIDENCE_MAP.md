# Paper evidence map

This map links every major claim in `PrivAgent_Research_Paper.md` to the code, raw data, result files or documents that support it. Paths are relative to the repository root.

## Evidence types

| Tag | Meaning |
|---|---|
| **CODE** | read directly from source code |
| **RESULT** | a stored experiment output |
| **EVID** | a file copied into `research_paper/evidence/` from the earlier session's scratch folder (see below) |
| **SNAP** | the frozen exploratory persistence snapshot |
| **LOG** | the development session log only (Claude Code transcript `0f0c970c-…jsonl`). Not a repository artifact; weaker evidence; marked in the paper where used |
| **RECOMP** | recomputed for this paper from stored outputs, or from the deterministic generator in memory, with no files written |
| **CITE** | verified online on 2026-11-10 |

**About the EVID files.** They were copied from the earlier session's scratch folder:

```
~\AppData\Local\Temp\claude\8143d54a3b4f9ca3\0f0c970c-8484-43ab-a070-6fa933b3819e\scratchpad\
```

That folder is temporary and may be deleted. Hashes are in `research_paper/evidence/SHA256SUMS.txt`.

**Working title.** The user's working title was "PrivAgent: Trajectory-Aware Runtime Governance and Provenance-Based Security for Multi-Agent LLM Systems". The manuscript uses a revised title, because provenance-based sensitivity is shadow-mode only. It is not an enforced security mechanism.

**No earlier paper in the repository.** The README refers to an earlier "PrivAgent research paper". No such paper exists in the repository, so nothing in the manuscript relies on it.

---

## Architecture and implementation (Sections 3–5)

| Claim | Evidence | Type |
|---|---|---|
| Four agents in a linear LangGraph pipeline; scripted LLM injectable | `agents/graph.py` (`build_graph`), `agents/llm.py` | CODE |
| Four MCP stdio servers; tool→server routing; one background event-loop thread; list reconstruction | `agents/mcp_client.py` (`SERVERS`, `TOOL_TO_SERVER`, `SINGLE_OBJECT_TOOLS`), `mcp_servers/*/server.py` | CODE |
| Single interception point; blocked actions not appended; per-run sequence numbers are metadata | `governance/trajectory_monitor.py` (`evaluate`, `_next_event`) | CODE |
| Shared feature module; look-ahead refused | `governance/features.py`, `governance/risk_engine.py:49-54` | CODE |
| Deployed features = `trajectory_invariant` (11 features) | `models/feature_config.json` | RESULT |
| Gradient boosting with 200 estimators, depth 5, learning rate 0.1 | `models/train_models.py:56-61` | CODE |
| Feature formulas (counts, maxima, `max_prev_risk = max(dest)/2`) | `governance/features.py:140-154` | CODE |
| Thresholds 0.22 / 0.50 / 0.85 | `models/thresholds.json` | RESULT |
| Deployed model equals the frozen baseline | `diff models/training_metrics.json models/baselines/trajectory_invariant_v1/training_metrics.json` gives no difference; hashes in `snapshots/pre_persistence_eval_20261109/MANIFEST.sha256` | RESULT |
| Three policy rules; a fired rule replaces the ML decision | `governance/policy_engine.py`; `trajectory_monitor.py:_decide` | CODE |
| RESTRICTED is executed like AUTONOMOUS | `ALLOWED_DECISIONS` in `trajectory_monitor.py:45`; no special handling in `agents/tools.py` | CODE |
| Provenance refs, HMAC fingerprints kept out of logs, item labels with their basis, `unregistered` refs | `governance/provenance.py` | CODE |
| `combine()`; unknown treated as sensitive; the authoritative label is the max of provenance and declaration; flags | `governance/sensitivity.py` | CODE |
| PII regex detectors with Luhn check | `governance/sensitivity.py:assess_text` | CODE |
| Six handoff events, read-only, errors caught, shadow mode | `agents/handoffs.py`, `agents/graph.py:observe` | CODE |
| Sensitivity mode defaults to shadow and is never set to enforce in the application | `trajectory_monitor.py:86`; `grep sensitivity_mode` finds `enforce` only in tests | CODE |
| Approval graph is opt-in; four writer nodes; digests; token; ledger claim before the call | `agents/graph.py:75-90`, `agents/approval_flow.py`, `governance/approval.py` | CODE |
| Flow rule `sensitive_crossed_agent_boundary_to_external` is escalation-only | `governance/approval.py:58-85,155-199` | CODE |
| Action digest fields; `authorize()` does not re-check destination, tool or server | `governance/approval.py:168-176,272-289`; `experiments/secure_persistence/PC1_PC2_IMPLEMENTATION_PLAN.md` | CODE |
| AES-GCM, strict MsgPack, owner-only permissions, `durability="exit"` | `governance/checkpoint_store.py`; `agents/approval_flow.py:178-181` | CODE |
| Three JSONL logs; append-only by convention | `governance/audit_logger.py` | CODE |
| Live tool calls are only internal reads or external sends | `agents/tools.py` (`destination_category` arguments) | CODE |
| The Research Assistant page uses the default graph, without approvals | `dashboard/page_research.py:55` | CODE |
| A Human Approval page exists and is exercised by a Streamlit AppTest on synthetic demo runs | `dashboard/page_approval.py`, `dashboard/review_queue.py`, `tests/test_dashboard_changes.py:test_approval_page_lists_and_approves` | CODE |
| LangGraph hazards: node restart, unknown-thread resume, `Command(resume=None)`, no checkpointer | `agents/approval_flow.py` docstrings and `submit_review`; probe results in the development log | CODE + LOG |
| Software versions | `experiments/secure_persistence/results/environment.json` | RESULT |

## Experiment 1: evaluation correction

| Claim | Evidence | Type |
|---|---|---|
| Stage 0 trajectory model: P 0.998, R 1.000, F1 0.999, AUROC 1.000 | `research_paper/evidence/stage0_original_training_metrics.json` | EVID |
| Stage 0 thresholds 0.15 / 0.40 / 0.65 | `research_paper/evidence/stage0_original_thresholds.json` | EVID |
| The original README reported "f1 0.99" | development log (original README text) | LOG |
| Trajectory ID set per row (`len(rows)`); row-level split; thresholds tuned on training data; held-out never scored; tool-ID collision | development log (code review and fix report). The defective code was not preserved | LOG |
| Stage 1: test F1 1.000; held-out types P 0.796, R 0.559, F1 0.657, AUROC 0.905; thresholds 0.39 / 0.40 / 0.65 | `research_paper/evidence/stage1_corrected_eval_training_metrics.json` | EVID |
| Stage 2 (deployed) metrics in Table 2 and the abstract | `models/training_metrics.json` (`trajectory_level`) | RESULT |
| Split sizes in Table 1 (runs, steps, unsafe steps) | `generate_dataset(write_csv=False)` + `split_by_trajectory` run in memory with seed 42; the 507 test unsafe steps match the per-type sum in `training_metrics.json` | RECOMP |
| Per-type runs caught: `path_cross_agent_leak` 6/107, variant `path_exfiltration` 2/48, variant `path_privilege_escalation` 6/57, `data_exfiltration` 101/101, `cascading_failure` 92/92 | `runs_caught` × (unsafe_steps / unsafe stages per template) from `training_metrics.json`; unsafe stages per template from `template_labels` (3, 2, 2, 1, 3) | RECOMP |
| Benign-run false alarms 17/346, 11/300, 16/300 with Wilson CIs | `benign_run_false_alarm` × benign runs per set (Table 1); `scipy.stats.binomtest(...).proportion_ci("wilson")` | RECOMP |
| Per-step FPR 0.8% on test | `training_metrics.json` `test.fpr` = 0.0079 | RESULT |

## Experiment 2: position shortcut

| Claim | Evidence | Type |
|---|---|---|
| Position-only validation AUROC 0.951 (legacy), 0.856 (randomized); randomized AUPRC 0.244 | `experiments/results/position_ablation.json` → `investigation.*.position_only_val_auroc`; `models["randomized/position_only"].val_auprc` | RESULT |
| Unsafe steps at 1–3 distinct positions (legacy) | `position_ablation.json` → `investigation.legacy.distinct_unsafe_positions` | RESULT |
| Ratio features recover the step index with R² 0.721 (legacy) and 0.747 (randomized) | `position_ablation.json` → `step_index_recovered_val_r2` | RESULT |
| Run lengths 4–7 (attack) and 4–10 (benign) on legacy data | `position_ablation.json` → `investigation.legacy.run_length` | RESULT |
| Selection rule and result (`trajectory_invariant`, validation AUPRC 0.9702 against 0.896) | `position_ablation.json` → `selection` | RESULT |
| Table 3 rows | `experiments/results/position_ablation.md` summary table | RESULT |
| Round 1 selected `trajectory_no_position`; its Attack Lab missed 2 path attacks | `experiments/results/round1_position_ablation.md`, `round1_attack_lab_replay.md` | RESULT |
| Recall by position bin (Figure 5) | `position_ablation.json` → `models[...].test_by_position` | RESULT |
| Sweep catch share 0.889; misses `path_cross_agent_leak` at every offset | `position_ablation.json` → `models["randomized/trajectory_invariant"].position_sweep` | RESULT |
| Score range 0.000 under neutral-step insertion | `phase3_flow_features.json` → `invariance_score_range` (baseline 0.0) | RESULT |
| Round 1 against deployed on `path_cross_agent_leak` and path variants | `position_ablation.md` per-type table (`randomized/trajectory_no_position` column) | RESULT |
| Legacy-trained `trajectory_invariant` types F1 0.804, not selected | `position_ablation.md` row `legacy/trajectory_invariant` | RESULT |
| Permutation importance values | `position_ablation.json` → `permutation_importance_val_auprc_drop` | RESULT |
| Live scoring matches training rows exactly | `tests/test_feature_consistency.py` | CODE (test) |

## Experiment 3: flow features

| Claim | Evidence | Type |
|---|---|---|
| Seeds 42, 7, 1234; training and validation data only | `experiments/phase3_flow_features.py` docstring; `phase3_flow_features.json` → `seeds` | CODE / RESULT |
| Table 4 means | `experiments/results/phase3_flow_features.md` summary | RESULT |
| Per-seed SDs 0.009 / 0.029 / 0.011 | recomputed from `phase3_flow_features.json` → `per_seed[*][cand].loto[*].auprc` | RECOMP |
| Decision-rule gains 0.015 ± 0.026 and 0.024 ± 0.027; both fail check (b); the baseline is preferred | `phase3_flow_features.md` → Decision rule | RESULT |
| LOTO per-type values (`prompt_injection` 1.00 → 0.77/0.93, and so on) | `phase3_flow_features.md` → leave-one-type-out table | RESULT |
| The retrained baseline reproduces the frozen model | `phase3_flow_features.json` → `frozen_baseline.retrained_baseline_reproduces_frozen_model = true` | RESULT |
| No rich model deployed | `models/feature_config.json` lists `trajectory_invariant` | RESULT |
| Candidate flow rules flag 11–24% of benign and 70–88% of attack runs; about 1% of benign steps match the path rule | development log (trade-off analysis); script output not stored | LOG |

## Attack Lab (Section 7.4)

| Claim | Evidence | Type |
|---|---|---|
| Table 5; 6 of 7 caught, ML-only also 6 of 7 | `experiments/results/attack_lab_replay.md` | RESULT |
| Replay identical to the frozen baseline | `diff experiments/results/attack_lab_replay.md models/baselines/trajectory_invariant_v1/results/attack_lab_replay.md` gives no difference | RESULT |
| Seven attacks plus one benign scenario | `governance/attack_scenarios.py:SCENARIOS` | CODE |
| Rule 2 relaxes ML BLOCKED to HUMAN_APPROVAL (three steps) | `attack_lab_replay.md` per-scenario tables | RESULT |

## Experiments 4 and 5: provenance, sensitivity, approval

| Claim | Evidence | Type |
|---|---|---|
| Handoff test coverage (15 tests), including on/off byte-identical behaviour | `tests/test_handoff_instrumentation.py` | CODE (test) |
| Sensitivity test coverage (11 tests) | `tests/test_sensitivity_authority.py` | CODE (test) |
| Table 6 and the outcome counts | `experiments/results/approval_evaluation.md` / `.json` → `outcomes`, `approval_metrics` | RESULT |
| Latency: gate 0.18–0.19 ms; added 9.6–31.0 ms | `approval_evaluation.json` → `approval_metrics.*.mean_gate_overhead_ms`, `median_overhead_ms_uninterrupted_runs` | RESULT |
| The approval evaluation used the persistent development store | `experiments/approval_evaluation.py` (`DevApprovalStore`) | CODE |

## Integration tests (Section 6.6, 7.6)

| Claim | Evidence | Type |
|---|---|---|
| 61 test functions across 6 suites | `grep -c "^def test" tests/*.py`: 2 + 15 + 11 + 16 + 7 + 10 | CODE |
| All suites passed in their last run (2026-11-09); not re-run for this paper | development log (test runs on 2026-11-09) | LOG |
| The test name `test_approval_resumes_and_executes_exactly_once` | `tests/test_human_approval.py:147` | CODE |

## Persistence study (Section 7.7), exploratory

| Claim | Evidence | Type |
|---|---|---|
| Frozen snapshot, 84-file manifest | `snapshots/exploratory_persistence_v1_20261109/{MANIFEST.sha256,SNAPSHOT.md}` | SNAP |
| 5,070 rows; 2,940 independent runs | `experiments/secure_persistence/EXPLORATORY_AUDIT.md` §2; `audit/output/facts.json` → `units` | RESULT |
| 900/900 pending request recovered | `audit/output/checks.csv` 1.4A–F | RESULT |
| Crash after send, without the ledger: 30/30 duplicates per configuration; with the ledger: 0/120 duplicates, 120/120 `executing` | checks 1.3, 1.6; `CORRECTIONS.md` C3, C4 | RESULT |
| Double-click 25/30 (A), 30/30 (F), 0/120 with the ledger | check 2.1–2.2; `CORRECTIONS.md` C5 | RESULT |
| Canary counts B 0/18 raw and 2/18 decrypted; E 18/18 decrypted; A 18/18 raw after purge | checks 3.1; `REPORT.md` B2 | RESULT |
| Encrypted configurations refuse 4 tampering manipulations 30/30; key failures reported separately; byte flip without encryption 59/60 loaded and sent | check 4.1; `CORRECTIONS.md` C1 | RESULT |
| Probe constructed 30/30 (D, key holder) against 0/30 (B) | check 5.1 | RESULT |
| +37.1% [31.7, 43.0]; F +1.2% | `REPORT.md` B6; checks 7.3 | RESULT |
| Exploratory status; v1.2 amendment pending; PC1 and PC2 unimplemented | `preregistration.md`, `preregistration_v1.2.md`, `PREREGISTRATION_HASHES.md`, `CONFIRMATORY_PROTOCOL.md` | RESULT |
| Constant associated data; snapshot rollback; ambiguous `executing`/`failed`; recipient without idempotency key | `preregistration.md` §4a; `LEDGER_RECOVERY_ANALYSIS.md`; `mcp_servers/external_server/server.py` | CODE / RESULT |

## Related work (Section 2): citation verification (2026-11-10)

| Ref | What was verified | How |
|---|---|---|
| [1] | Anthropic MCP announcement dated 25 Nov 2024 | Anthropic news listing and contemporaneous reports |
| [2] | MCP specification revision 2025-06-18 | modelcontextprotocol.io |
| [3] | LangGraph `interrupt()` and checkpointer requirement | docs.langchain.com |
| [4] | AISec 2023, pp. 79–90, authors | CISPA and researchr records |
| [5] | Findings of ACL 2024, authors, 1,054 cases | ACL Anthology / arXiv 2403.02691 |
| [6] | NeurIPS 2024 Datasets and Benchmarks; authors; 97 tasks / 629 cases | NeurIPS proceedings; arXiv 2406.13352 abstract page |
| [7] | Authors; arXiv 2503.18813; no venue listed | arXiv abstract page |
| [8] | Authors; arXiv 2505.23643; no venue listed | arXiv abstract page |
| [9] | Authors; arXiv 2410.03055 v1–v3; TMLR per the Microsoft Research listing (OpenReview not checked) | arXiv; MSR listing |
| [10] | AGATE title, nine authors, 25 Sep 2026, cs.CR, no venue; evaluation summary | arXiv abstract page |
| [11] | CapAgent title, authors, BDCC 10(9):293, DOI | publisher listings via search; **full text blocked (HTTP 403)** |
| [12] | Agent-BOM paper title, 12 authors, v1 May 2026 / v2 Oct 2026, no venue | arXiv abstract page |
| [13] | PCAA single author, 2 Jun 2026, no venue | arXiv abstract page |
| [14] | Progent authors, arXiv 2504.11703 | arXiv listing (search) |
| [15] | IsolateGPT, NDSS 2025, authors | NDSS paper page; arXiv |
| [16] | Agent-Sentry authors, arXiv 2603.22868 | arXiv and secondary listings; the author list differs between versions |
| [17]–[24], [26] | bibliographic details | publisher and repository records via search |
| [25], [27] | Wilson 1927; RFC 2104 | standard references, not re-checked online in this session |

Concurrent work found but not cited in detail: AgentCap (arXiv 2611.00729), AgentFlow (arXiv 2608.22868), APPA (arXiv 2607.24625). They were identified by search only and not read.

## Figures

| Figure | Source | Generator |
|---|---|---|
| 1–3 (diagrams) | the code paths listed above | `research_paper/build/make_figures.py` (`fig_architecture`, `fig_lifecycle`, `fig_decision`) |
| 4 | EVID stage 0 and 1; `models/training_metrics.json` | `fig_eval_correction` |
| 5 | `position_ablation.json` | `fig_position` |
| 6, 7 | `phase3_flow_features.json` | `fig_phase3` |
| 8 | `approval_evaluation.json` | `fig_approval` |
| 9 | copied unchanged from `snapshots/exploratory_persistence_v1_20261109/files/secure_persistence/analysis/figures/` | `copy_persistence` |

## Claims deliberately not made

- No claim of exactly-once delivery, complete security, or universal attack prevention.
- No claim that a rich flow-feature model replaced the frozen baseline.
- No claim that provenance-based sensitivity is enforced.
- No claim of a working human-approval interface for live use.
- No claim of production readiness.
- No claim of novelty for the combination of established mechanisms.
- Exploratory persistence findings are not presented as confirmatory.
