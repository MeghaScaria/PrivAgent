# Final evidence map: PrivAgent Research Paper (final working version)

**Relationship to earlier maps.** This map extends `research_paper/revised/REVISED_EVIDENCE_MAP.md`, and through it `research_paper/PAPER_EVIDENCE_MAP.md`, with the validation evidence gathered on 11 November 2026. Both earlier maps are preserved unchanged. Claims not listed here keep the evidence given there.

**Tags:**

| Tag | Meaning |
|---|---|
| CODE | source code |
| RESULT | stored experiment output |
| EVID | `research_paper/evidence/` |
| LOG | persisted application logs |
| DEVLOG | development session log only |
| RECOMP-11NOV | recomputed during final validation without retraining: deterministic data regenerated in memory, saved model and thresholds loaded |
| TEST-11NOV | existing test suites or Attack Lab replay re-run in an isolated copy of the repository on 11 November 2026 |
| LIT | publication |

## Claims re-verified during final validation

| Claim | Evidence | Type |
|---|---|---|
| One trajectory ID per run; no run crosses train/validation/test; held-out sets share no IDs with the main data | 3,000 IDs, each with one attack type and `run_length` equal to its row count; overlaps 0/0/0 | RECOMP-11NOV |
| Saved model matches the feature configuration | `model.feature_names_in_` equals `feature_config.json["trajectory_level"]` equals `FEATURE_SETS["trajectory_invariant"]` (11 features); no positional, look-ahead, context or averaged feature | RECOMP-11NOV |
| Thresholds come from validation only | `tune_thresholds(validation labels, saved-model validation scores)` reproduces `models/thresholds.json` exactly | RECOMP-11NOV |
| Deployed test, held-out-types and variant metrics, including per-attack-type rows | recomputed values equal `models/training_metrics.json` (tolerance 1e-9) | RECOMP-11NOV |
| Stage 0 (0.999) and Stage 1 (0.657) metrics | preserved metric files; **not recomputable**, because the historical generator versions were not preserved | EVID |
| Downgrade case `demo_9e6a8ae2` | `logs/audit_log.jsonl`: score 0.9952 (derives to ML BLOCKED at the 0.85 threshold), final HUMAN_APPROVAL, source `policy_engine`; `logs/approval_log.jsonl`: gate HUMAN_APPROVAL by `policy_engine`, response `rejected`, execution `refused` (`not_approved:reviewer_rejected`). Transmission did not occur | LOG |
| Misreporting demos `demo_cc0f5f9e`, `demo_89c31726` | audit log: declared 0, provenance 1, authoritative 1, enforced 0.0 → AUTONOMOUS, shadow 0.9952 → HUMAN_APPROVAL, `would_change_outcome = true`; approval log: gate HUMAN_APPROVAL by `flow_rule`, response `approved`, execution `executed`. Transmission occurred | LOG |
| Development-log misreporting example (≈0.0000005 / ≈0.9995) | development log only; the test asserts shadow > enforced | DEVLOG, CODE |
| Resumed runs lack the transmission handoff event | `logs/handoff_log.jsonl`: the unpaused run `demo_e4f2276e` has six events, including `transmission`; the paused-and-resumed runs `demo_cc0f5f9e`, `demo_89c31726` and `demo_9e6a8ae2` have no `transmission` event, and their deliveries are logged under other run IDs | LOG, CODE (`agents/handoffs.py:after_writer` iterates the current monitor's decisions) |
| Handoffs are never in the scored trajectory; no handoff event in the audit log | `trajectory_monitor.py`; `audit_log.jsonl` contains no handoff-type tool events | CODE, LOG |
| Test-suite and Attack Lab outcomes | see `FINAL_RESEARCH_VALIDATION_REPORT.md` §F | TEST-11NOV |
| Wang et al. 2026 | full text read (see the revised map) | LIT |

## Manuscript structure checks (final)

- Figures 1–10 and Tables 1–11 are numbered in order, and each is referenced in the body text.
- Every "Section X" reference resolves to a heading.
- Every citation [1]–[28] is listed, and every listed reference is cited.
- Figure 11 (persistence ablation) was removed, because persistence is now a scope note.
