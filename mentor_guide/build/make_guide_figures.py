"""
Figures for the PrivAgent learning guide. New conceptual diagrams are
drawn here; result charts are copied unchanged from
research_paper/PrivAgent_Figures/ (themselves generated from the result
files). Run from the repository root:

    python mentor_guide/build/make_guide_figures.py
"""
import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "mentor_guide", "figures")
PAPER_FIGS = os.path.join(ROOT, "research_paper", "PrivAgent_Figures")
os.makedirs(OUT, exist_ok=True)

BLUE, ORANGE, GRAY, RED, GREEN = "#2a78d6", "#c26a0c", "#8c8b86", "#b42318", "#2f7d32"
INK, MUTED, GRID = "#1d1d1b", "#55544f", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc="#f4f6fa", ec="#9aa7b8", fs=8, bold=False, tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015",
                                fc=fc, ec=ec, lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, color="#55544f", ls="-", lw=1.1):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color=color,
                                 lw=lw, linestyle=ls, shrinkA=1, shrinkB=1))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def per_call_vs_trajectory():
    fig, ax = canvas(9.5, 4.2)
    steps = [("1. Retriever reads\nHR document", "looks OK"), ("2. Retriever queries\nemployees table", "looks OK"),
             ("3. Analyst summarises\n(handoff, not a tool call)", "not checked at all"), ("4. Writer sends summary\nto external address",
                                                                      "OK if it says\n'not sensitive'")]
    ax.text(0.01, 0.95, "Per-call check: each step judged alone", fontsize=10, fontweight="bold", color=INK)
    for i, (s, v) in enumerate(steps):
        x = 0.01 + i * 0.25
        box(ax, x, 0.66, 0.21, 0.2, s, fs=8)
        ax.text(x + 0.105, 0.6, v, ha="center", va="top", fontsize=7.5, color=GREEN)
        if i:
            arrow(ax, x - 0.04, 0.76, x, 0.76)
    ax.text(0.01, 0.42, "Trajectory-aware check: step 4 judged with everything executed before it",
            fontsize=10, fontweight="bold", color=INK)
    for i, (s, _) in enumerate(steps):
        x = 0.01 + i * 0.25
        box(ax, x, 0.13, 0.21, 0.2, s, fc="#eef3fb" if i < 3 else "#fdecea", ec=BLUE if i < 3 else RED, fs=8)
        if i:
            arrow(ax, x - 0.04, 0.23, x, 0.23)
    ax.add_patch(FancyBboxPatch((0.005, 0.1), 0.715, 0.26, boxstyle="round,pad=0.005", fc="none", ec=BLUE,
                                lw=1.4, ls="--"))
    ax.text(0.36, 0.05, "prefix: 2 sensitive reads already executed", ha="center", fontsize=8, color=BLUE)
    ax.text(0.865, 0.05, "same action, now high risk", ha="center", fontsize=8, color=RED)
    save(fig, "g01_per_call_vs_trajectory.png")


def threshold_bar():
    fig, ax = plt.subplots(figsize=(9, 1.7))
    bands = [(0, 0.22, "#d9ead3", "AUTONOMOUS\n(executes)"), (0.22, 0.50, "#fff2cc", "RESTRICTED\n(executes; nothing "
             "restricted today)"), (0.50, 0.85, "#fce5cd", "HUMAN_APPROVAL\n(not executed in default graph)"),
             (0.85, 1.0, "#f4cccc", "BLOCKED\n(not executed)")]
    for a, b, c, t in bands:
        ax.barh(0, b - a, left=a, color=c, edgecolor="white", height=0.6)
        ax.text((a + b) / 2, 0, t, ha="center", va="center", fontsize=7.5, color=INK)
    for t in (0.22, 0.50, 0.85):
        ax.axvline(t, color=INK, lw=1)
        ax.text(t, 0.42, f"{t:.2f}", ha="center", fontsize=8, color=INK)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("risk score r = model's probability that the action is unsafe")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    save(fig, "g02_threshold_scale.png")


def default_flowchart():
    fig, ax = canvas(9.5, 5.2)
    box(ax, 0.02, 0.82, 0.22, 0.12, "Agent proposes a tool call\n(e.g. query_database)", fc="#eef3fb", ec=BLUE)
    box(ax, 0.30, 0.82, 0.24, 0.12, "TrajectoryMonitor.evaluate()\nbuild candidate action", fc="#eef3fb", ec=BLUE)
    box(ax, 0.60, 0.82, 0.18, 0.12, "Features from\nprefix + candidate")
    box(ax, 0.82, 0.82, 0.16, 0.12, "RiskEngine\nscore r")
    box(ax, 0.82, 0.58, 0.16, 0.12, "AutonomyController\nr -> ML decision")
    box(ax, 0.56, 0.58, 0.22, 0.12, "PolicyEngine: does a\nhard rule fire?")
    box(ax, 0.30, 0.58, 0.22, 0.12, "Final decision\n(rule replaces ML if it fires)")
    box(ax, 0.30, 0.34, 0.22, 0.12, "AuditLogger writes\none JSON line")
    box(ax, 0.02, 0.34, 0.22, 0.12, "Allowed?\nAUTONOMOUS or RESTRICTED", fc="#fff8e1", ec=ORANGE)
    box(ax, 0.02, 0.08, 0.22, 0.14, "YES: call MCP server,\nappend to trajectory,\nregister result refs",
        fc="#e8f5e9", ec=GREEN)
    box(ax, 0.30, 0.08, 0.30, 0.14, "NO: tool not called, nothing\nregistered, not added to trajectory;\n"
        "agent receives a 'blocked' result", fc="#fdecea", ec=RED)
    arrow(ax, 0.24, 0.88, 0.30, 0.88)
    arrow(ax, 0.54, 0.88, 0.60, 0.88)
    arrow(ax, 0.78, 0.88, 0.82, 0.88)
    arrow(ax, 0.90, 0.82, 0.90, 0.70)
    arrow(ax, 0.82, 0.64, 0.78, 0.64)
    arrow(ax, 0.56, 0.64, 0.52, 0.64)
    arrow(ax, 0.41, 0.58, 0.41, 0.46)
    arrow(ax, 0.30, 0.40, 0.24, 0.40)
    arrow(ax, 0.13, 0.34, 0.13, 0.22)
    arrow(ax, 0.24, 0.30, 0.36, 0.22)
    save(fig, "g03_default_decision_flow.png")


def provenance_example():
    fig, ax = canvas(9.5, 4.6)
    box(ax, 0.01, 0.75, 0.2, 0.15, "ref1: task text\nuser input\nPII regex: none -> 0", fs=7.5)
    box(ax, 0.01, 0.45, 0.2, 0.15, "ref2: hr_007 document\nsource label 'high' -> 1", fc="#fdecea", ec=RED, fs=7.5)
    box(ax, 0.01, 0.15, 0.2, 0.15, "ref3: employees#12\ntable policy -> 1", fc="#fdecea", ec=RED, fs=7.5)
    box(ax, 0.30, 0.45, 0.2, 0.15, "ref4: analysis\nderived from ref1-3\ninherited max -> 1", fc="#fdecea", ec=RED,
        fs=7.5)
    box(ax, 0.57, 0.45, 0.2, 0.15, "ref5: final answer\nderived from ref4, ref1\ninherited -> 1", fc="#fdecea",
        ec=RED, fs=7.5)
    box(ax, 0.82, 0.45, 0.17, 0.15, "send_result\n(outbound)", fc="#eef3fb", ec=BLUE, fs=8)
    for y in (0.825, 0.525, 0.225):
        arrow(ax, 0.21, y, 0.30, 0.525)
    arrow(ax, 0.50, 0.525, 0.57, 0.525)
    arrow(ax, 0.77, 0.525, 0.82, 0.525)
    box(ax, 0.30, 0.78, 0.47, 0.12, "Analyst declares contains_sensitive_data = False\n"
        "-> flag: self_report_disagrees_with_provenance", fc="#fff8e1", ec=ORANGE, fs=7.5)
    box(ax, 0.42, 0.08, 0.57, 0.22, "Shadow mode (default): enforced decision uses declared 0;\n"
        "the authoritative label max(provenance 1, declared 0) = 1 is logged with\n"
        "flag declared_lower_than_provenance and the decision it WOULD give.\n"
        "Enforce mode (exists, not enabled): the model would score label 1.", fc="#fbf4ea", ec=ORANGE, fs=7.5)
    save(fig, "g04_provenance_example.png")


def approval_flow():
    fig, ax = canvas(9.5, 4.8)
    nodes = [("writer_compose\nLLM writes payload;\nstate minimised", 0.01),
             ("transmission_gate\ngovernance + flow rule\n-> pending action", 0.205),
             ("human_approval\ninterrupt(): pause,\ncheckpoint saved", 0.40),
             ("transmission_execute\ncheck digest + token\nledger.claim(id)", 0.595),
             ("external_server\nsend_result", 0.80)]
    for t, x in nodes:
        box(ax, x, 0.68, 0.18, 0.2, t, fc="#eef3fb" if "external" not in t else "white",
            ec=BLUE if "external" not in t else "#9aa7b8", fs=7.5)
    for i in range(4):
        arrow(ax, nodes[i][1] + 0.18, 0.78, nodes[i + 1][1], 0.78)
    box(ax, 0.40, 0.40, 0.18, 0.16, "Reviewer (UI or code)\napprove / reject\n+ action_id + digest",
        fc="#fff8e1", ec=ORANGE, fs=7.5)
    arrow(ax, 0.49, 0.68, 0.49, 0.56, ls="--")
    arrow(ax, 0.58, 0.48, 0.66, 0.68, ls="--")
    ax.text(0.60, 0.55, "Command(resume=...)", fontsize=7, color=MUTED)
    box(ax, 0.595, 0.08, 0.385, 0.24, "ExecutionLedger (SQLite)\nINSERT action_id, status 'executing' (claim)\n"
        "-> call tool -> UPDATE 'executed' or 'failed'\nSecond claim on the same id fails:\n"
        "at most one execution attempt per action id", fc="#fbf4ea", ec=ORANGE, fs=7.5)
    arrow(ax, 0.685, 0.68, 0.685, 0.32)
    box(ax, 0.01, 0.08, 0.53, 0.24, "Reject, malformed or mismatched response -> run halts, nothing sent.\n"
        "Crash after claim but before 'executed': entry stays 'executing';\n"
        "a retry is refused, so delivery is NOT recorded (ambiguous).\n"
        "No exactly-once delivery is claimed.", fc="#fdecea", ec=RED, fs=7.5)
    save(fig, "g05_approval_flow.png")


def data_generation():
    fig, ax = canvas(9.5, 3.4)
    ax.text(0.01, 0.92, "Randomized training run: an attack template embedded in benign padding",
            fontsize=10, fontweight="bold", color=INK)
    seq = ["b", "b", "b", "A1", "b", "A2", "b", "b", "A3", "b"]
    for i, s in enumerate(seq):
        x = 0.01 + i * 0.098
        atk = s.startswith("A")
        box(ax, x, 0.5, 0.085, 0.22, s if atk else "benign", fc="#fdecea" if atk else "#f4f6fa",
            ec=RED if atk else "#9aa7b8", fs=8)
    ax.text(0.01, 0.38, "0-8 benign steps before | 0-3 between stages | 0-4 after   (30% of attack runs are "
            "'compact': no padding)", fontsize=8, color=MUTED)
    ax.text(0.01, 0.24, "Labels come from the template only: each stage gets 0 or 1 from the original PrivAgent "
            "rule (not every stage is unsafe); every benign step is 0.", fontsize=8, color=MUTED)
    ax.text(0.01, 0.10, "Each step becomes one training row: features of (executed prefix, this step) + label.",
            fontsize=8, color=INK)
    save(fig, "g06_training_data.png")


def copy_paper_figures():
    mapping = {"fig01_architecture.png": "p01_architecture.png",
               "fig03_decision_pipeline.png": "p03_decision_pipeline.png",
               "fig04_evaluation_correction.png": "p04_evaluation_correction.png",
               "fig05_position_recall.png": "p05_position_recall.png", "fig06_phase3_loto.png": "p06_phase3_loto.png",
               "fig08_approval_outcomes.png": "p08_approval_outcomes.png"}
    for src, dst in mapping.items():
        shutil.copyfile(os.path.join(PAPER_FIGS, src), os.path.join(OUT, dst))


if __name__ == "__main__":
    per_call_vs_trajectory()
    threshold_bar()
    default_flowchart()
    provenance_example()
    approval_flow()
    data_generation()
    copy_paper_figures()
    print("figures in", OUT)
