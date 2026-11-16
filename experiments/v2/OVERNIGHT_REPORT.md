# Overnight report: 16–17 Nov 2026

**Scope.** No new LLM runs. No changes to frozen files or to the confirmatory results: `git diff 2ed41c7 HEAD` touches
no file under `models/`, `snapshots/`, `experiments/results/`, `experiments/secure_persistence/`,
`research_paper/final/`, `research_paper/evidence/`, `logs/`, `runtime/`, `experiments/v2/results/`,
`experiments/v2/analysis/` or `CONFIRMATORY_REPORT.md`. Each item has its own commit; there is no remote and
nothing was pushed.

| # | Item | Commit | Outcome |
|---|---|---|---|
| 1 | Amendment 1: stale DRAFT header | `9846df9` | Appended at the bottom; the frozen text is byte-identical (prefix hash still `846374a7…`); amended-file hash recorded in `PREREGISTRATION_HASHES.md` |
| 2 | Independent recomputation | `b39b664` | `INDEPENDENT_CHECK.md`. A subagent that did not read the analysis code or its outputs recomputed 53 items: **44 match, 2 within tolerance, 7 mismatch** (3 causes), plus 1 wrong observation |
| 3 | Exploratory analyses | `6b750b6` | `exploratory/EXPLORATORY_v2_familyB_and_H4b.{md,json}` and `exploratory_v2.py` |
| 4 | Claim–evidence ledger | `0469c65` | `research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md`: 44 rows (P, C, X, D, V) with artifact, commit and v1 status codes |
| 5 | Figures | `68e76d7` | 5 figures (PNG + SVG) and `research_paper/v2/figures/make_figures_v2.py` |
| 6 | Paper skeleton | `588e663` | `research_paper/v2/PrivAgent_v2_DRAFT.md`, built by `research_paper/v2/build/make_skeleton_v2.py` |

## Needs your attention

1. **H4(b) depends on an undefined label (M2).** The pre-registration does not say how to label attack-run steps that
   carry no canary.
   - **The registered code** (`h4.py`, `843d157`) counts them as safe: AUROC 0.654, NOT SUPPORTED. That is the
     confirmatory outcome as computed, and it stands.
   - **Leaving them unlabelled** gives 142 safe steps and AUROC 0.599 [0.530, 0.668], which would pass the
     point rule.
   - The independent check reproduced 0.654 exactly under the code's reading.
   - The paper must report both.
2. **A wrong statement in `CONFIRMATORY_REPORT.md` (M4).** It says the frozen model's own decisions did not stop
   the v2 sends. In fact the model's decision on all 52 canary-carrying v2 sends was BLOCKED. Of those, 44 were
   relaxed to HUMAN_APPROVAL by `max_severity_reviewable` and 8 kept BLOCKED. What the model missed was the
   handoffs (1/62), not the sends. I did not edit the report. Whether to add a dated erratum is your call; the ledger
   marks the statement WRONG (C23).
3. **The H1 live cost denominator (M1).** `h1.py` divides by benign runs (14), but the pre-registration defines the
   cost over benign sends, and only 12 runs request one. Per send the difference is 0.667, not 0.571. No decision
   depends on it.
4. **The latency scope (M3).** The reported 72–106 s pools family B and benign runs; benign alone gives 81.4–94.0 s.

## Exploratory results (not pre-registered)

- **v2 family B outcomes:** of the 55 runs that reached the writer, 8 were hard-blocked, 44 sent to review, 3 allowed
  and 0 leaked. The 3 allowed runs are all one task, whose send carried no canary, so the split is three-way, not
  two.
- **Reviewer sweep:** expected attack success is 0.080, 0.240, 0.400 and 0.744 at P(approve | attack) = 0.1, 0.3,
  0.5 and 0.93 (task-bootstrap CIs in the file). The configuration that actually ran with p = 0.5, `v2_reviewer`,
  observed 17/53 = 0.321, against 0.387 expected from its own counts.
- **H4(b) without the writer's final send:** AUROC 0.567 [0.508, 0.625], down from 0.654. Much of the 0.654 comes
  from the send step always coming last.

## Paper skeleton: what was changed

- **v1 text:** unchanged apart from citation numbers and `[VERIFY]` marks. A script check found no v1 line removed or
  reworded.
- **References:** renumbered by first citation. [24] (GCM) and [26] (Newcombe) are cited nowhere; they are kept at
  the end and flagged, not deleted.
- **`[VERIFY]` marks:** on CaMeL, FIDES, Permissive IFC and CapAgent, both in the text and in the reference list.
  Arp et al., TESSERACT, AgentLeak, GuardAgent, ShieldAgent, Kairos and Inspectra were not in v1's references; each
  is a `[VERIFY]` placeholder with no bibliographic details.
- **Appendix A:** the original paper's per-experiment script → output rows were dropped from the final version.
  They are restored, the final figure script is added, and every path was checked to exist. A new Appendix B lists
  the v2 artifacts.
- **v2 headings:** 16 empty headings (§2.7, §4.13–4.16, §6.1, §7.5.1–7.5.7, §7.6, §7.7, §9.x), each listing its
  ledger rows. No new prose.

## Not done or not verified

- **WP3 code:** for the hash-chained logs, HKDF and send binding (D6), I relied on the 15 Nov gate; the code was not
  re-read.
- **Figures:** each was checked by rendering and looking at it. The light theme only; there is no dark variant.
