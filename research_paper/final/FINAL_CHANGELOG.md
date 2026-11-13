# Final changelog (revised → final)

| | |
|---|---|
| Source | `research_paper/revised/PrivAgent_Research_Paper_Revised.md` (unchanged) |
| Final | `research_paper/final/PrivAgent_Research_Paper_Final.md` / `.pdf` |
| Date | 11 November 2026 |

**Scope.** Only evidence-backed corrections were made. No research finding was changed, no new experiment was run, and no model was retrained.

| # | Section | Change | Reason | Evidence |
|---|---|---|---|---|
| 1 | Abstract; Table 1 (RQ2); §8 RQ2 | Replaced the merged figure "shadow score about 0.995" with the stored value (enforced 0.0, shadow 0.9952). The development-log example is now referenced separately | The two misreporting evidence sources must not be combined into one claim | LOG; DEVLOG |
| 2 | §7.2 | The misreporting table is now numbered **Table 9**, titled "two separate sources, not one experiment". Added an explanation of why the sources stay separate (different runs and recording locations, rounding in the audit log). Added the stored outcome: in both demo runs the escalated sends were **approved and transmitted** | Reconciliation requested; outcome found in `approval_log.jsonl` during validation | LOG |
| 3 | §8 RQ2 | Added that the provenance flag informed the review but did not itself prevent transmission | Same evidence as change 2 | LOG |
| 4 | §4.7 | Added a caveat: in paused-and-resumed approval runs, the closing *transmission* handoff event is not recorded, and *delivery* is logged under the resumed process's run ID (0 of 3 resumed demo runs have a transmission event) | Newly found inconsistency between the handoff table and the logs; known in-memory-state limitation | LOG; CODE |
| 5 | §7.4 | Persistence reduced to a **scope note**: separate study, confirmatory not run, PC1/PC2 unimplemented; only the ledger and ambiguous-delivery observation retained. Figure 11 removed | Keeps the paper focused, per the author's preference. The only persistence result bearing on the paper's claims is the at-most-once / ambiguous-delivery observation | SNAP (frozen exploratory study) |
| 6 | Table 3 | Persistence row reworded to "scope note; separate study" | Consistency with change 5 | – |
| 7 | Tables 9→10, 10→11 | Renumbered after change 2 | Numbering | – |
| 8 | Throughout | Added body-text references to Figures 2, 3 and 7–10, and to Tables 1–3, 5, 6, 8, 10 and 11 (previously cited only by their captions) | Every figure and table must be referenced in the text | Structural audit |
| 9 | PDF banner | "see Sections 7.4 and 9" → "see Section 9" | Section 7.4 is now a scope note | – |
| 10 | Table 3, E6 row | Updated with the results of the 11 November 2026 re-run of the existing suites (see the validation report §F) | Reproducibility record | TEST-11NOV |

**Not changed:**

- all metrics;
- the RQ structure;
- the related work;
- the limitations content (apart from changes 4–5);
- the references (still [1]–[28], all cited);
- Figures 1–10.
