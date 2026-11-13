"""
Figure 2 (decision precedence) for the final manuscript.

Redrawn on 12 Nov 2026 so that the diagram separates the CURRENT
implementation (a firing rule replaces the ML decision; R2 can downgrade an
ML BLOCKED to HUMAN_APPROVAL when R1 does not fire) from the PROPOSED,
not-implemented invariant of Section 4.10. Same drawing helpers and palette as
research_paper/revised/build/make_revised_figures.py, which is left unchanged.

    python research_paper/final/build/make_figure2_final.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "research_paper", "final", "figures")

BLUE, ORANGE, GREEN, RED, GRAY = "#2a78d6", "#c26a0c", "#2f7d32", "#b42318", "#8c8b86"
INK, MUTED = "#1d1d1b", "#55544f"
FILL = {"default": "#eef3fb", "observed": "#fdeceb", "optin": "#eaf4ea", "proposed": "#f6f6f4"}
EDGE = {"default": BLUE, "observed": RED, "optin": GREEN, "proposed": GRAY}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def box(ax, x, y, w, h, text, kind, fs=7.5, ls="-", ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                fc=FILL[kind], ec=EDGE[kind], lw=1.2, linestyle=ls))
    tx = x + w / 2 if ha == "center" else x + 0.012
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=INK, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=MUTED,
                                 lw=1.1, shrinkA=1, shrinkB=1))


def main():
    fig, ax = plt.subplots(figsize=(10, 5.0))
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Panel A: current implementation
    ax.text(0.0, 0.975, "A. CURRENT IMPLEMENTATION (as coded and logged)", fontsize=8.6,
            fontweight="bold", color=BLUE, va="top")
    box(ax, 0.0, 0.68, 0.17, 0.22, "ML decision\nfrom score r\n(thresholds\n0.22 / 0.50 / 0.85)", "default")
    box(ax, 0.22, 0.68, 0.2, 0.22, "PolicyEngine, in order:\nR1 -> BLOCKED\nR2 -> HUMAN_APPROVAL\nR3 -> BLOCKED\n(first that fires)",
        "default")
    box(ax, 0.47, 0.68, 0.18, 0.22, "Final decision:\nfiring rule REPLACES\nthe ML decision\n(even if less restrictive);\nelse ML decision",
        "default")
    box(ax, 0.70, 0.80, 0.29, 0.10, "Default graph: HUMAN_APPROVAL\nis not executed (acts as a block)", "default")
    box(ax, 0.70, 0.66, 0.29, 0.11, "Approval graph: offered for review;\nan approval EXECUTES it", "optin")
    arrow(ax, 0.17, 0.79, 0.22, 0.79)
    arrow(ax, 0.42, 0.79, 0.47, 0.79)
    arrow(ax, 0.65, 0.82, 0.70, 0.85)
    arrow(ax, 0.65, 0.74, 0.70, 0.715)

    box(ax, 0.0, 0.43, 0.99, 0.19,
        "Downgrade path (observed): ML BLOCKED (r >= 0.85) and R2 fires while R1 does not  ->  final HUMAN_APPROVAL.\n"
        "Attack Lab: 3 scenarios (r = 0.995-0.999). Dashboard demo demo_9e6a8ae2: r = 0.9952, offered for review, rejected.\n"
        "R1 is checked before R2, so after >= 2 prior sensitive actions R1 blocks instead. Logged: score, final decision, source\n"
        "(ml_model / policy_engine); the ML decision is not a separate log field.",
        "observed", fs=7.3, ha="left")

    # Panel B: proposal, visually separated
    ax.plot([0.0, 0.99], [0.385, 0.385], color=GRAY, lw=0.8, ls=(0, (4, 3)))
    ax.text(0.0, 0.355, "B. PROPOSED FUTURE WORK (Section 4.10) - NOT IMPLEMENTED; the policy engine is unchanged",
            fontsize=8.6, fontweight="bold", color=MUTED, va="top")
    box(ax, 0.0, 0.03, 0.99, 0.26,
        "Scope: external transmissions of sensitive data.\n"
        "- A BLOCKED decision is never automatically downgraded to HUMAN_APPROVAL, RESTRICTED or AUTONOMOUS.\n"
        "- Policies may escalate restrictions but not relax them; conflicts resolve to the more restrictive outcome,\n"
        "  unless an explicit and logged exception applies.\n"
        "- ML decision, policy decision, override reason and final decision are logged as separate fields.\n"
        "- Cost in false positives and review burden has not been measured.",
        "proposed", fs=7.3, ls="--", ha="left")

    path = os.path.join(OUT, "r04_decision_precedence.png")
    fig.savefig(path, dpi=220, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    main()
