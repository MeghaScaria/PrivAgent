"""
Figures for the PrivAgent v2 paper, from committed confirmatory result files only.

Inputs (read only):
  experiments/v2/results/confirmatory/analysis/h1.json, h4.json, h5.json
  experiments/v2/results/confirmatory/multiseed_confirmatory.json
Outputs (this directory): v2_f1_h5_asr.png, v2_f2_benign_utility.png,
  v2_f3_h1_live_costs.png, v2_f4_h4a_recall.png, v2_f5_multiseed_heldout.png
  (each also as .svg).

All intervals are Wilson 95% intervals taken from the result files.

    python research_paper/v2/figures/make_figures_v2.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CONF = os.path.join(ROOT, "experiments", "v2", "results", "confirmatory")

INK, MUTED, GRID = "#1f2328", "#59636e", "#d8dee4"
BASE, EMPH = "#8fa3b8", "#1f5fa8"            # neutral series; highlighted series (v2)
PAIR = ("#1f5fa8", "#d9822b")                # two-category pair (blue / orange)
CONFIGS = ["no_governance", "rules_only", "ml_only", "v1", "v2", "v2_reviewer"]

plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 200, "savefig.bbox": "tight", "font.family": "DejaVu Sans"})


def load(name):
    with open(os.path.join(CONF, name), encoding="utf-8") as f:
        return json.load(f)


def err(rates):
    """Asymmetric error bars from Wilson intervals: rates = [(rate, (lo, hi)), ...]."""
    # clamped at 0: a stored Wilson bound can sit a rounding error inside a rate of exactly 0 or 1
    return [[max(0.0, r - lo) for r, (lo, hi) in rates], [max(0.0, hi - r) for r, (lo, hi) in rates]]


def finish(fig, ax, name, ylabel=None):
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(HERE, f"{name}.{ext}"))
    plt.close(fig)
    print("wrote", name)


def rate_bars(ax, labels, cells, highlight=None):
    rates = [(c["rate"], c["wilson95"]) for c in cells]
    colors = [EMPH if lab == highlight else BASE for lab in labels]
    ax.bar(labels, [r for r, _ in rates], color=colors, width=0.62, yerr=err(rates),
           error_kw={"ecolor": INK, "elinewidth": 0.9, "capsize": 3})
    for i, c in enumerate(cells):
        ax.text(i, c["wilson95"][1] + 0.02, f"{c['k']}/{c['n']}", ha="center", va="bottom", color=MUTED, fontsize=8)
    ax.set_ylim(0, 1.1)
    ax.tick_params(axis="x", rotation=20)


def f1_h5(h5):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    rate_bars(ax, CONFIGS, [h5["family_B_per_config"][c]["asr"] for c in CONFIGS], highlight="v2")
    ax.set_title("Family B attack success per configuration (qwen2.5:3b)", loc="left", color=INK)
    finish(fig, ax, "v2_f1_h5_asr", "Attack success rate (Wilson 95%)")


def f2_utility(h5):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    rate_bars(ax, CONFIGS, [h5["benign_utility"][c]["benign_success"] for c in CONFIGS], highlight="v2")
    ax.set_title("Benign task success per configuration (40 tasks, qwen2.5:3b)", loc="left", color=INK)
    finish(fig, ax, "v2_f2_benign_utility", "Benign success (Wilson 95%)")


def f3_h1(h1):
    costs = h1["live"]["costs"]["accurate"]
    arms = ["first_fire_v1", "max_severity", "max_severity_reviewable"]
    measures = [("ext_hard_block", "Benign sends hard-blocked"), ("approval", "Benign approval volume")]

    def cell(arm, m):
        if arm == "first_fire_v1":
            return costs["max_severity"][m]["first_fire_v1"]
        return costs[arm][m]["arm"]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    w = 0.36
    for j, (m, label) in enumerate(measures):
        cells = [cell(a, m) for a in arms]
        xs = [i + (j - 0.5) * w for i in range(len(arms))]
        rates = [(c["rate"], c["wilson95"]) for c in cells]
        ax.bar(xs, [r for r, _ in rates], width=w - 0.04, color=PAIR[j], label=label, yerr=err(rates),
               error_kw={"ecolor": INK, "elinewidth": 0.9, "capsize": 3})
        for x, c in zip(xs, cells):
            ax.text(x, c["wilson95"][1] + 0.02, f"{c['k']}/{c['n']}", ha="center", va="bottom", color=MUTED, fontsize=8)
    ax.set_xticks(range(len(arms)), arms)
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    ax.set_title("H1 live costs per precedence arm (WP4, benign, accurate declaration)", loc="left", color=INK)
    finish(fig, ax, "v2_f3_h1_live_costs", "Share of benign runs (Wilson 95%)")


def f4_h4(h4):
    rc = h4["a"]["recall_counts"]
    fig, ax = plt.subplots(figsize=(4, 3.2))
    rate_bars(ax, ["Path-dependent\n(handoff)", "Direct\n(external send)"], [rc["path"], rc["direct"]])
    ax.tick_params(axis="x", rotation=0)
    ax.set_title("H4(a): frozen-model step recall, v2 traces", loc="left", color=INK)
    finish(fig, ax, "v2_f4_h4a_recall", "Step recall (Wilson 95%)")


def f5_multiseed(ms):
    rows = []
    for s, tag in (("holdout_types", "held-out type"), ("holdout_variants", "variant B")):
        for t, x in ms["per_set"][s]["per_attack_type"].items():
            rows.append((f"{t}\n({tag})", {"rate": x["rate"], "wilson95": x["wilson95"],
                                          "k": x["runs_caught"], "n": x["runs"]}))
    rows.sort(key=lambda r: r[1]["rate"])
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ys = range(len(rows))
    rates = [(c["rate"], c["wilson95"]) for _, c in rows]
    colors = [EMPH if lab.startswith("path_") else BASE for lab, _ in rows]
    ax.barh(list(ys), [r for r, _ in rates], color=colors, height=0.62, xerr=err(rates),
            error_kw={"ecolor": INK, "elinewidth": 0.9, "capsize": 3})
    for y, (_, c) in zip(ys, rows):
        ax.text(min(c["wilson95"][1] + 0.02, 1.02), y, f"{c['k']}/{c['n']}", va="center", color=MUTED, fontsize=8)
    ax.set_yticks(list(ys), [lab for lab, _ in rows], fontsize=8)
    ax.set_xlim(0, 1.2)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Runs caught, pooled over 10 seeds (Wilson 95%)")
    ax.set_title("Held-out attack types and variants: run-level recall by type", loc="left", color=INK)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(HERE, f"v2_f5_multiseed_heldout.{ext}"))
    plt.close(fig)
    print("wrote v2_f5_multiseed_heldout")


def main():
    plt.rcParams["svg.hashsalt"] = "privagent-v2"   # deterministic SVG ids
    h1, h4, h5 = load("analysis/h1.json"), load("analysis/h4.json"), load("analysis/h5.json")
    f1_h5(h5)
    f2_utility(h5)
    f3_h1(h1)
    f4_h4(h4)
    f5_multiseed(load("multiseed_confirmatory.json"))


if __name__ == "__main__":
    main()
