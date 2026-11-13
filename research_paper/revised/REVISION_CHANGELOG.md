# Revision changelog: PrivAgent research paper

| | |
|---|---|
| Original | `research_paper/PrivAgent_Research_Paper.md` / `.pdf` (unchanged) |
| Revised | `research_paper/revised/PrivAgent_Research_Paper_Revised.md` / `.pdf` |
| Date | 10 November 2026 |

**Scope.** This is a manuscript revision only. No production code, models, thresholds, feature configurations, datasets, result files, frozen snapshots, pre-registration or confirmatory protocol were changed. No new experiment was run.

**Basis column:**

| Value | Meaning |
|---|---|
| EVID | existing experimental evidence |
| CODE | code inspection |
| LOG | stored application logs (`logs/*.jsonl`) |
| DEVLOG | the development session log |
| LIT | literature |

## Changes

| # | Section (revised) | What changed | Why | Basis |
|---|---|---|---|---|
| 1 | Title / subtitle | Subtitle changed to "An Integrated Prototype and an Empirical Study of Evaluation Pitfalls, Shortcut Learning and Generalization Limits" | Frames the paper as an investigation, not a component list | Review request |
| 2 | Abstract | Rewritten around the empirical findings: leakage (0.999 → 0.657); the shortcut; the deployed results (0.912 / 0.665 / 0.493; 6/107); provenance and approval as controlled demonstrations; major limitations. Approval wording now states that effectiveness depends on the reviewer and that no real reviewers were studied | Emphasise findings over components; avoid overstating approval | EVID, CODE |
| 3 | §1.2 (new) | Central statement added | Requested reframing | – |
| 4 | §1.3 (new) | RQ1–RQ3 and Table 1, mapping each RQ to its experiments with "investigated / demonstrated / remains unproven" | Requested; makes the evidence strength explicit | EVID |
| 5 | §1.3 | Contributions rewritten into four items, with no novelty claim. Item 4, documented architectural gaps, is new | Avoid unsupported novelty | CODE |
| 6 | §2.3 (new) | Detailed comparison with Wang, Zhu and Li, *Electronics* 15(13):2829 (2026): interception point, cross-step labels, rules, hash-chained audit, real-LLM evaluation, mock and real MCP use, and single-agent PEP against multi-agent orchestration. The full article was read in a browser | Requested; closest published work | LIT |
| 7 | §2.2, §2.6, references | Re-checked publication status. CaMeL, FIDES and Progent are still arXiv preprints (no venue found on 10 Nov 2026), and the reference notes say so. PIFA's TMLR status still rests only on the Microsoft Research listing. Positioning table updated with Wang et al. | Remove or flag outdated status | LIT |
| 8 | §4 / Figure 1 | New three-tier architecture figure: default governed execution, shadow-mode instrumentation, opt-in approval | Requested; clarity on what is enforced | CODE |
| 9 | §4.9 (new) | "Recorded, propagated, scored" table and the handoff limitation, using the requested wording. Clarifies how this relates to 6/107: an offline generalisation failure in which cross-agent steps *are* present, so it is not caused by the live exclusion. The two limitations compound | Requested; prevents implying that recorded handoffs are scored | CODE (`trajectory_monitor.py` `record_handoff` and `evaluate`; `agents/tools.py`) |
| 10 | §4.10 (new) / Figure 2 | Decision precedence: ML, policy, final and approval outcomes. Shows that R2 can downgrade an ML BLOCKED to HUMAN_APPROVAL, and that the ML decision is not logged separately. Evidence: Attack Lab (3 scenarios) and dashboard demo `demo_9e6a8ae2` (r = 0.9952 offered for review, rejected). The proposed invariant and conflict rules are labelled as future work. The policy engine is unchanged | Requested; a real architectural limitation | CODE, EVID, LOG |
| 11 | §6 Table 3 (new) | Experiment table: RQ, evidence type, units, measures. Explicit step-level against run-level metric definitions | Requested; avoids confusing the metric levels | EVID |
| 12 | §7.1.1 (new) | "Why High Evaluation Accuracy Can Be Misleading in Trajectory-Based Security Models": A leakage (Figure 4, new split diagram); B shortcut (Figure 5, new diagram; the 0.04-against-1.0 example labelled as development-log values; stored recall-by-position corroboration); C generalisation trade-off (round-1 against deployed comparison). States that 0.999 is historical evidence of an evaluation problem | Requested | EVID, DEVLOG |
| 13 | §7.1.2 | Stage table kept, with a stronger "not directly comparable" caption | Avoid an apples-to-apples reading | EVID |
| 14 | §7.1.2 Table 6 | Run-level table, plus an explicit definition of what "6/107" measures | Requested | EVID |
| 15 | §7.2 (rewritten) | Controlled misreporting demonstration. Development-log test values (≈0.0000005 against ≈0.9995) **and** stored dashboard-demo values (0.0 against 0.9952, shadow HUMAN_APPROVAL, `would_change_outcome = true`). Explicitly not a detection-accuracy claim; lists shadow mode, retained declaration, conservative unknown, no enforcement. Proposed future experiment (accurate, incorrect, missing, contradictory declarations), marked as not conducted | Requested; the requested values exist only in the development log, so the stored evidence was added | DEVLOG, LOG, CODE |
| 16 | §7.3 | Approval results unchanged in substance; interpretation reworded to "controlled mechanism"; reviewer dependence emphasised | Requested | EVID |
| 17 | §8 (rewritten) | Discussion answers RQ1, RQ2 and RQ3 explicitly | Requested | – |
| 18 | §9 (reorganised) | Limitations in five categories (A–E), plus summary Table 10. Added: policy-precedence downgrade; ML decision not logged separately; misreported send after fewer than two sensitive reads passes (supported by E5 `*_misreported`, sent in the current configuration); audit log not tamper-evident (contrast [28]) | Requested; every statement checked against the code | CODE, EVID |
| 19 | §10 | Future work reordered; adds decision precedence, the declaration experiment, comparison with a PEP design, and a hash-chained audit log. All labelled as not implemented | Requested | – |
| 20 | §11 | Conclusion rewritten around the requested framing, adapted to the evidence. Adds "including every run of two held-out direct attack types", and states the live-scoring and precedence gaps | Requested | EVID |
| 21 | Figures | New: r01 (three tiers), r02 (row against run split), r03 (position shortcut), r04 (decision precedence). Reused unchanged: evaluation stages, position recall, LOTO, variant C, approval outcomes, persistence (exploratory), approval lifecycle | Requested | – |
| 22 | §3, §5 | Condensed; content unchanged | Length | – |

## Numerical corrections

None to reported values. The revision keeps the audited values of the original paper, including the two rounding corrections already made in the original (held-out-types AUROC 0.984, precision 0.857).

**One wording correction carried over.** Policy rules see *declared* sensitivity only for `send_result`. For reads, the tool wrappers assign it.

## Claims weakened, qualified or removed

- **Misreporting values.** The ≈0.0000005 / ≈0.9995 values are attributed to the development log, not to a stored result, and are presented next to the stored 0.0 / 0.9952 values.
- **"Policy rules override the model"** is now explicitly "replace", with the documented downgrade case.
- **The approval workflow** is described as a controlled demonstration whose effectiveness depends on the reviewer.
- **6/107** is explicitly *not* attributed to the live handoff exclusion (see the inconsistency below).
- **"The policy engine still uses declared values"** is narrowed to outbound sends.

## Technical inconsistencies found

1. **The suggested link between the handoff limitation and 6/107 is not causal.** The offline evaluation includes cross-agent steps as actions, so the 6/107 miss is a classifier generalisation failure. The live exclusion is a separate, compounding limitation. The paper states this explicitly instead of attributing the miss to the exclusion.
2. **The ML decision is not stored as its own field** in the audit or approval logs. Only the score, the final decision and its source are stored.
3. **Experiment 5 does not store ML scores.** Whether its two policy-escalated scenarios had an ML BLOCKED score cannot be verified from the results (see unresolved items).
4. **The requested misreporting values (0.0000005 / 0.9995) are not in any stored result file.** The test asserts only that the shadow score exceeds the enforced score.

## Unresolved items requiring further evidence or experiments

- **ML scores for Experiment 5's policy-escalated scenarios.** They were not stored, so whether those cases were ML BLOCKED → HUMAN_APPROVAL downgrades is unknown.
- **Misreport-detection accuracy** across declaration conditions: the proposed experiment has not been run.
- **Live ML scoring of cross-agent flow:** not implemented and not evaluated.
- **Real-LLM and real-reviewer evaluation:** not conducted.
- **Confirmatory persistence study:** pre-registered (v1.1; amendment v1.2 pending) and not run.
- **"Towards Verifiably Safe Tool Use for LLM Agents":** not added, because the paper and its bibliographic details were not verified, as instructed.
- **CapAgent:** still described from its abstract and bibliographic record only (publisher page blocked automated access).
