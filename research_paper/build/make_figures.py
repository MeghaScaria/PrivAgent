"""
Generates every figure in PrivAgent_Figures/ from the repository's own
result files. No number is typed in by hand except where a source file
does not exist (none currently). Run from the repository root:

    python research_paper/build/make_figures.py

Sources (read-only):
  models/training_metrics.json                        deployed model metrics
  research_paper/evidence/stage0_original_training_metrics.json
  research_paper/evidence/stage1_corrected_eval_training_metrics.json
  experiments/results/position_ablation.json          Experiment 2
  experiments/results/phase3_flow_features.json       Experiment 3
  experiments/results/approval_evaluation.json        Experiment 5
  snapshots/exploratory_persistence_v1_20261109/...   persistence study (exploratory)
"""
import json
import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "research_paper", "PrivAgent_Figures")
EVID = os.path.join(ROOT, "research_paper", "evidence")
os.makedirs(OUT, exist_ok=True)

BLUE, ORANGE, GRAY = "#2a78d6", "#c26a0c", "#8c8b86"
INK, MUTED, GRID, SURF = "#1d1d1b", "#55544f", "#e4e3df", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})


def load(*p):
    with open(os.path.join(ROOT, *p)) as f:
        return json.load(f)


def style(ax, title=None, ylabel=None):
    if title:
        ax.set_title(title, loc="left", fontsize=10, color=INK, fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=220, facecolor=SURF, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- diagrams
def box(ax, x, y, w, h, text, fc="#f4f6fa", ec="#9aa7b8", fs=8, bold=False, tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                fc=fc, ec=ec, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#55544f", style="-|>", ls="-", lw=1.0, text=None, tx=0, ty=0,
          fs=7):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=9,
                                 color=color, lw=lw, linestyle=ls, shrinkA=1, shrinkB=1))
    if text:
        ax.text((x1 + x2) / 2 + tx, (y1 + y2) / 2 + ty, text, fontsize=fs, color=MUTED,
                ha="center", va="center")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # Agent layer
    ax.text(0.02, 0.965, "LangGraph agent pipeline (agents/graph.py)", fontsize=9, color=MUTED,
            fontweight="bold")
    agents = ["Orchestrator\n(plan)", "Retriever\n(governed MCP reads)", "Analyst\n(synthesis, LLM)",
              "Writer\n(answer, optional send)"]
    for i, a in enumerate(agents):
        box(ax, 0.02 + i * 0.245, 0.83, 0.21, 0.1, a, fc="#eef3fb", ec=BLUE, fs=8)
        if i:
            arrow(ax, 0.02 + i * 0.245 - 0.035, 0.88, 0.02 + i * 0.245, 0.88)
    box(ax, 0.02, 0.715, 0.94, 0.07,
        "HandoffTracker (agents/handoffs.py): records every agent-to-agent transfer after each node\n"
        "read-only, errors caught; SHADOW MODE (logged, never scored or enforced)",
        fc="#fbf4ea", ec=ORANGE, fs=7.5)
    # Governance layer
    ax.add_patch(FancyBboxPatch((0.02, 0.255), 0.94, 0.43, boxstyle="round,pad=0.005",
                                fc="#fafaf8", ec=GRID, lw=1))
    ax.text(0.03, 0.665, "Governance layer (governance/)", fontsize=9, color=MUTED, fontweight="bold")
    box(ax, 0.04, 0.53, 0.25, 0.1, "TrajectoryMonitor.evaluate()\nsingle interception point\n(trajectory_monitor.py)",
        fc="#eef3fb", ec=BLUE, fs=7.5, bold=True)
    box(ax, 0.33, 0.56, 0.2, 0.075, "Feature extraction\n(features.py, shared\ntrain/live)", fs=7)
    box(ax, 0.33, 0.465, 0.2, 0.075, "RiskEngine: gradient-boosted\nclassifier P(unsafe)\n(risk_engine.py)", fs=7)
    box(ax, 0.33, 0.37, 0.2, 0.075, "AutonomyController\nthresholds 0.22 / 0.50 / 0.85", fs=7)
    box(ax, 0.57, 0.56, 0.18, 0.075, "PolicyEngine\n3 deterministic rules\n(override ML)", fs=7)
    box(ax, 0.57, 0.465, 0.18, 0.075, "ProvenanceRegistry\nHMAC-fingerprinted refs\n(in memory)", fs=7)
    box(ax, 0.57, 0.37, 0.18, 0.075, "Sensitivity assessment\nprovenance-authoritative\nSHADOW MODE", fc="#fbf4ea",
        ec=ORANGE, fs=7)
    box(ax, 0.78, 0.53, 0.165, 0.1, "AuditLogger\naudit / handoff /\napproval JSONL logs", fs=7)
    box(ax, 0.78, 0.37, 0.165, 0.13,
        "ApprovalService +\nExecutionLedger\n(opt-in; approval graph\nonly) + SQLite checkpoints", fc="#fbf4ea",
        ec=ORANGE, fs=7)
    box(ax, 0.04, 0.29, 0.25, 0.065, "Decision: AUTONOMOUS | RESTRICTED\n| HUMAN_APPROVAL | BLOCKED", fs=7)
    for y in (0.597, 0.502, 0.407):
        arrow(ax, 0.29, 0.58, 0.33, y)
    ax.plot([0.2, 0.2, 0.66], [0.63, 0.65, 0.65], color="#55544f", lw=1, ls="--")
    arrow(ax, 0.66, 0.65, 0.66, 0.635, ls="--")
    arrow(ax, 0.75, 0.58, 0.78, 0.58)
    arrow(ax, 0.165, 0.53, 0.165, 0.355)
    # Tool wrappers & MCP
    box(ax, 0.02, 0.155, 0.94, 0.07,
        "Governed tool wrappers (agents/tools.py): evaluate -> call only if allowed -> register result provenance",
        fc="#eef3fb", ec=BLUE, fs=7.5)
    ax.text(0.02, 0.115, "MCP stdio servers (mcp_servers/), one client thread (agents/mcp_client.py)",
            fontsize=8, color=MUTED, fontweight="bold")
    for i, s in enumerate(["document_server\nsearch / retrieve", "database_server\nquery / list_tables",
                           "web_server\nsearch_web", "external_server\nsend_result (outbound)"]):
        box(ax, 0.02 + i * 0.245, 0.01, 0.21, 0.085, s, fc="#ffffff", ec="#9aa7b8", fs=7.5)
    arrow(ax, 0.49, 0.83, 0.49, 0.785)
    arrow(ax, 0.30, 0.83, 0.16, 0.635)
    ax.text(0.255, 0.695, "proposed tool call", fontsize=7, color=MUTED, ha="left")
    arrow(ax, 0.16, 0.29, 0.16, 0.225)
    arrow(ax, 0.49, 0.155, 0.49, 0.095)
    ax.text(0.96, 0.115, "Orange = shadow-mode or opt-in component", fontsize=7, color=ORANGE, ha="right")
    save(fig, "fig01_architecture.png")


def fig_lifecycle():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(-0.01, 1.12)
    ax.set_ylim(0, 1)
    ax.axis("off")
    lanes = ["User", "Orchestrator", "Retriever", "Analyst", "writer_\ncompose", "transmission_\ngate",
             "human_\napproval", "transmission_\nexecute", "external_\nserver"]
    xs = [0.05 + i * 0.115 for i in range(len(lanes))]
    for x, l in zip(xs, lanes):
        ext = l in ("User", "external_\nserver")
        box(ax, x - 0.05, 0.9, 0.1, 0.08, l, fc="#ffffff" if ext else "#eef3fb",
            ec="#9aa7b8" if ext else BLUE, fs=6.5)
        ax.plot([x, x], [0.08, 0.9], color=GRID, lw=1, zorder=0)
    steps = [
        (0, 1, 0.84, "task (PII regex assessed)"),
        (1, 2, 0.77, "plan  [handoff]"),
        (2, 2, 0.70, "governed MCP reads: evaluate -> call -> register refs"),
        (2, 3, 0.63, "documents, records, web  [handoff; analyst reads 10/10/5]"),
        (3, 4, 0.56, "analysis + self-reported sensitivity  [handoff]"),
        (4, 5, 0.49, "payload; state minimised to reference stubs"),
        (5, 6, 0.42, "pending action: id, keyed digests, governance context"),
        (6, 6, 0.35, "interrupt(): checkpoint (SQLite, AES-GCM), wait for reviewer"),
        (6, 7, 0.28, "approval token (or rejection = halt, no send)"),
        (7, 7, 0.21, "re-check digest + token; ledger.claim(action_id)"),
        (7, 8, 0.14, "send_result (at most one attempt per action id)"),
    ]
    for a, b, y, t in steps:
        if a == b:
            ax.plot([xs[a]], [y], marker="s", ms=7, color=ORANGE)
            ax.text(xs[a] + 0.015, y, t, fontsize=7, color=INK, va="center")
        else:
            arrow(ax, xs[a], y, xs[b], y)
            ax.text((xs[a] + xs[b]) / 2 + (0.06 if b - a == 1 else 0), y + 0.022, t, fontsize=7, color=INK,
                    ha="left" if b - a == 1 else "center", va="bottom")
    ax.text(0.02, 0.06, "Without approvals=..., the default graph runs a single writer node; HUMAN_APPROVAL then "
            "means the call is not executed (blocked).", fontsize=7, color=MUTED)
    ax.text(0.02, 0.02, "Every tool decision and handoff receives a per-run sequence number (log metadata only, "
            "never a model feature).", fontsize=7, color=MUTED)
    save(fig, "fig02_request_lifecycle.png")


def fig_decision():
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.set_xlim(-0.01, 1.0)
    ax.set_ylim(0, 1)
    ax.axis("off")
    box(ax, 0.0, 0.55, 0.15, 0.3, "Candidate action\nagent_role, tool_name,\naction_type,\ndata_sensitivity,\n"
        "destination_category", fs=7)
    box(ax, 0.0, 0.1, 0.15, 0.3, "Executed prefix\n(allowed actions\nonly, this run)", fs=7)
    box(ax, 0.2, 0.33, 0.17, 0.34, "trajectory_invariant\nfeatures (11):\n5 action features +\nmax_sensitivity,\n"
        "max_destination,\nprev_sensitive_reads,\nprev_external_transmits,\nprev_risky_actions,\nmax_prev_risk", fs=6.5)
    box(ax, 0.42, 0.45, 0.15, 0.2, "Gradient boosting\n200 trees, depth 5\n-> risk score r", fs=7)
    box(ax, 0.62, 0.45, 0.16, 0.2, "r < 0.22 AUTONOMOUS\nr < 0.50 RESTRICTED\nr < 0.85 HUMAN_APPROVAL\nelse BLOCKED",
        fs=6.5)
    box(ax, 0.42, 0.08, 0.36, 0.22, "PolicyEngine(prefix, candidate): if a rule fires,\nits decision REPLACES "
        "the ML decision\n(rules 1, 3: BLOCKED; rule 2: HUMAN_APPROVAL)", fs=6.8)
    box(ax, 0.83, 0.3, 0.16, 0.36, "Final decision\nexecuted iff\nAUTONOMOUS or\nRESTRICTED;\nlogged with source\n"
        "ml_model | policy_engine", fc="#eef3fb", ec=BLUE, fs=6.8)
    box(ax, 0.42, 0.75, 0.36, 0.2, "send_result only: provenance-authoritative label computed.\nShadow mode: "
        "the decision it WOULD give is logged\nwith mismatch flags; the enforced input is unchanged",
        fc="#fbf4ea", ec=ORANGE, fs=6.6)
    arrow(ax, 0.15, 0.7, 0.2, 0.55)
    arrow(ax, 0.15, 0.25, 0.2, 0.45)
    arrow(ax, 0.37, 0.55, 0.42, 0.55)
    arrow(ax, 0.57, 0.55, 0.62, 0.55)
    arrow(ax, 0.78, 0.55, 0.83, 0.52)
    arrow(ax, 0.78, 0.19, 0.83, 0.38)
    arrow(ax, 0.15, 0.2, 0.42, 0.19)
    arrow(ax, 0.15, 0.78, 0.42, 0.85, ls="--")
    save(fig, "fig03_decision_pipeline.png")


# ---------------------------------------------------------------- charts
def fig_eval_correction():
    s0 = json.load(open(os.path.join(EVID, "stage0_original_training_metrics.json")))["trajectory_level"]
    s1 = json.load(open(os.path.join(EVID, "stage1_corrected_eval_training_metrics.json")))["trajectory_level"]
    s2 = load("models", "training_metrics.json")["trajectory_level"]
    bars = [
        ("Stage 0\nrow-level split\ntest (legacy data)", s0["f1"], GRAY),
        ("Stage 1\nrun-level split\ntest (legacy data)", s1["test"]["f1"], GRAY),
        ("Stage 1\nheld-out attack\ntypes (legacy)", s1["holdout"]["overall"]["f1"], BLUE),
        ("Stage 2 (deployed)\nrandomized\ntest", s2["test"]["f1"], GRAY),
        ("Stage 2 (deployed)\nheld-out attack\ntypes", s2["holdout_types"]["f1"], BLUE),
        ("Stage 2 (deployed)\nheld-out tool\nvariants (B)", s2["holdout_variants"]["f1"], BLUE),
    ]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    x = range(len(bars))
    ax.bar(x, [b[1] for b in bars], color=[b[2] for b in bars], width=0.6, edgecolor="white")
    for i, b in enumerate(bars):
        ax.text(i, b[1] + 0.02, f"{b[1]:.3f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(list(x), [b[0] for b in bars], fontsize=7)
    ax.set_ylim(0, 1.12)
    ax.axvline(0.5, color=GRID, lw=0.8)
    ax.axvline(2.5, color=GRID, lw=0.8)
    style(ax, "Trajectory-model F1 at the stop threshold, by evaluation stage and set", "F1 (step level)")
    ax.text(5.4, 1.07, "gray = in-distribution test   blue = held-out", fontsize=7, color=MUTED, ha="right")
    save(fig, "fig04_evaluation_correction.png")


def fig_position():
    pa = load("experiments", "results", "position_ablation.json")["models"]
    old = pa["saved current model"]["test_by_position"]
    new = pa["randomized/trajectory_invariant"]["test_by_position"]
    bins = list(old.keys())
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.plot(range(len(bins)), [old[b]["recall"] for b in bins], "o-", color=GRAY, lw=2, ms=6)
    ax.plot(range(len(bins)), [new[b]["recall"] for b in bins], "o-", color=BLUE, lw=2, ms=6)
    ax.set_xticks(range(len(bins)), [f"steps {b}\n(n={old[b]['unsafe_steps']})" for b in bins], fontsize=7)
    ax.set_ylim(-0.05, 1.12)
    ax.text(len(bins) - 1.05, new[bins[-1]]["recall"] + 0.06, "trajectory_invariant (deployed)", color=BLUE,
            fontsize=7.5, ha="right")
    ax.text(1.15, 0.36, "Stage 1 model (all_current features)", color=GRAY, fontsize=7.5, ha="left")
    style(ax, "Unsafe-step recall by position in the run (randomized test split)", "step recall")
    ax.set_xlabel("prefix length (number of earlier executed actions)")
    save(fig, "fig05_position_recall.png")


def fig_phase3():
    r = load("experiments", "results", "phase3_flow_features.json")
    seeds = [str(s) for s in r["seeds"]]
    cands = [("baseline", GRAY, "baseline (frozen features)"), ("rich_invariant", ORANGE, "rich_invariant"),
             ("rich_invariant_no_tool", BLUE, "rich_invariant_no_tool")]
    types = list(r["per_seed"][seeds[0]]["baseline"]["loto"].keys())
    fig, ax = plt.subplots(figsize=(9, 3.4))
    w = 0.26
    for j, (c, col, lab) in enumerate(cands):
        vals = [sum(r["per_seed"][s][c]["loto"][t]["auprc"] for s in seeds) / len(seeds) for t in types]
        xs = [i + (j - 1) * w for i in range(len(types))]
        ax.bar(xs, vals, w, color=col, edgecolor="white", label=lab)
        for x_, v in zip(xs, vals):
            ax.text(x_, v + 0.015, f"{v:.2f}", ha="center", fontsize=6, color=INK)
    ax.set_xticks(range(len(types)), [t.replace("_", "\n", 1) for t in types], fontsize=7)
    ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper right")
    style(ax, "Leave-one-attack-type-out AUPRC (mean of 3 data seeds; train/validation data only)",
          "AUPRC on left-out type")
    save(fig, "fig06_phase3_loto.png")

    metrics = [("variant_c_recall", "Variant C: step recall"), ("variant_c_path_recall", "Variant C: path recall"),
               ("val_benign_run_false_alarm", "Val.: benign-run alarm rate")]
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 2.8))
    fig.subplots_adjust(wspace=0.35)
    for ax, (m, title) in zip(axes, metrics):
        vals = [r["summary"][c][m] for c, _, _ in cands]
        ax.bar(range(3), vals, color=[c[1] for c in cands], width=0.6, edgecolor="white")
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals) * 0.03, f"{v:.3f}", ha="center", fontsize=7, color=INK)
        ax.set_xticks(range(3), ["baseline", "rich", "rich\nno tool"], fontsize=7)
        ax.set_ylim(0, max(vals) * 1.25)
        style(ax, title)
        ax.title.set_fontsize(8)
    save(fig, "fig07_phase3_variantc_falsealarm.png")


def fig_approval():
    r = load("experiments", "results", "approval_evaluation.json")
    out = r["outcomes"]
    cfgs = [("current", GRAY, "Current pipeline\n(approvals off)"),
            ("approval_oracle", BLUE, "Approval,\naccurate reviewer"),
            ("approval_rubber", ORANGE, "Approval,\napprove-all reviewer")]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 2.9))
    fig.subplots_adjust(wspace=0.3)
    for ax, (key, title, ymax) in zip(axes, [("attack_transmissions_executed", "Attack sends executed (of 4)", 4),
                                              ("benign_sends_completed", "Benign sends completed (of 2)", 2)]):
        ax.set_yticks(range(ymax + 1))
        vals = [out[c][key] for c, _, _ in cfgs]
        ax.bar(range(3), vals, color=[c[1] for c in cfgs], width=0.6, edgecolor="white")
        for i, v in enumerate(vals):
            ax.text(i, v + 0.08, str(v), ha="center", fontsize=8, color=INK)
        ax.set_xticks(range(3), [c[2] for c in cfgs], fontsize=7)
        ax.set_ylim(0, ymax + 0.6)
        style(ax, title)
        ax.title.set_fontsize(8)
    save(fig, "fig08_approval_outcomes.png")


def copy_persistence():
    src = os.path.join(ROOT, "snapshots", "exploratory_persistence_v1_20261109", "files", "secure_persistence",
                       "analysis", "figures")
    # fig1_recovery_success.png is deliberately not used: CORRECTIONS.md C2 notes that it
    # conflates checkpoint recovery with execution outcome.
    for name, dst in (("fig6_component_ablation.png", "fig09_persistence_ablation_exploratory.png"),):
        shutil.copyfile(os.path.join(src, name), os.path.join(OUT, dst))


if __name__ == "__main__":
    fig_architecture()
    fig_lifecycle()
    fig_decision()
    fig_eval_correction()
    fig_position()
    fig_phase3()
    fig_approval()
    copy_persistence()
    print("figures written to", OUT)
