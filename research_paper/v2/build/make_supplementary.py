"""
Builds research_paper/v2/SUPPLEMENTARY.md.

Moved v1 blocks are copied verbatim from the frozen v1 paper (research_paper/final/PrivAgent_Research_Paper_Final.md,
read only), with three mechanical edits, each listed in research_paper/v2/RESTRUCTURE_LOG.md:
  - v1 citation numbers become author names (the v2 manuscript renumbers its references);
  - figure paths point to ../final/figures/;
  - statements that v2 contradicts are rescoped by an editor's note or removed (REMOVE / NOTE below).
The development results, the ledger mapping and the reference-verification log are written here.

    python research_paper/v2/build/make_supplementary.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(V2))
V1 = os.path.join(ROOT, "research_paper", "final", "PrivAgent_Research_Paper_Final.md")
MS = os.path.join(V2, "PrivAgent_v2_DRAFT.md")
LEDGER = os.path.join(V2, "CLAIM_EVIDENCE_LEDGER_v2.md")
DST = os.path.join(V2, "SUPPLEMENTARY.md")

V1_REFS = {1: "Anthropic (MCP)", 2: "MCP specification", 3: "LangGraph documentation", 4: "Greshake et al.",
           5: "InjecAgent", 6: "AgentDojo", 7: "CaMeL", 8: "FIDES", 9: "Permissive IFC", 10: "AGATE",
           11: "CapAgent", 12: "Li et al. (Agent-BOM)", 13: "Z. Wang (PCAA)", 14: "Progent", 15: "IsolateGPT",
           16: "Agent-Sentry", 17: "Denning", 18: "Buneman et al.", 19: "Friedman", 20: "scikit-learn",
           21: "Kapoor and Narayanan", 22: "Geirhos et al.", 23: "Parasuraman and Riley", 24: "NIST SP 800-38D",
           25: "Wilson", 26: "Newcombe", 27: "RFC 2104 (HMAC)", 28: "Wang et al."}

V1_NOTE = ("> *Editor's note (v2): this block is moved verbatim from the v1 paper and describes the **v1 system and "
           "Phase 1**. Where v2 changed the system, see TABLE II of the main text; specific rescoping notes are "
           "inline. Section, table and figure numbers inside the block refer to the v1 paper.*")

# (start heading, end heading) in the v1 paper; text in [start, end)
BLOCKS = [
    ("S1", "Persistence study (scope note; moved from v1 Section 7.4)",
     "### 7.4 Persistence and recovery (scope note)", "## 8. Discussion"),
    ("S2", "Experiment 5: per-scenario human-approval results (moved from v1 Section 7.3)",
     "### 7.3 RQ3: human approval", "### 7.4 Persistence and recovery (scope note)"),
    ("S3", "Phase 1 detailed results: RQ1 (moved from v1 Section 7.1)",
     "### 7.1 RQ1: trajectory-aware risk detection", "### 7.2 RQ2: provenance-derived sensitivity"),
    ("S4", "Phase 1 detailed results: RQ2 provenance demonstrations (moved from v1 Section 7.2)",
     "### 7.2 RQ2: provenance-derived sensitivity", "### 7.3 RQ3: human approval"),
    ("S5", "Phase 1 methodology and evaluation sets (moved from v1 Section 6)",
     "## 6. Experimental Methodology", "## 7. Results"),
    ("S6", "Phase 1 implementation summary (moved from v1 Section 5)",
     "## 5. Implementation Summary", "## 6. Experimental Methodology"),
    ("S7", "v1 handoff instrumentation and decision-precedence analysis (moved from v1 Sections 4.7 and 4.10)",
     "### 4.7 Provenance registry and handoff instrumentation (shadow mode)", "### 4.8 Provenance-authoritative sensitivity (shadow mode)"),
    ("S7b", None,
     "### 4.10 Policy override conflicts and decision precedence", "### 4.11 Human approval and execution ledger (opt-in)"),
    ("S8", "Detailed comparison with Wang et al. (moved from v1 Section 2.3)",
     "### 2.3 Runtime policy enforcement for MCP-based agents (Wang et al.)", "### 2.4 Provenance-based and compositional-attack defences"),
]

# Statements v2 contradicts, inside moved blocks: (exact v1 text, replacement). Logged in RESTRUCTURE_LOG.md.
EDITS = [
    # v1 7.2: the declaration-condition experiment was run in v2 (WP4)
    (re.compile(r"\*\*A future experiment, not conducted\.\*\*.*?It should run on synthetic and real-LLM pipelines\.\n?", re.S),
     "*[Editor's note (v2): the declaration-condition experiment proposed here in v1 was run in v2 (WP4, five "
     "conditions); see main text Sections V-C and VI-B (H3).]*\n"),
    # v1 4.10: the invariant was implemented in v2
    (re.compile(r"\*\*Proposed future work, not implemented\.\*\* For external transmissions.*?The policy engine was not changed for this revision\.\n?", re.S),
     "*[Editor's note (v2): the invariant proposed here in v1 is implemented in v2 as `max_severity` precedence, "
     "and its reviewable variant is the primary configuration; ML and policy decisions are logged separately "
     "(main text Section IV-C; H1).]*\n"),
    (re.compile(r"Whatever precedence is chosen, it should be explicit, and the ML decision, the policy decision, the override reason and the final decision should be logged as separate fields\. PrivAgent currently logs only the score, the final decision and its source\."),
     "Whatever precedence is chosen, it should be explicit, and the ML decision, the policy decision, the override "
     "reason and the final decision should be logged as separate fields. *[Editor's note (v2): v1 logged only the "
     "score, the final decision and its source; v2 logs the model decision, the fired rules and the precedence "
     "mode separately.]*"),
    # v1 6 opening: Phase 1 only
    (re.compile(r"No experiment involves real users, a real LLM, real reviewers or a real external recipient\."),
     "No Phase 1 experiment involves real users, a real LLM, real reviewers or a real external recipient. "
     "*[Editor's note (v2): Phase 2 adds a real-LLM pilot with `qwen2.5:3b`; main text Section V-C.]*"),
    # Figure 2 caption (panel B proposed, now implemented)
    (re.compile(r"\(B\) The proposed invariant of Section 4\.10, scoped to sensitive external transmissions; it is not implemented\."),
     "(B) The invariant proposed in v1, scoped to sensitive external transmissions; implemented in v2 as `max_severity`."),
    # v1 2.3 table: rows v2 changed
    (re.compile(r"\| Audit \| hash-chained, tamper-evident \| append-only by convention, not hash-chained \|"),
     "| Audit | hash-chained, tamper-evident | v1: append-only by convention; v2: hash-chained |"),
    (re.compile(r"\| LLMs \| real LLMs \(deepseek-v4-pro, four more backends\) \| scripted LLM only \|"),
     "| LLMs | real LLMs (deepseek-v4-pro, four more backends) | v1: scripted LLM only; v2: one local 3B model (pilot) |"),
    (re.compile(r"PrivAgent's evaluation is weaker in realism: no real LLM, synthetic trajectories, and a scripted workload\. It also lacks a tamper-evident audit log\."),
     "PrivAgent's v1 evaluation was weaker in realism: no real LLM, synthetic trajectories, and a scripted workload, "
     "and v1 lacked a tamper-evident audit log. *[Editor's note (v2): v2 adds a hash-chained log and a small "
     "real-LLM pilot; the realism gap to Wang et al. remains (one 3B model, scripted family B writer).]*"),
    (re.compile(r"Provenance enforcement is not globally enabled, and its false-positive cost is unmeasured\."),
     "Provenance enforcement was not enabled in v1, and its false-positive cost was unmeasured. *[Editor's note (v2): "
     "v2 enforces provenance in the primary configuration and measures the cost (main text H3).]*"),
    (re.compile(r"\*\*shadow only\*\* \|"), "**shadow only** (v1); enforced in v2 |"),
    (re.compile(r"\| Rules \| five rules, first match \| three rules that replace the ML decision \|"),
     "| Rules | five rules, first match | three rules; v1: a firing rule replaces the ML decision; v2: rules only escalate |"),
    (re.compile(r"\| Evaluation \| attack success, task success and false-positive/false-negative rates over LLM-driven runs \| step-level detection metrics on synthetic trajectories; scripted demonstrations \|"),
     "| Evaluation | attack success, task success and false-positive/false-negative rates over LLM-driven runs | v1: step-level detection metrics on synthetic trajectories; scripted demonstrations; v2 adds canary-based attack success on scripted graph scenarios and a 3B-model pilot |"),
]


def slice_v1(text, start, end):
    a = text.index("\n" + start + "\n") + 1
    b = text.index("\n" + end + "\n", a)
    return text[a:b].rstrip().rstrip("-").rstrip()


def v1_clean(block):
    block = re.sub(r"\[(\d{1,2})\]", lambda m: f"[{V1_REFS[int(m.group(1))]}]", block)
    block = block.replace("](figures/", "](../final/figures/")
    for pat, rep in EDITS:
        block = pat.sub(lambda m: rep, block)
    # demote headings two levels so they sit under the S-section heading
    return re.sub(r"^(#{2,4}) ", lambda m: "#" * min(len(m.group(1)) + 1, 6) + " ", block, flags=re.M)


def ledger_rows(prefix):
    t = open(LEDGER, encoding="utf-8").read()
    return [m.group(0) for m in re.finditer(r"^\| (%s\d+[a-z]?) \|.*$" % prefix, t, flags=re.M)]


def mapping():
    ms = open(MS, encoding="utf-8").read()
    out = ["| Manuscript section | Ledger rows cited |", "|---|---|"]
    for sec in re.split(r"\n(?=## )", ms):
        head = sec.splitlines()[0].lstrip("# ").strip()
        if not sec.startswith("## "):        # text before the first section: title, abstract, index terms
            head = "Title and Abstract"
        ids = []
        for c in re.findall(r"<!--(.*?)-->", sec, flags=re.S):
            for i in re.findall(r"(v1:#\d+|\b[A-Z]\d+[a-z]?\b)", c):
                if re.fullmatch(r"v1:#\d+|[CPSVXDL]\d+[a-z]?", i) and i not in ids:
                    ids.append(i)
        if ids:
            out.append(f"| {head} | {', '.join(ids)} |")
    return "\n".join(out)


VERIFY_LOG = """| Reference | Checked against (17 Nov 2026 unless stated) | Status |
|---|---|---|
| CaMeL | https://arxiv.org/abs/2503.18813; https://www.computer.org/csdl/proceedings-article/satml/2026/785900a587/2jZks3ksGT6 | arXiv record verified. Venue: Proc. IEEE SaTML 2026, verified by the author in a browser on 17 Nov 2026 (the CSDL page does not render for automated fetching). Pages **[VERIFY]** |
| FIDES | https://neurips.cc/virtual/2026/poster/152696; https://arxiv.org/abs/2505.23643 | NeurIPS 2026 (title and authors as on the conference page); page numbers not available |
| Permissive IFC | https://arxiv.org/abs/2410.03055; https://www.microsoft.com/en-us/research/publication/permissive-information-flow-analysis-for-large-language-models/ | TMLR, Oct. 2025, as listed by Microsoft Research (per the authors' instruction); the OpenReview page (id ufYRO8y3mr) could not be read |
| CapAgent | https://api.crossref.org/works/10.3390/bdcc10090293 | verified (Crossref); publisher page returned HTTP 403 |
| Arp et al. | https://www.usenix.org/conference/usenixsecurity22/presentation/arp | verified |
| TESSERACT | https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury | verified |
| AgentLeak | https://api.crossref.org/works/10.1109/ACCESS.2026.3704541; https://arxiv.org/abs/2602.11510 | verified |
| GuardAgent | https://proceedings.mlr.press/v267/xiang25a.html | verified |
| ShieldAgent | https://proceedings.mlr.press/v267/chen25ae.html | verified |
| Kairos | https://arxiv.org/abs/2610.18457 | verified; identity confirmed by the authors |
| Noumi et al. (Inspectra) | https://arxiv.org/abs/2608.21423 | verified (title, authors, submission date; the abstract names Inspectra as the authors' platform) |
| McNemar | https://api.crossref.org/works?query.bibliographic=McNemar... (DOI 10.1007/BF02295996) | verified (Crossref) |
| Claude Code (AI system, cited in Sections I–IX) | https://code.claude.com/docs/en/overview | page title and product name verified |
| DeLong et al. | Crossref (DOI 10.2307/2531595) | verified except the end page (Crossref gives the first page only) **[VERIFY]** |
| All other references | carried from the v1 paper, whose ledger records them as LIT (v1 ledger rows 40, 41) | not re-checked in this pass |
"""


def main():
    v1 = open(V1, encoding="utf-8").read()
    out = ["# PrivAgent v2: Supplementary Material", "",
           "Supplementary Material for *What Stops a Leak? A Pre-Registered Evaluation of Learned, Rule-Based and "
           "Human Controls for Multi-Agent LLM Governance*. Generated by `research_paper/v2/build/make_supplementary.py`; "
           "every move from the main text is listed in `research_paper/v2/RESTRUCTURE_LOG.md`.", "",
           "Citations inside moved v1 blocks name the work; the numbered list is in the main text.", ""]
    for sid, title, start, end in BLOCKS:
        if title:
            out += [f"## {sid}. {title}", "", V1_NOTE, ""]
        out += [v1_clean(slice_v1(v1, start, end)), ""]
    out += ["## S9. Development results (not confirmatory)", "",
            "Development data only (WP1–WP6, before the freeze). Each row is quoted from the claim–evidence ledger "
            "(`research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md`), with its artifact, commit and status.", "",
            "| # | Claim | Planned location | Supporting artifact | Commit | Status |", "|---|---|---|---|---|---|",
            *ledger_rows("D"), "",
            "## S10. Exploratory analyses: per-task table", "",
            "The per-task outcome table for the `v2` family B runs (EXPLORATORY, not pre-registered) is in "
            "`experiments/v2/exploratory/EXPLORATORY_v2_familyB_and_H4b.md`, Section 1.", "",
            "## S11. Claim–evidence mapping of the main text", "",
            "Every number in the main text cites a ledger row in an HTML comment. This table lists, per section, the "
            "rows cited (generated from the manuscript). The full ledger, with artifacts, commits and statuses, is "
            "`research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md`; `v1:#N` is row N of "
            "`research_paper/final/CLAIM_EVIDENCE_LEDGER.md`.", "", mapping(), "",
            "## S12. Reference verification", "", VERIFY_LOG]
    open(DST, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("wrote", DST)


if __name__ == "__main__":
    main()
