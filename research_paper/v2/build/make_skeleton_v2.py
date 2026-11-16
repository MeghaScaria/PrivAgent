"""
Builds research_paper/v2/PrivAgent_v2_DRAFT.md from the frozen v1 paper
(research_paper/final/PrivAgent_Research_Paper_Final.md, read only).

Mechanical edits only; no new prose claims:
  1. A status note under the title (what this file is).
  2. References renumbered in order of first citation (IEEE), every in-text
     [n] rewritten to match. References never cited in the text are kept at
     the end and marked [VERIFY: not cited in the text].
  3. Citations that need updating are marked [VERIFY], in the text and in
     the reference list. Works not in the v1 reference list get placeholder
     entries with no bibliographic details (to be filled from the
     publications, not from memory).
  4. Appendix A restored: the per-experiment script -> output rows of the
     original paper (dropped in the final version) and the final figure
     script are added back; paths checked to exist.
  5. Empty section headings for the v2 material, each with the ledger rows
     (research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md) it will use.

    python research_paper/v2/build/make_skeleton_v2.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, "research_paper", "final", "PrivAgent_Research_Paper_Final.md")
DST = os.path.join(ROOT, "research_paper", "v2", "PrivAgent_v2_DRAFT.md")
CITE = re.compile(r"\[(\d{1,2})\]")

# v1 reference numbers whose entries need updating (identified by title, checked below)
VERIFY_V1 = {7: "Defeating prompt injections by design",        # CaMeL
             8: "Securing AI agents with information-flow control",  # FIDES
             9: "Permissive information-flow analysis",
             11: "CapAgent"}
NEW_REFS = ["Arp et al.", "TESSERACT", "AgentLeak", "GuardAgent", "ShieldAgent", "Kairos", "Inspectra"]

STATUS = ("> **PrivAgent v2 working draft: SKELETON (17 Nov 2026).** The text below is the v1 final paper "
          "(`research_paper/final/PrivAgent_Research_Paper_Final.md`), unchanged except for the mechanical edits "
          "listed in `research_paper/v2/build/make_skeleton_v2.py` (reference order, [VERIFY] marks, Appendix A, "
          "empty v2 headings). No v2 prose has been written; every v2 heading lists the ledger rows of "
          "`research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md` it will use.")


def rows(*ids):
    return "\n".join(f"- {i}" for i in ids)


def section(heading, ledger, extra=()):
    out = [heading, "", "*[Not yet written.]* Ledger rows to use:", "", rows(*ledger)]
    out += [f"- {e}" for e in extra]
    return "\n".join(out) + "\n"


V2_SECTIONS = {
    # inserted immediately before the heading given as key
    "## 3. Problem Definition and Threat Model": section(
        "### 2.7 Related work added for v2 [VERIFY]",
        ["(no ledger rows; LIT entries to be verified: Arp et al., TESSERACT, AgentLeak, GuardAgent, ShieldAgent, "
         "Kairos, Inspectra, and the updated CaMeL, FIDES, Permissive IFC, CapAgent entries)"]),
    "## 5. Implementation Summary": "\n".join([
        section("### 4.13 v2: escalation-only decision precedence (WP1)", ["D1", "D2"]),
        section("### 4.14 v2: scored agent handoffs (WP2)", ["D3", "D4"]),
        section("### 4.15 v2: RESTRICTED semantics, hash-chained logs and send binding (WP3)", ["D5", "D6"]),
        section("### 4.16 v2: enforced provenance and the declaration study (WP4)", ["D7", "D8"])]),
    "## 7. Results": section(
        "### 6.1 v2: pre-registered confirmatory protocol",
        ["P1", "P2", "P3", "P4", "C21", "C22"]),
    "## 8. Discussion": "\n".join([
        "### 7.5 v2 confirmatory results\n",
        section("#### 7.5.1 H1: escalation-only precedence", ["C1", "C2", "C3", "C4", "C5", "C6"],
                ["Figure: `research_paper/v2/figures/v2_f3_h1_live_costs.png`"]),
        section("#### 7.5.2 H2: scored handoffs", ["C7", "C8", "C9"]),
        section("#### 7.5.3 H3: enforced provenance", ["C10", "C11"]),
        section("#### 7.5.4 H4: shortcut vs generalisation on real traces", ["C12", "C13", "C14"],
                ["Figure: `research_paper/v2/figures/v2_f4_h4a_recall.png`"]),
        section("#### 7.5.5 H5: defence comparison on a real LLM", ["C15", "C16", "C17", "C18", "C18b"],
                ["Figures: `research_paper/v2/figures/v2_f1_h5_asr.png`, `v2_f2_benign_utility.png`"]),
        section("#### 7.5.6 Multi-seed offline evaluation (descriptive)", ["C19", "C20"],
                ["Figure: `research_paper/v2/figures/v2_f5_multiseed_heldout.png`"]),
        section("#### 7.5.7 Independent recomputation", ["V1"]),
        section("### 7.6 v2 exploratory analyses (EXPLORATORY)", ["X1", "X2", "X3", "X4"]),
        section("### 7.7 v2 development results (not confirmatory)", ["D9", "D10", "D11"])]),
    "## 10. Future Work (proposed, not implemented)": section(
        "### 9.x v2 limitations and threats to validity", ["C14", "C21", "C22", "D10", "X2", "X3"]),
}

APPENDIX_ROWS = [
    ("Synthetic data generator", "`data/generate_trajectories.py`"),
    ("Experiment 2 (position ablation)", "`experiments/position_ablation.py` → `experiments/results/position_ablation.{json,md}`; "
     "round 1: `experiments/results/round1_position_ablation.{json,md}`"),
    ("Experiment 3 (flow features)", "`experiments/phase3_flow_features.py` → `experiments/results/phase3_flow_features.{json,md}`"),
    ("Attack Lab", "`experiments/attack_lab_replay.py` → `experiments/results/attack_lab_replay.md`"),
    ("Experiment 5 (approval)", "`experiments/approval_evaluation.py` → `experiments/results/approval_evaluation.{json,md}`"),
    ("Final figures", "`research_paper/final/figures/`; Figure 2: `research_paper/final/build/make_figure2_final.py`"),
]
APPENDIX_B = """### Appendix B. v2 reproducibility

| Item | Location |
|---|---|
| Pre-registration and its hash | `experiments/v2/PREREGISTRATION_v2.md`; `experiments/v2/PREREGISTRATION_HASHES.md` |
| Confirmatory results | `experiments/v2/results/confirmatory/` |
| Pre-registered analyses | `experiments/v2/analysis/h1.py` … `h5.py` → `experiments/v2/results/confirmatory/analysis/` |
| Confirmatory report; independent recomputation | `experiments/v2/CONFIRMATORY_REPORT.md`; `experiments/v2/INDEPENDENT_CHECK.md` |
| Exploratory analyses | `experiments/v2/exploratory/` |
| Development results | `experiments/v2/results/` (files marked DEVELOPMENT) |
| v2 figures | `research_paper/v2/figures/make_figures_v2.py` |
| Claim-to-evidence ledger | `research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md` |
"""


def main():
    with open(SRC, encoding="utf-8") as f:
        text = f.read()
    ref_at = text.index("\n## References\n")
    app_at = text.index("\n### Appendix A. Reproducibility\n")
    body, refs_block, appendix = text[:ref_at], text[ref_at:app_at], text[app_at:]

    # --- references ---
    entries = dict((int(m.group(1)), m.group(0).strip())
                   for m in re.finditer(r"^\[(\d+)\] .*$", refs_block, flags=re.M))
    for n, title in VERIFY_V1.items():
        assert title in entries[n], (n, title)
    order = []
    for m in CITE.finditer(body):
        n = int(m.group(1))
        if n in entries and n not in order:
            order.append(n)
    uncited = [n for n in sorted(entries) if n not in order]
    new_num = {old: i + 1 for i, old in enumerate(order + uncited)}

    def renumber(m):
        old = int(m.group(1))
        if old not in new_num:
            return m.group(0)
        mark = " [VERIFY]" if old in VERIFY_V1 else ""
        return f"[{new_num[old]}]{mark}"
    body = CITE.sub(renumber, body)
    lines = []
    for old in order + uncited:
        e = re.sub(r"^\[\d+\]", f"[{new_num[old]}]", entries[old])
        if old in VERIFY_V1:
            e += " **[VERIFY]**: details to be checked against the current publication record."
        if old in uncited:
            e += " **[VERIFY: not cited in the text]**"
        lines.append(e)
    k = len(lines)
    for i, name in enumerate(NEW_REFS, start=1):
        lines.append(f"[{k + i}] **[VERIFY]** {name}: placeholder; bibliographic details to be added from the "
                     "publication itself (not filled from memory). Not yet cited in the text.")
    refs_block = "\n## References\n\n" + "\n\n".join(lines) + "\n\n---\n"

    # --- appendix A: restore dropped rows, then append appendix B ---
    for _, loc in APPENDIX_ROWS:
        for p in re.findall(r"`([^`]+)`", loc):
            for q in ([p.replace("{json,md}", e) for e in ("json", "md")] if "{json,md}" in p else [p]):
                assert os.path.exists(os.path.join(ROOT, q)), q
    add = "\n".join(f"| {a} | {b} |" for a, b in APPENDIX_ROWS)
    appendix = appendix.rstrip("\n") + "\n" + add + "\n\n" + APPENDIX_B

    # --- v2 headings ---
    for anchor, block in V2_SECTIONS.items():
        assert body.count("\n" + anchor + "\n") == 1, anchor
        body = body.replace("\n" + anchor + "\n", "\n" + block + "\n" + anchor + "\n")

    # --- status note under the subtitle line ---
    marker = "\n---\n\n**Abstract.**"
    assert body.count(marker) == 1
    body = body.replace(marker, "\n" + STATUS + "\n" + marker)

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="utf-8", newline="\n") as f:
        f.write(body + refs_block + appendix)
    print("order of first citation (old numbers):", order, "uncited:", uncited)
    print("wrote", DST)


if __name__ == "__main__":
    main()
