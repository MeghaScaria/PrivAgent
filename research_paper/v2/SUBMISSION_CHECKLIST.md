# IEEE Access submission checklist: PrivAgent v2 (17 Nov 2026)

**Sources:**

- the IEEE Access *Submission Checklist* PDF (ieeeaccess.ieee.org, read 17 Nov 2026);
- the IEEE Access submission-guidelines page (ieeeaccess.ieee.org/authors/submission-guidelines, read the same day).

**Status values:** **done**; **todo** (a task that can be done without the authors' input); **needs-author** (a
decision or input only the authors can give).

| # | Requirement (source) | Status | Notes |
|---|---|---|---|
| 1 | Use the required IEEE Access template, double column, single spaced (checklist 1–2) | **needs-author** | The LaTeX template download returned HTTP 403 (`ACCESS_latex_template_20260513-1-1.zip`). Please upload it. The Markdown already maps onto the standard IEEE journal layout (`<!-- TEMPLATE -->` markers); conversion to LaTeX is **todo** once the template is here |
| 2 | Word or LaTeX source **and** a PDF, with identical content; each ≤ 40 MB (checklist 1–2) | **todo** | after conversion |
| 3 | Authorship meets IEEE's definition; non-author contributors go in the Acknowledgment (checklist 3) | **needs-author** | author list and Acknowledgment are placeholders |
| 4 | Submitting author has a public, populated ORCID iD (checklist 4) | **needs-author** | |
| 5 | All authors listed in both the source and the PDF (checklist 5) | **needs-author** | |
| 6 | Short biographies for **all** authors, below the references (checklist 6) | **needs-author** | placeholder after the references |
| 7 | Thorough grammar review (checklist 7) | **needs-author** | drafts are marked `<!-- DRAFT: author to review -->`; IEEE suggests Paperpal Preflight |
| 8 | Every reference relevant, accurate and not retracted (checklist 8) | **todo**, partly done | 34 references in IEEE style. Checked this pass against primary sources (Supplementary S12): FIDES, Permissive IFC, CapAgent, Arp, TESSERACT, AgentLeak, GuardAgent, ShieldAgent, Kairos, Noumi, McNemar, DeLong. Still open: CaMeL venue `[VERIFY]` and DeLong end page `[VERIFY]`. The 20 references carried from v1 were not re-checked for retraction |
| 9 | Not under review elsewhere (checklist 9) | **needs-author** | |
| 10 | Supplementary material ready (checklist 10) | **done** (draft) | `SUPPLEMENTARY.md` (S1–S12); format for upload **todo** with the template |
| 11 | Define every abbreviation at first use, even if defined in the abstract (checklist 11) | **todo** | LLM and MCP are defined. Check: AUROC, AUPRC, ASR (defined in V-C), PEP (II-B), IFC (only in TABLE I), HKDF, SHA-256, CI, SE, LOTO (Supplementary only) |
| 12 | 3–10 keywords (checklist 12; guidelines page) | **done** (draft) | 8 keywords, alphabetical; author to confirm |
| 13 | Manuscript type (checklist 13) | **needs-author** | "Research Article" is the default. "Negative Result" does not fit: most hypotheses are supported |
| 14 | Opposed reviewers, if any (checklist 14) | **needs-author** | |
| 15 | Video, if any (checklist 15) | n/a | none |
| 16 | List of updates if resubmitting after rejection (checklist 16) | n/a | first submission |
| 17 | Under 20 pages recommended; longer needs EIC permission (checklist 17) | **done** (estimate) | Estimated at about 13 pages: about 4,900 words of running text, 9 tables, 8 figures, 34 references. To be confirmed in the template |
| 18 | No "Lena" image (checklist 18) | **done** | none |
| 19 | AI-generated text disclosed in the Acknowledgment; sections with AI-generated text must cite the AI system (guidelines page) | **needs-author** | The draft "Declaration of AI Use" names Claude (Anthropic) and its uses. Still needed: check it against IEEE's current policy, move it into or alongside the Acknowledgment as the template requires, list the model versions, and decide how to cite the AI system in sections with AI-drafted text |
| 20 | Title (author decision) | **needs-author** | draft title marked for review |
| 21 | Abstract, one paragraph, 150–250 words (authors' target) | **done** (draft) | 234 words; author to review |
| 22 | Introduction ending in 5 numbered contributions | **done** (draft) | author to review |
| 23 | Discussion, Limitations, Conclusion | **done** (draft) | author to review; limitations stated plainly (3B local model, scripted family B writer, deterministic WP4, simulated reviewers, family A not run, synthetic data) |
| 24 | Every number traceable to evidence (project rule) | **done** | ledger-row comment on every number, script-checked; mapping in Supplementary S11 |
| 25 | Fig. 1 architecture for v2 | **needs-author** | placeholder: the v1 figure shows shadow-mode provenance and handoffs. Redraw for v2 (or ask for a generated draft) |
| 26 | Figures legible in two-column width; source files | **todo** | v2 figures are PNG plus SVG (`figures/`); v1 figures `r03` and `r05` are PNG only. Check resolution and width in the template |
| 27 | Data and Code Availability statement | **needs-author** | repository URL or archive DOI; there is no public remote yet |
| 28 | v1 statements consistent with v2 | **done** | `RESTRUCTURE_LOG.md` §4 |
| 29 | Acknowledgment (funding, contributors) | **needs-author** | placeholder |
| 30 | Phase 1 duplicate-publication check: has the v1 paper been posted or submitted anywhere? | **needs-author** | it affects checklist 9 and how Phase 1 is presented |
