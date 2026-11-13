# PrivAgent: Final Research Validation Report

| | |
|---|---|
| Date | 11 November 2026 |
| Scope | closing validation of the current research phase |
| Final manuscript | `research_paper/final/PrivAgent_Research_Paper_Final.md` / `.pdf` |

**Method.** This was a validation, not a development cycle:

- no production code, model, threshold, dataset, frozen snapshot or pre-registration was changed;
- no model was retrained;
- the persistence confirmatory study was not started;
- nothing was committed.

**How the tests ran.** Test suites and the Attack Lab replay ran in an **isolated copy** of the repository, made in a temporary scratch directory, so existing logs and results could not be touched. SHA-256 hashes of 58 tracked files (logs, runtime, result files, models, both papers, the revised directory, both pre-registration files) were recorded before the validation and re-checked after it: **58/58 unchanged**.

---

## A. Project completion summary

**Table A1. Functionality inventory.** "Implemented" does not mean "validated"; the last column states the strongest evidence that exists.

| Functionality | Implemented | Status | Strongest evidence |
|---|---|---|---|
| Four-agent LangGraph pipeline (orchestrator, retriever, analyst, writer) | yes | default | integration tests (scripted LLM) |
| Four MCP stdio servers with synthetic data | yes | default | integration tests; Attack Lab replay |
| Single interception point, trajectory prefix, audit log | yes | default | functional tests |
| Gradient-boosted risk model (`trajectory_invariant`, 11 features), thresholds 0.22 / 0.50 / 0.85 | yes | default | **controlled experiments** on synthetic data (E1–E3); metrics recomputed 11 Nov |
| Three deterministic policy rules (replace the ML decision when they fire) | yes | default | Attack Lab demonstration; functional tests |
| RESTRICTED autonomy level | name only | default | executes like AUTONOMOUS; no restriction implemented |
| Provenance registry (HMAC-fingerprinted refs, label inheritance) | yes | **shadow** | functional tests (E4); controlled demonstrations |
| Handoff instrumentation (6 event types) | yes | **shadow**; not in the scored trajectory | functional tests; persisted logs |
| Provenance-authoritative sensitivity for `send_result` | yes | **shadow** (enforce mode exists, unit-tested, not enabled) | controlled demonstrations (development log; 2 stored demo runs) |
| User-input PII regex assessment | yes | shadow (feeds provenance) | unit tests |
| Human-approval graph (interrupt, digests, signed token, flow rule) | yes | **opt-in** | controlled evaluation (E5, 8 scenarios); functional tests |
| Execution ledger (at most one execution attempt per action ID) | yes | opt-in | functional tests; exploratory persistence study |
| Encrypted SQLite checkpoint store | yes | opt-in, development use only | functional tests; **exploratory** study |
| Human Approval dashboard page | minimal | opt-in; not wired to the live Research Assistant page | Streamlit AppTest on synthetic demo runs; no reviewer study |
| Decision-precedence invariant (BLOCKED never relaxed) | **no** | proposed | – |
| Live handoffs in the scored trajectory | **no** | proposed | – |
| Pre-send binding of destination, tool and server (PC1); canonical digests (PC2) | **no** | proposed | – |
| Confirmatory persistence study | **no** | pre-registered (v1.1; v1.2 awaiting approval) | – |

**Categories, by type of evidence:**

- **Experimentally demonstrated** (controlled, synthetic):
  - leakage correction and the held-out results;
  - removal of the positional shortcut;
  - flow-feature trade-offs;
  - approval outcomes under two simulated reviewers.
- **Shadow mode:** provenance labels, handoff events, the authoritative sensitivity label.
- **Opt-in:** the approval graph, ledger, encrypted store and approval page.
- **Exploratory:** all persistence findings.
- **Unresolved limitations:** Section D.
- **Proposed future work:** Section G.

---

## B. Final experimental results

**Table B1. Trajectory model, step-level metrics at each stage's stop threshold.** The sets differ between stages and are not directly comparable.

| Stage | Data / split | Set | P | R | F1 | AUROC | Reproduced 11 Nov? |
|---|---|---|---|---|---|---|---|
| 0, historical (original) | legacy, **row** split, thresholds on train | test | 0.998 | 1.000 | **0.999** | 1.000 | no: historical generator not preserved; value from `research_paper/evidence/` |
| 1, corrected | legacy, run split | test (seen types) | 1.000 | 1.000 | 1.000 | 1.000 | no (same reason) |
| 1, corrected | legacy, run split | held-out types | 0.796 | 0.559 | **0.657** | 0.905 | no (same reason) |
| 2, deployed | randomized, run split | test (seen types) | 0.881 | 0.945 | 0.912 | 0.998 | **yes, exactly** |
| 2, deployed | randomized, run split | held-out types | 0.857 | 0.543 | **0.665** | 0.984 | **yes, exactly** |
| 2, deployed | randomized, run split | held-out variants (tool-swapped) | 0.857 | 0.346 | **0.493** | 0.986 | **yes, exactly** |

**What these metrics measure:**

- **Precision:** the share of stopped steps (r ≥ 0.50) that are truly unsafe.
- **Recall:** the share of unsafe steps that are stopped.
- **F1:** their harmonic mean.
- **AUROC:** threshold-free ranking quality, i.e. the probability that a random unsafe step scores above a random safe step.

All four are **step-level**, and steps within a run are not independent.

**Table B2. Deployed model, run-level results** (Wilson 95% CIs; reproduced exactly).

| Set | Measure | Result | 95% CI |
|---|---|---|---|
| held-out types | `data_exfiltration` runs caught | 101/101 | [0.963, 1] |
| held-out types | `cascading_failure` runs caught | 92/92 | [0.960, 1] |
| held-out types | `path_cross_agent_leak` runs caught | **6/107** | [0.026, 0.117] |
| held-out variants | `path_exfiltration` / `path_privilege_escalation` runs caught | 2/48 / 6/57 | [0.012, 0.140] / [0.049, 0.211] |
| test / types / variants | benign runs with any step stopped | 17/346 / 11/300 / 16/300 | [0.031, 0.077] / [0.021, 0.064] / [0.033, 0.085] |

"Runs caught" means an attack run had at least one unsafe step scored ≥ 0.50 in the **offline** evaluation.

**Table B3. Position shortcut (E2) and flow features (E3).**

| Result | Value | Source |
|---|---|---|
| Position-only validation AUROC (legacy) | 0.951 | `position_ablation.json` |
| Stage-1 model recall, prefix 0–4 against ≥ 20 | 0.84 against 0.00 | `position_ablation.json` |
| Deployed model: score change under 0–20 inserted steps | 0.000 | `phase3_flow_features.json` |
| Round 1 (`trajectory_no_position`): held-out types F1 / variants F1 | 0.763 / 0.667 | `position_ablation.md` |
| LOTO AUPRC: baseline / `rich_invariant` / `rich_invariant_no_tool` | 0.801 / 0.816 / 0.825 | `phase3_flow_features.md` |
| Gain ± SE (`rich_invariant`; `rich_invariant_no_tool`) | 0.015 ± 0.026; 0.024 ± 0.027, both failing the rule, so the **baseline was retained** | same |
| Variant-C path recall: baseline / `rich_invariant_no_tool` | 0.004 / 0.476 | same |
| LOTO recall, `prompt_injection` left out: baseline / rich / rich-no-tool | 1.00 / 0.77 / 0.93 | same |

**Table B4. Attack Lab (demonstration, re-run 11 Nov).** Full governance caught 6 of 7 attacks; ML-only also 6 of 7; the benign scenario was clean; `path_cross_agent_leak` was missed. The re-run output was **byte-identical** to the frozen baseline replay.

**Table B5. Human approval (E5; 8 scenarios, first run of each).**

| | Current pipeline | Accurate reviewer | Approve-all reviewer |
|---|---|---|---|
| Attack transmissions executed (of 4) | 2 | 0 | 3 |
| Benign sends completed (of 2) | 1 | 2 | 2 |

**Table B6. Provenance misreporting: two separate evidence sources, not combined.**

| Source | Enforced | Shadow | Status |
|---|---|---|---|
| A. Development-log example (test scenario `sensitive_send_misreported`) | ≈ 0.0000005 | ≈ 0.9995 | development log only; the test asserts shadow > enforced, the flag, and enforced = declared |
| B. Stored dashboard demo runs `demo_cc0f5f9e`, `demo_89c31726` | 0.0 (AUTONOMOUS) | 0.9952 (HUMAN_APPROVAL), `would_change_outcome = true` | persisted `logs/audit_log.jsonl`. The flow rule then escalated both; the reviewer **approved** both; both **executed** |

**Why A and B stay separate:**

- They come from different scenarios and runs (an automated test against interactive dashboard demos).
- They were recorded in different places (a development-log report against the persisted audit log).
- The audit log rounds scores to four decimals.
- Neither source is a detection-rate estimate.

---

## C. Research findings

**Strongest positive findings:**

- The leakage and shortcut corrections are **reproducible**: the deployed metrics recompute exactly from the saved model and the deterministic data.
- Position invariance holds by construction and empirically (score change 0.000).
- Every run of two held-out *direct* attack types is detected.
- Provenance instrumentation leaves agent behaviour byte-identical, and it exposes under-reported sensitivity in controlled runs.
- The approval workflow pauses before sending and permits at most one execution attempt per action ID.

**Strongest negative findings:**

- The original F1 of 0.999 was an evaluation artefact (held-out F1 0.657 after correction).
- The corrected model used a positional shortcut.
- The deployed model catches 6/107 runs of the held-out path attack, with variants F1 0.493.
- An approve-everything reviewer let through *more* attacks (3) than no approval step (2).
- In the stored demos, provenance-escalated misreported sends were approved and transmitted.

**Mixed findings:**

- Flow features improve path attacks and variant-C recall, and halve false alarms. They hurt left-out direct attacks and fail the pre-set rule.
- Removing the shortcut cost path-attack generalisation (round 1: 0.84 of runs caught, against 0.06 for the deployed model).

---

## D. Technical limitations (actual implementation gaps)

1. **Handoffs are recorded and propagated but not scored.** `cross_agent` never occurs in live scored trajectories. No live ML monitoring of cross-agent flow.
2. **Policy precedence.** A firing rule replaces the ML decision, so R2 can relax ML **BLOCKED** to HUMAN_APPROVAL. Confirmed from saved evidence in demo `demo_9e6a8ae2`:

   | Field | Value |
   |---|---|
   | Score | 0.9952 |
   | Derived ML decision | BLOCKED (≥ 0.85) |
   | Policy decision | HUMAN_APPROVAL (R2) |
   | Final enforced decision | HUMAN_APPROVAL, source `policy_engine` |
   | Approval outcome | offered for review, **rejected** |
   | Execution | `refused`; **no transmission** |

   The ML decision is not logged as its own field. Also seen in 3 Attack Lab scenarios.
3. **Provenance and sensitivity enforcement are shadow-only.** For outbound sends, the model and rules see the declared sensitivity. A misreported send after fewer than two sensitive reads is transmitted in the default pipeline (E5 `*_misreported`).
4. **Resumed approval runs lose handoff continuity.** The transmission event is missing in 3/3 paused-and-resumed demo runs, and delivery is logged under another run ID. This is new in this validation and is caused by in-memory state.
5. **Approval binding is incomplete.**
   - Destination, tool and server are not re-verified before sending (PC1).
   - Digests are not canonical (PC2).
   - The approval key shares the master key.
6. **Delivery semantics.**

   | Property | Status |
   |---|---|
   | **At most one execution attempt** per action ID | provided (functional tests; exploratory study: 0/120 duplicates with the ledger) |
   | **Confirmed external delivery** | not recorded by the system: only `executed` after a normal completion |
   | **Ambiguous delivery after a crash** at or after the claim (`executing` / `failed`) | real; cannot be resolved, because the external server has no idempotency key |
   | **Exactly-once delivery** | not provided and not claimed |

7. **RESTRICTED does nothing.** The audit log is not tamper-evident.
8. **Persistence limits:**
   - single SQLite writer;
   - key stored next to the data;
   - no context-bound encryption or rollback detection.

---

## E. Evidence quality

| Result | Classification |
|---|---|
| Any confirmatory result | **none exists** in this project |
| E1 evaluation correction; E2 position study; E3 flow features; E5 approval | controlled experiments on synthetic data. E2 and E3 used selection rules fixed in advance; E5's labels were fixed in advance |
| Attack Lab | demonstration (one replay per scenario; not blind) |
| Provenance misreporting | controlled mechanism demonstrations (two separate sources) |
| E4 instrumentation; E6 integration (61 tests) | functional tests: pass or fail, not security evaluations |
| Persistence study (2,940 independent runs) | **exploratory** |
| 0.04 against 1.0 positional example; 0.0000005 / 0.9995; candidate flow-rule rates; ~1% overlapping benign steps | development log only (weaker evidence) |

---

## F. Reproducibility

**Table F1. Existing test suites, re-run 11 Nov 2026** (isolated copy; Python 3.14.3; `-W default`).

| Suite | What it covers | Result | Time |
|---|---|---|---|
| `test_feature_consistency` (2) | live scores equal training rows; look-ahead refused | **passed** (`ok`) | 17 s |
| `test_handoff_instrumentation` (15) | trajectory monitoring, handoffs, provenance, shadow behaviour | **15/15** | 31 s |
| `test_sensitivity_authority` (11) | provenance and sensitivity assessment | **11/11** | 25 s |
| `test_human_approval` (16) | approval workflow, ledger, duplicate prevention, fail-closed | **16/16** | 30 s |
| `test_restart_recovery` (7) | separate-process restart, ledger, store | **7/7** | 276 s |
| `test_dashboard_changes` (10) | Attack Lab halt mode, approval page, local-only config | **10/10** | 34 s |
| **Total** | | **61/61 passed, 0 failed** | |

**Warnings (none affect results):**

- `ResourceWarning: unclosed database`, from SQLite connections in tests and the ledger. These are visible because warnings were enabled.
- Third-party deprecation warnings (starlette `multipart`, langsmith `asyncio.iscoroutinefunction`).

**Environmental limitations:**

- the tests use a scripted LLM (no Gemini key);
- MCP servers run locally over stdio;
- a single Windows machine.

**Table F2. Saved experiments.**

| Item | Reproduced? |
|---|---|
| Deployed metrics, per-type and run-level (Tables B1 Stage 2, B2) | **yes, exactly** (in memory; saved model; no retraining) |
| Validation-only thresholds | **yes**: re-tuning on validation predictions gives exactly 0.22 / 0.50 / 0.85 |
| Split integrity, IDs, feature configuration | **yes** |
| Attack Lab replay | **yes, byte-identical** to the frozen baseline |
| Stage 0 / Stage 1 metrics | **no**: historical generator versions were not preserved; values from preserved metric files |
| E2 position ablation, E3 flow features, E5 approval | not re-run (stored results audited; a full re-run would regenerate result files and was out of scope) |
| Persistence study | not re-run (frozen; audited earlier: 67/71 checks matched, 4 interpretive corrections in `CORRECTIONS.md`) |

---

## G. Remaining work (prioritised)

1. **Real-LLM evaluation** on injection benchmarks, extended to multi-agent handoffs. This is the largest gap in external validity.
2. **Decision precedence.** Never relax BLOCKED; log ML and policy decisions separately; give each override a reason.
3. **Live handoffs in the scored trajectory**, then re-run the flow-feature comparison under a pre-set protocol.
4. **Enforced provenance**, with a measured false-positive cost and the declaration-condition experiment.
5. **Approval binding** (PC1/PC2), separate approval keys, and a reviewer study.
6. **Persist the monitor and provenance across resume** (closes the gap in D4).
7. **The persistence confirmatory study**, after v1.2 approval and PC1/PC2. This should stay a separate paper.
8. **Recipient idempotency and reconciliation** for ambiguous deliveries.
9. **A tamper-evident audit log; a meaningful RESTRICTED level.**
10. **Independent replication.**

**Persistence placement.** The persistence work should remain a **separate study**:

- it has its own pre-registration;
- its confirmatory phase has not run;
- its preconditions are unmet.

The final paper keeps only a short scope note, plus the one observation that bears on its claims (at most one attempt, ambiguous delivery).

---

## H. Final research claims

**The paper can legitimately claim:**

1. An integrated prototype combines trajectory-aware ML scoring, deterministic rules, audit logging, shadow-mode provenance and an opt-in approval gate around real MCP tool calls in a LangGraph multi-agent pipeline.
2. On synthetic trajectories, the originally reported F1 of 0.999 was inflated by trajectory-level leakage. After correction, held-out F1 was 0.657 (Stage 1).
3. The corrected model exploited attack position. Position-invariant features remove this by construction.
4. The deployed model reaches F1 0.912 (test), 0.665 (held-out types) and 0.493 (tool-swapped variants). It catches every run of two held-out direct attack types and 6/107 runs of the held-out path attack. These are reproducible from the saved model.
5. Flow features improved path-attack detection but weakened direct-attack detection, and did not pass a pre-set decision rule.
6. In controlled demonstrations, provenance-derived sensitivity exposes under-reported sensitivity without changing agent behaviour.
7. In 8 scripted scenarios, the approval workflow paused external sends. Outcomes depended on the simulated reviewer: 0/4 against 3/4 attack sends.
8. The ledger permits at most one execution attempt per action ID.
9. Implementation gaps exist and are documented: unscored handoffs, policy downgrade of BLOCKED, shadow-only provenance, incomplete binding.

**The paper must avoid claiming:**

- complete security, prevention of prompt injection, or universal attack prevention;
- exactly-once delivery, or confirmed delivery after a crash;
- production readiness, or a working approval interface for live use;
- that provenance is enforced, or a misreport-detection accuracy;
- that recorded handoffs are scored by the ML model, or that the 6/107 miss is *caused* by the live handoff exclusion;
- that the rich flow-feature model replaced the baseline;
- any confirmatory persistence result, or that the confirmatory study ran;
- novelty for combining established mechanisms;
- results on real LLMs, real attacks or real reviewers;
- that the 0.999 F1 reflects the deployed model's performance.

---

## Newly discovered inconsistencies (this validation)

1. **Resumed approval runs lack the transmission handoff event** (0/3 in the logs), and delivery is logged under a different run ID. Now stated in the final paper (§4.7).
2. **In the stored misreporting demos, the escalated sends were approved and transmitted.** The revised paper had not stated this outcome; the final paper now does (§7.2, §8).
3. **The README is out of date relative to the code.** It describes three dashboard pages (there are four, including Human Approval) and "nine attack patterns" in the Attack Lab (there are seven attacks plus one benign scenario). It was not edited, because only manuscript files were in scope.
4. **The revised paper merged two evidence sources** ("shadow score about 0.995") and referenced some figures and tables only in their captions. Both are corrected in the final paper.
