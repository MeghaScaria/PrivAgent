"""
Figures for the revised manuscript. New explanatory diagrams are drawn
here; result charts are copied unchanged from ../PrivAgent_Figures (which
research_paper/build/make_figures.py generated from the result files).

    python research_paper/revised/build/make_revised_figures.py
"""
import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "research_paper", "revised", "figures")
SRC = os.path.join(ROOT, "research_paper", "PrivAgent_Figures")
os.makedirs(OUT, exist_ok=True)

BLUE, ORANGE, GREEN, RED, GRAY = "#2a78d6", "#c26a0c", "#2f7d32", "#b42318", "#8c8b86"
INK, MUTED = "#1d1d1b", "#55544f"
FILL = {"default": "#eef3fb", "shadow": "#fbf4ea", "optin": "#eaf4ea", "neutral": "#f6f6f4"}
EDGE = {"default": BLUE, "shadow": ORANGE, "optin": GREEN, "neutral": "#9aa7b8"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, kind="neutral", fs=7.5, bold=False, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                fc=FILL[kind], ec=EDGE[kind], lw=1.2, linestyle=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, color=MUTED, ls="-", lw=1.1):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=color,
                                 lw=lw, linestyle=ls, shrinkA=1, shrinkB=1))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=220, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def architecture():
    fig, ax = canvas(10, 6.2)
    ax.text(0.01, 0.97, "Agents (LangGraph StateGraph)", fontsize=9, fontweight="bold", color=MUTED)
    for i, a in enumerate(["Orchestrator\n(LLM; no tools)", "Retriever\n(governed reads)", "Analyst\n(LLM; no tools)",
                           "Writer\n(answer; optional send)"]):
        box(ax, 0.01 + i * 0.25, 0.85, 0.21, 0.09, a, "default", fs=7.5)
        if i:
            arrow(ax, i * 0.25 - 0.03, 0.895, 0.01 + i * 0.25, 0.895)
    # Shadow lane
    box(ax, 0.01, 0.72, 0.96, 0.08, "HandoffTracker: records agent-to-agent transfers  ->  ProvenanceRegistry: refs, "
        "origins, inherited labels  ->  handoff_log.jsonl\n(recorded and propagated; NOT added to the scored "
        "trajectory; never enforced)", "shadow", fs=7.2)
    # Default governed path
    ax.text(0.01, 0.665, "Default governed tool execution (every tool call)", fontsize=9, fontweight="bold",
            color=BLUE)
    box(ax, 0.01, 0.53, 0.17, 0.11, "Governed wrapper\nagents/tools.py", "default")
    box(ax, 0.21, 0.53, 0.18, 0.11, "TrajectoryMonitor\nexecuted prefix\n(tool actions only)", "default")
    box(ax, 0.42, 0.53, 0.16, 0.11, "11 features ->\ngradient boosting\n-> score r", "default")
    box(ax, 0.61, 0.53, 0.16, 0.11, "Thresholds ->\nML decision", "default")
    box(ax, 0.80, 0.53, 0.17, 0.11, "PolicyEngine: rule\nREPLACES ML decision\n-> final decision", "default")
    for x1, x2 in ((0.18, 0.21), (0.39, 0.42), (0.58, 0.61), (0.77, 0.80)):
        arrow(ax, x1, 0.585, x2, 0.585)
    box(ax, 0.80, 0.38, 0.17, 0.1, "AuditLogger\naudit_log.jsonl", "default")
    arrow(ax, 0.885, 0.53, 0.885, 0.48)
    box(ax, 0.01, 0.38, 0.38, 0.1, "send_result only: provenance-authoritative label;\nshadow decision logged, "
        "enforced input unchanged", "shadow", fs=7.2)
    arrow(ax, 0.30, 0.53, 0.30, 0.48, color=ORANGE, ls="--")
    box(ax, 0.42, 0.38, 0.35, 0.1, "AUTONOMOUS / RESTRICTED: MCP call executes\nHUMAN_APPROVAL / BLOCKED: not "
        "executed (default graph)", "default", fs=7.2)
    arrow(ax, 0.83, 0.53, 0.70, 0.48)
    # Opt-in approval lane
    ax.text(0.01, 0.31, "Optional human approval (build_graph(..., approvals=...); writer's send only)", fontsize=9,
            fontweight="bold", color=GREEN)
    for i, t in enumerate(["transmission_gate\n+ escalation-only\nflow rule", "human_approval\ninterrupt(),\ncheckpoint",
                           "Reviewer\napprove / reject", "transmission_execute\ndigest + token,\nledger.claim"]):
        box(ax, 0.01 + i * 0.25, 0.16, 0.21, 0.12, t, "optin", fs=7.3)
        if i:
            arrow(ax, i * 0.25 - 0.03, 0.22, 0.01 + i * 0.25, 0.22, color=GREEN)
    # MCP
    ax.text(0.01, 0.105, "MCP client (stdio) -> document / database / web / external servers", fontsize=8.5,
            color=MUTED, fontweight="bold")
    for i, s in enumerate(["document_server", "database_server", "web_server", "external_server"]):
        box(ax, 0.01 + i * 0.25, 0.0, 0.21, 0.07, s, "neutral", fs=7.5)
    handles = [Patch(fc=FILL["default"], ec=BLUE, label="default execution path"),
               Patch(fc=FILL["shadow"], ec=ORANGE, label="shadow mode: recorded, not enforced"),
               Patch(fc=FILL["optin"], ec=GREEN, label="opt-in approval workflow")]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.06), fontsize=7.5, frameon=False, ncol=3)
    save(fig, "r01_architecture_three_tiers.png")


def split_diagram():
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.3))
    runs = [("Run 1", 5, "#e8eef9"), ("Run 2", 6, "#fbeee0"), ("Run 3", 4, "#e8f3e8")]
    for ax, title, mode in ((axes[0], "Original (Stage 0): one ID per row, row-level split", "row"),
                            (axes[1], "Corrected (Stage 1+): one ID per run, run-level split", "run")):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 5)
        ax.axis("off")
        ax.set_title(title, fontsize=9, loc="left", fontweight="bold", color=INK)
        y = 4.0
        k = 0
        for name, n, col in runs:
            ax.text(0.0, y + 0.3, name, fontsize=8, va="center", color=MUTED)
            for s in range(n):
                if mode == "row":
                    split = "test" if k % 4 == 3 else "train"
                else:
                    split = "test" if name == "Run 3" else "train"
                k += 1
                ax.add_patch(FancyBboxPatch((1.3 + s * 1.15, y), 1.0, 0.6, boxstyle="round,pad=0.02",
                                            fc=col, ec=RED if split == "test" else "#9aa7b8",
                                            lw=2.0 if split == "test" else 1.0))
                ax.text(1.8 + s * 1.15, y + 0.3, split, fontsize=7, ha="center", va="center",
                        color=RED if split == "test" else INK)
            y -= 1.25
        note = ("Steps of the SAME run fall in train and test:\nnear-duplicates leak into evaluation (F1 0.999)"
                if mode == "row" else "Every step of a run stays in one split;\nheld-out attack types scored "
                "separately (F1 0.657)")
        ax.text(0.0, 0.15, note, fontsize=7.5, color=RED if mode == "row" else GREEN)
    save(fig, "r02_row_vs_run_split.png")


def position_diagram():
    fig, ax = canvas(10, 3.2)
    ax.text(0.01, 0.93, "Legacy data: every attack template is a short standalone run, so unsafe steps sit at 1-3 "
            "fixed positions", fontsize=8.5, fontweight="bold", color=INK)
    for i in range(8):
        unsafe = i == 4
        box(ax, 0.01 + i * 0.075, 0.62, 0.065, 0.18, f"step {i + 1}", "shadow" if unsafe else "neutral", fs=7)
    ax.text(0.62, 0.71, "model learns 'step 5 of a short run = attack'\n(position-only classifier: val. AUROC "
            "0.951)", fontsize=7.8, color=RED, va="center")
    ax.text(0.01, 0.47, "Randomized data + position-invariant features (counts and maxima only)", fontsize=8.5,
            fontweight="bold", color=INK)
    for row, (pad, ytop) in enumerate(((0, 0.18), (3, 0.0))):
        for i in range(9):
            if i < pad:
                box(ax, 0.01 + i * 0.065, 0.2 - row * 0.19 + 0.02, 0.055, 0.14, "benign", "neutral", fs=6.2)
            elif i < pad + 3:
                box(ax, 0.01 + i * 0.065, 0.2 - row * 0.19 + 0.02, 0.055, 0.14, f"A{i - pad + 1}", "shadow", fs=6.5)
        ax.text(0.6, 0.2 - row * 0.19 + 0.09, f"offset {pad}", fontsize=7, color=MUTED, va="center", ha="right")
    ax.text(0.62, 0.2, "inserting harmless steps leaves every prefix feature unchanged:\nunsafe-step scores identical "
            "at offsets 0-20 (range 0.000)", fontsize=7.8, color=GREEN, va="center")
    save(fig, "r03_position_shortcut.png")


def precedence_diagram():
    fig, ax = canvas(10, 3.6)
    ax.set_xlim(-0.01, 1.01)
    box(ax, 0.0, 0.62, 0.17, 0.26, "ML decision\nfrom score r\n(e.g. r = 0.9952\n-> BLOCKED)", "default")
    box(ax, 0.22, 0.62, 0.2, 0.26, "PolicyEngine\nfirst matching rule:\nR1 BLOCKED, R2\nHUMAN_APPROVAL,\nR3 BLOCKED",
        "default")
    box(ax, 0.47, 0.62, 0.18, 0.26, "Final decision =\nrule decision if a\nrule fires, else ML\n(logged: score,\nfinal, source)",
        "default")
    box(ax, 0.70, 0.75, 0.29, 0.13, "Default graph: HUMAN_APPROVAL\nis not executed (acts as a block)", "default")
    box(ax, 0.70, 0.55, 0.29, 0.15, "Approval graph: offered for review;\nan approval EXECUTES it",
        "optin")
    arrow(ax, 0.17, 0.75, 0.22, 0.75)
    arrow(ax, 0.42, 0.75, 0.47, 0.75)
    arrow(ax, 0.65, 0.78, 0.70, 0.81)
    arrow(ax, 0.65, 0.70, 0.70, 0.63)
    box(ax, 0.0, 0.05, 0.99, 0.38,
        "Observed downgrade: ML BLOCKED -> R2 -> final HUMAN_APPROVAL (Attack Lab: 3 scenarios; dashboard demo "
        "demo_9e6a8ae2:\nr = 0.9952 offered for review, rejected by the reviewer). Rule R1 is checked before R2, so "
        "after >= 2 sensitive reads R1 blocks.\n\nProposed invariant (future work, NOT implemented): a BLOCKED "
        "decision must never be automatically downgraded to\nHUMAN_APPROVAL, RESTRICTED or AUTONOMOUS; policies may "
        "only escalate; conflicts resolve to the more restrictive outcome;\nML and policy decisions are logged "
        "separately; every override carries an explicit reason.", "shadow", fs=7.4)
    save(fig, "r04_decision_precedence.png")


def copy_results():
    for src, dst in {"fig04_evaluation_correction.png": "r05_evaluation_correction.png",
                     "fig05_position_recall.png": "r06_position_recall.png",
                     "fig06_phase3_loto.png": "r07_phase3_loto.png",
                     "fig07_phase3_variantc_falsealarm.png": "r08_phase3_variantc.png",
                     "fig08_approval_outcomes.png": "r09_approval_outcomes.png",
                     "fig09_persistence_ablation_exploratory.png": "r10_persistence_exploratory.png",
                     "fig02_request_lifecycle.png": "r11_approval_lifecycle.png"}.items():
        shutil.copyfile(os.path.join(SRC, src), os.path.join(OUT, dst))


if __name__ == "__main__":
    architecture()
    split_diagram()
    position_diagram()
    precedence_diagram()
    copy_results()
    print("figures in", OUT)
