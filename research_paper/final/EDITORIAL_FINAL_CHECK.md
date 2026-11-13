# Editorial final check: PrivAgent Research Paper

| | |
|---|---|
| Manuscript | `research_paper/final/PrivAgent_Research_Paper_Final.md` (948 lines, sha256 `6a514648…fc1a3607`) |
| PDF | `research_paper/final/PrivAgent_Research_Paper_Final.pdf` (20 pages, two-column layout, sha256 `ee2d9002…af4157c9a029`) |
| Pre-editorial copy | `research_paper/final/archive/PrivAgent_Research_Paper_Final_pre_editorial_2026-11-11.md` (sha256 `283a7f03…bb5`) and `.pdf` (18 pages) |
| Date | 11 November 2026 |
| Companion documents | `CLAIM_EVIDENCE_LEDGER.md`, `TERMINOLOGY_GLOSSARY.md` |

**Scope.** This was an editorial and validation pass only:

- no experimental result, model, threshold, dataset, generator, attack scenario, policy rule, feature, source file, log, snapshot or pre-registration was changed;
- no experiment was run;
- no citation was added.

## 1. Issues assessed and actions taken

| # | Issue | Verdict after checking the evidence | Action | Section(s) |
|---|---|---|---|---|
| 1 | Positioning led with "a runtime-governance prototype" rather than the empirical investigation | valid | Subtitle, abstract, §1.2 and §11 now present the empirical investigation as the primary contribution and PrivAgent as the experimental platform. §1.2 adds the implemented / demonstrated / unvalidated distinction. Main title unchanged (author's decision) | front matter; Abstract; §1.2; §11 |
| 2 | Abstract implied a progression 0.999 → 0.657 → 0.665 | valid: Stage 1 (legacy generator) and Stage 2 (randomized generator, invariant features) use different sets (Table 5 already says so) | Abstract states the values are from different stages and are not one model's progression. It also states that removing the shortcut did not fix generalisation, and adds 0.493, 6/107 and step recall 0.019 with step/run-level wording. Table 1 RQ1 cell relabelled | Abstract; Table 1 |
| 3 | Abstract omitted the unmodified-pipeline 2/4 baseline | valid (E5 totals: 2 / 0 / 3 of 4) | Added, with the sample size (eight scripted scenarios) | Abstract |
| 4 | Misreporting demo outcome missing from the abstract | valid (approval log: both approved and executed) | Added "the flag informed human review but did not prevent transmission" | Abstract |
| 5 | Policy precedence: the invariant was recommended without trade-offs; no explicit finding | valid | Added the key finding, a trade-off discussion (false positives, review burden, security-critical actions, privilege escalation, conflicting signals) and a separate-logging recommendation. The invariant is scoped to sensitive external transmissions and remains a proposal with unmeasured cost. "Most restrictive always wins" is not prescribed universally | §4.10; §11 |
| 6 | Provenance roles conflated | partly valid: the text was accurate but scattered | New table: identify / detect mismatch / record / prevent, with status and code locations | §4.8 |
| 7 | Realism wording imprecise ("every experiment uses synthetic data and scripted components") | valid: E1–E3 are offline; Attack Lab, E4, E5 and the approval tests use the real MCP stdio servers; persistence used `SyntheticMCP` | Replaced with an infrastructure breakdown that uses the term "real MCP tool servers exercised under scripted workloads". Table 3 itself unchanged, to keep it readable in two columns | §6; Abstract |
| 8 | Wang et al. comparison overstated the overlap ("substantially the same problem") | valid | Now states the different research questions and the non-comparability of the numbers, adds that PrivAgent lacks tamper-evident logging, and states explicitly that no outperformance is claimed | §2.3 |
| 9 | Human approval lacked a "control point" interpretation | valid | Added: "Human approval is a control point, not an independent security guarantee." | §7.3 |
| 10 | §8 RQ1 opened with "Trajectory context does change risk assessment", which was unsupported as stated | valid: the in-paper evidence is weak | Replaced with the measured evidence: prefix importances 0.049 / 0.025 (verified in `position_ablation.json`) and Attack Lab path attacks caught by ML only. Also removed "every run of the seen attack types" (not reported in Table 6) | §8 |
| 11 | Spelling inconsistency ("Generalization" in the subtitle) | valid | Subtitle now uses British spelling. "Randomized" is kept as the generator's name (see glossary) | front matter |
| 12 | Stale date line ("Revised working research draft, 10 November 2026") | valid | Now "Working research draft (editorially audited), 11 November 2026". The 10 Nov 2026 literature-check dates are kept, because they are factual | front matter |
| 13 | Abstract's "detects every run" mixed step and run level | valid | Now "At run level (at least one unsafe step stopped), the deployed model catches every run…". The glossary defines detects / catches | Abstract; glossary |
| 14 | Appendix A did not point to the new ledger and glossary | – | Rows added | Appendix A |

**Suggestions not adopted, or adopted only partly, after verification:**

- **Table 3 realism column.** Not added. A sixth column would make Table 3 too dense for the two-column layout; the §6 bullet list carries the same information.
- **"Most restrictive always wins".** Not prescribed universally, as the audit asked.
- **Main title.** Unchanged; retitling is left to the author.

## 2. Sections modified

- front matter (subtitle and date);
- Abstract;
- §1.2;
- Table 1 (RQ1 "Demonstrated" cell);
- §2.3;
- §4.8 (new provenance-capability table);
- §4.10 (finding, trade-offs, scoped proposal);
- §6 (opening paragraph);
- §7.3 (closing sentence);
- §8 (RQ1 paragraph);
- §11 (first two paragraphs);
- Appendix A.

**Unchanged:**

- §3, §4.1–4.7, §4.9, §4.11–4.12, §5, §7.1, §7.2, §7.4, §9 and §10;
- all tables apart from Table 1;
- all figures;
- all references.

## 3. Numerical claims verified

All 42 ledger rows were checked; see `CLAIM_EVIDENCE_LEDGER.md`.

- **Recomputed on 11 Nov 2026 and matching `models/training_metrics.json`:** the deployed metrics (0.912 / 0.665 / 0.493; P, R, AUROC), 6/107 with step recall 0.0187, the per-type runs caught, benign false alarms, Table 4 sizes and the thresholds.
- **Stage 0 and Stage 1:** match the preserved evidence files, but cannot be recomputed.
- **Newly cited in this pass:**
  - 0.049 and 0.025 from `position_ablation.json`;
  - 3.7–5.3% benign-run false alarms from Table 6;
  - the 2/4 unmodified-pipeline count from `approval_evaluation.json`;
  - demo outcomes (approved, executed) from `logs/approval_log.jsonl`.

No number in the manuscript was changed.

## 4. Unresolved claims (recorded, not guessed)

| Item | Status |
|---|---|
| Whether E5's two R2-escalated scenarios had an ML BLOCKED | unverifiable; E5 stores no score; stated in §4.10 and §9 |
| Stage 0 / Stage 1 metrics | preserved files only; historical generator not preserved |
| ≈0.0000005 / ≈0.9995 (test misreport) and ≈0.04 / ≈1.0 (positional example) | development log only; labelled in the text |
| ~1% of benign steps match the path rule | development observation; labelled in §9 |
| Permissive IFA [9] venue | OpenReview not checked; stated in the reference |
| **Figure 2 text vs §4.10** (RESOLVED 12 Nov 2026; see Section 8) | The figure's annotation box lists the proposed rule as "conflicts resolve to the more restrictive outcome"; §4.10 now adds "unless an explicit and logged exception applies" and scopes the invariant to sensitive external transmissions. The figure was not edited, because figure files are outside the permitted scope. The text governs. Recommended: regenerate Figure 2 in a later, authorised pass |

## 5. Markdown / PDF synchronisation

- The PDF was regenerated with `research_paper/final/build/build_pdf_final.py` after the last Markdown edit. Timestamps: MD 21:40:31, intermediate HTML 21:40:32, PDF 21:40:33.
- All new passages were confirmed in the build HTML that the PDF is printed from, and the old date string is absent.
- All 20 pages were rendered to images. Pages 1, 7 and 8 were inspected:
  - **Page 1:** title, banner, author/date line and full abstract all fit, followed by the two-column body.
  - **Pages 7–8:** the new provenance table and the §4.10 trade-off text render correctly in the two-column layout.
- **Page count:** 18 → 20, because of the added text.
- **Layout fix during the pass:** the first build pushed the unbreakable abstract block onto page 2, leaving page 1 blank. The abstract wording was tightened, with no content removed, and the PDF rebuilt. Page 1 is correct now.

**Result: synchronised.**

## 6. Changes outside the permitted files

Files created or modified in this pass:

| File | Change |
|---|---|
| `research_paper/final/PrivAgent_Research_Paper_Final.md` | edited |
| `research_paper/final/PrivAgent_Research_Paper_Final.pdf` | rebuilt |
| `research_paper/final/build/PrivAgent_Research_Paper_Final.html` | intermediate HTML, regenerated by the existing build script (not hand-edited) |
| `research_paper/final/archive/PrivAgent_Research_Paper_Final_pre_editorial_2026-11-11.md` / `.pdf` | recoverable copies, new |
| `research_paper/final/CLAIM_EVIDENCE_LEDGER.md`, `TERMINOLOGY_GLOSSARY.md`, `EDITORIAL_FINAL_CHECK.md` | new |

**Integrity checks after the pass:**

| Check | Result |
|---|---|
| 58 protected tracked files (code, models, data, results, logs, pre-registration) against the pre-pass hash list | 58/58 OK |
| `snapshots/exploratory_persistence_v1_20261109/MANIFEST.sha256` | 84/84 OK |
| `snapshots/pre_persistence_eval_20261109/MANIFEST.sha256`, verified on an extracted copy in scratch | 86/86 OK |
| `models/*` against `models/baselines/trajectory_invariant_v1/` | identical (5 files) |
| Files newer than the backup, outside `research_paper/final/` | none |

No commits were made.

## 7. Freeze recommendation

**Recommend freezing** this manuscript as the final working research draft. Conditions:

1. the author accepts or reverts the subtitle and abstract repositioning;
2. the Figure 2 annotation mismatch (Section 4 above) is accepted as a known minor inconsistency or fixed in a separately authorised figure pass;
3. author names, affiliations and a final title decision are added before any submission.

No numerical, factual or citation issue blocks the freeze.

## 8. Addendum: final author-requested corrections (12 November 2026)

**Recoverable copies made before this round:**

- `archive/PrivAgent_Research_Paper_Final_pre_final_corrections_2026-11-12.md` and `.pdf`;
- `archive/r04_decision_precedence_pre_2026-11-12.png`.

| # | Request | Change | Location |
|---|---|---|---|
| 1 | Abstract precision | The sentence now says the five F1 values come from different experimental stages *and* evaluation sets. The bullets label each one: Stage 0 test 0.999; Stage 1 held-out types 0.657; Stage 2 (deployed) 0.912 test, 0.665 held-out types, 0.493 variants. Numbers unchanged | Abstract |
| 2 | Figure 2 | Redrawn by a new script, `build/make_figure2_final.py`; the revised-paper script is unchanged. Panel A (current implementation) shows that a firing rule replaces the ML decision, even if it is less restrictive, and the observed R2 downgrade of ML BLOCKED to HUMAN_APPROVAL when R1 does not fire. Panel B is visually separated, dashed and labelled "PROPOSED … NOT IMPLEMENTED". It carries the scoped invariant with its logged-exception clause and unmeasured cost. Caption rewritten to match | `figures/r04_decision_precedence.png`; §4.10 caption |
| 3 | MCP terminology | Standardised to "four locally run FastMCP stdio server processes, exercised using synthetic data and scripted workloads". §6 states that the servers genuinely execute, but no workload is LLM-driven or drawn from production use. The only remaining "real MCP" refers to Wang et al.'s server | Abstract; Contribution 3; Table 2 (comparison table in §2.3); §4.2; §6; Table 3; §7.1.3; §9 E3; §11 |
| 4 | Consistency | Limitation C4 now states the exact mechanism (firing rule replaces ML; R2 vs R1) and that the invariant is not implemented, matching the abstract, Figure 2, §4.10, Table 11, §8 RQ3, §10 and §11 | §9 C4 |
| 5 | Date line | 11 → 12 November 2026 | front matter |

**Consistency check.** The abstract, Figure 2, §4.10, §9 C4, Table 11 and §11 agree on three points:

1. **Current behaviour:** a firing rule replaces the ML decision, so R2 can turn ML BLOCKED into HUMAN_APPROVAL when R1 does not fire.
2. **Proposed invariant:** future work, not implemented, scoped to sensitive external transmissions, with a logged-exception clause.
3. **"Most restrictive":** never presented as implemented, and never as universally correct.

No contradictions were found.

**Rebuild and synchronisation:**

- The PDF was rebuilt after the last Markdown edit. Timestamps: figure 02:20:54, MD 02:22:33, HTML 02:22:34, PDF 02:22:35.
- All new passages were confirmed in the build HTML.
- 20 pages, rendered and inspected:
  - **Page 1:** title, author/date line and full abstract fit. An intermediate build had pushed the abstract to page 2; the redundant restatement of the F1 values was folded into the bullets.
  - **Page 8:** the new Figure 2 and its caption render legibly in the two-column layout.

**Final hashes:**

| File | sha256 |
|---|---|
| MD | `acba53d2…bff5892` |
| PDF | `949a242a…a559527` |
| Figure 2 | `014ecdcb…6541be9cc1c2692b821a088d794f1b` |

**Integrity:**

| Check | Result |
|---|---|
| Protected files | 58/58 OK |
| Exploratory snapshot manifest | 84/84 OK |
| Pre-persistence snapshot manifest | 86/86 OK |
| Models | identical to `models/baselines/trajectory_invariant_v1/` |
| Files changed outside `research_paper/final/` | none |
| Commits | none |

**Recommendation: freeze the manuscript.**
