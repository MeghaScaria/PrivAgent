# Draft report: v2 Methods and Results prose, 17 Nov 2026

No new LLM runs. No changes to frozen files or to the confirmatory results, apart from the requested append-only
erratum in `CONFIRMATORY_REPORT.md`. Each step was committed separately. There is no remote, and nothing was pushed.

| Step | Commit |
|---|---|
| Erratum in `CONFIRMATORY_REPORT.md` (M1–M4) and ledger rows C4b, C13b, C18c, C24 | `3a413b1`, `09bc445` |
| Methods prose and ledger rows S1–S12, P5 | `19fe8b3` |
| Results prose | `1f783b1` |
| References checked against primary sources | `f047434` |

## What was written (`research_paper/v2/PrivAgent_v2_DRAFT.md`)

Every number in these sections carries an HTML comment naming its ledger row
(`research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md`). A script checked each section: every number in the prose appears in
the text of the ledger rows that section cites. The only exceptions are "95", the confidence level defined in S9, and
section numbers.

| Section | Content | Ledger rows |
|---|---|---|
| 4.13 | WP1 precedence modes | S4 |
| 4.14 | WP2 scored handoffs, `r1_counts_handoffs`, `handoff_enforce`, R3 | S5 |
| 4.15 | WP3 hash chain, HKDF keys, RESTRICTED semantics, send binding | S6, D6 |
| 4.16 | WP4 enforced provenance, five declaration conditions, split, unit of analysis | S7, S2 |
| 6.1 | Pre-registration, freeze, amendment, configurations, data, statistics, exclusions, execution | P1–P5, S7, S9, S10, S12, C21, C22 |
| 6.2 (new) | Real-LLM pilot design, canary ground truth, metrics, H4 labels, position-only classifier | S1, S2, S3, S8, S11 |
| 6.3 (new) | Independent recomputation: method | V1 |
| 7.5.1 | H1 (supported), downgrades, costs including the per-send correction | C1–C6, C4b |
| 7.5.2 | H2 (supported), cost, R3 | C7, C8, C9, S7 |
| 7.5.3 | H3 (supported), costs | C10, C11, S7 |
| 7.5.4 | H4(a) supported, **H4(b) not supported**, the undefined label and the 0.599 sensitivity analysis | C12, C13, C13b, C14 |
| 7.5.5 | H5 (supported), per-configuration table, `rules_only` claim, what stopped the sends (corrected), utility, latency | C15–C18, C18b, C18c, C21, C24, C12, S8 |
| 7.5.6 | Multi-seed table and the path-dependent types | C19, C20, S10 |
| 7.5.7 | Independent recomputation: results and the four erratum points | V1, C4, C4b, C13, C13b, C18b, C18c, C24 |
| 7.6 | EXPLORATORY: v2 outcome split, reviewer sweep, H4(b) without the send step | X1–X4 |

**Figures used:** V2-1 `v2_f1_h5_asr.png`, V2-2 `v2_f2_benign_utility.png`, V2-3 `v2_f3_h1_live_costs.png`, V2-4
`v2_f4_h4a_recall.png`, V2-5 `v2_f5_multiseed_heldout.png` (all in `research_paper/v2/figures/`). The caption of V2-3
states that its denominators are benign runs.

**Not written, as instructed or out of scope:**

- left for you and your advisor: the abstract, introduction, contributions, discussion and conclusion;
- still empty headings: §2.7 (related work), §7.7 (development results; rows D1–D5, D7–D11 are not yet used) and §9.x
  (v2 limitations).

The v1 text is unchanged. Ledger row C23 (the wrong observation) is deliberately not used.

**Build script.** `research_paper/v2/build/make_skeleton_v2.py` built the skeleton. The prose was added afterwards, so
re-running the script would overwrite it. Don't re-run it on this file.

## Citations (`[VERIFY]` status)

Each entry records the URL checked, on 17 Nov 2026. Nothing was filled from memory.

| Ref | Work | Status | Source checked |
|---|---|---|---|
| [9] | CaMeL | arXiv record verified; **`[VERIFY: venue]`**. The first author's page says SaTML 2026, which was not confirmed on a conference page. | arxiv.org/abs/2503.18813 |
| [10] | FIDES | Verified: preprint, no venue listed | arxiv.org/abs/2505.23643 |
| [18] | CapAgent | Verified from the Crossref record; the publisher page returned 403 | api.crossref.org/works/10.3390/bdcc10090293 |
| [21] | Permissive IFC | arXiv record verified; **`[VERIFY: venue]`**. Microsoft Research lists TMLR, Oct. 2025, but OpenReview was unreadable (browser check). | arxiv.org/abs/2410.03055; microsoft.com publication page |
| [29] | Arp et al. | Verified: USENIX Security 2022, pp. 3971–3988 | usenix.org/conference/usenixsecurity22/presentation/arp |
| [30] | TESSERACT | Verified: USENIX Security 2019, pp. 729–746 | usenix.org/conference/usenixsecurity19/presentation/pendlebury |
| [31] | AgentLeak | Verified: IEEE Access vol. 14, pp. 94960–94978, 2026 | api.crossref.org/works/10.1109/ACCESS.2026.3704541; arxiv.org/abs/2602.11510 |
| [32] | GuardAgent | Verified: ICML 2025, PMLR 267, pp. 68316–68342 | proceedings.mlr.press/v267/xiang25a.html |
| [33] | ShieldAgent | Verified: ICML 2025, PMLR 267, pp. 8313–8344 | proceedings.mlr.press/v267/chen25ae.html |
| [34] | Kairos | Details verified; **`[VERIFY: identity]`**. arXiv:2610.18457 is the only agent-security "Kairos" found; confirm it is the one intended. | arxiv.org/abs/2610.18457 |
| [35] | Inspectra | **`[VERIFY]`, not identified.** The only match is a case-study platform inside arXiv:2608.21423, not a standalone publication. | arxiv.org/abs/2608.21423 |
| [27], [28] | GCM, Newcombe (from v1) | **`[VERIFY: not cited in the text]`**; unchanged | none |

**Still unverified:** [9] venue, [21] venue, [34] identity, [35], plus the two uncited v1 references. The new
references [29]–[35] are not yet cited in the text, because §2.7 is unwritten.
