"""
Statistical analysis and figures for the secure-persistence experiments.

    python analysis/analyze.py                       # reads results/, writes analysis/output and analysis/figures
    python analysis/analyze.py --results results/validation --out analysis/validation

Every number in the report comes from the raw per-trial CSVs through this
script. Rates come with Wilson 95% intervals; latencies with mean,
median, standard deviation, P95 and a bootstrap 95% interval of the
median (10,000 resamples, seed 20261111). Relative overhead compares
medians with configuration A, with a bootstrap interval of the ratio.
Fisher's exact test is used only for the pre-stated leave-one-out
contrasts on binary outcomes (two-sided); Mann-Whitney U for B versus A
latency.
"""
import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.dirname(os.path.dirname(BASE)))
from configurations import CONFIGS, DESCRIPTIONS  # noqa: E402

ORDER = ["A", "B", "C", "D", "E", "F"]
RNG = np.random.default_rng(20261111)
ACCENT, NEUTRAL = "#2a78d6", "#8c8b86"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


# -- statistics --------------------------------------------------------

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def boot_median_ci(x, reps=10000):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan")
    meds = np.median(RNG.choice(x, size=(reps, len(x)), replace=True), axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def boot_ratio_ci(x, y, reps=10000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx = np.median(RNG.choice(x, size=(reps, len(x))), axis=1)
    my = np.median(RNG.choice(y, size=(reps, len(y))), axis=1)
    r = mx / my
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def describe(x):
    x = np.asarray(pd.to_numeric(pd.Series(x), errors="coerce").dropna(), float)
    if len(x) == 0:
        return {"n": 0}
    lo, hi = boot_median_ci(x)
    return {"n": len(x), "mean": x.mean(), "median": float(np.median(x)), "sd": x.std(ddof=1) if len(x) > 1 else 0.0,
            "p95": float(np.percentile(x, 95)), "median_ci_lo": lo, "median_ci_hi": hi}


def markdown(df, floatfmt=3):
    """A pipe table (no tabulate dependency)."""
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:.{floatfmt}f}"
        return str(v).replace("|", "/")
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, sep, *body])


def fisher(k1, n1, k2, n2):
    return float(stats.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])[1])


def as_bool(s):
    return s.astype(str).str.lower().isin(["true", "1", "1.0"])


# -- figures -----------------------------------------------------------

def _style(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="600")
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


SHORT = {"A": "baseline", "B": "full", "C": "−enc", "D": "−strict", "E": "−minim",
         "F": "−ledger"}


def _xlabels(configs):
    return [f"{c}\n{SHORT[c]}" for c in configs]


def rate_bars(ax, configs, rates, lo, hi, title, ylabel, pct=True, ci=True):
    x = np.arange(len(configs))
    colors = [ACCENT if c == "B" else NEUTRAL for c in configs]
    vals = np.array(rates, float) * (100 if pct else 1)
    err_lo = vals - np.array(lo, float) * (100 if pct else 1)
    err_hi = np.array(hi, float) * (100 if pct else 1) - vals
    ax.bar(x, vals, width=0.55, color=colors, edgecolor="white", linewidth=1)
    if ci:
        ax.errorbar(x, vals, yerr=[err_lo, err_hi], fmt="none", ecolor=INK, elinewidth=1, capsize=3)
    tops = vals + (err_hi if ci else 0)
    for xi, v, top in zip(x, vals, tops):
        if pct and ci and v < top - 0.5:
            # Label beside the whisker so it never collides with it
            ax.text(xi + 0.08, top + 1, f"{v:.0f}%", ha="left", va="bottom", fontsize=8, color=INK)
            continue
        ax.text(xi, top + (3 if pct else 0.02 * max(vals.max(), 1)), f"{v:.0f}%" if pct else f"{v:.1f}",
                ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, _xlabels(configs))
    if pct:
        ax.set_ylim(0, 112)
    _style(ax, title, ylabel)


def median_iqr(ax, configs, groups, title, ylabel):
    x = np.arange(len(configs))
    for xi, c in zip(x, configs):
        v = np.asarray(groups[c], float)
        v = v[~np.isnan(v)]
        if len(v) == 0:
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        col = ACCENT if c == "B" else NEUTRAL
        ax.vlines(xi, q1, q3, color=col, linewidth=6, alpha=0.9)
        ax.plot(xi, med, "o", color="white", markersize=5, markeredgecolor=INK, markeredgewidth=1)
        ax.text(xi + 0.12, med, f"{med:.2f}", va="center", fontsize=8, color=INK)
    ax.set_xticks(x, _xlabels(configs))
    _style(ax, title, ylabel)


def save(fig, out, name):
    fig.tight_layout()
    path = os.path.join(out, name)
    fig.savefig(path, dpi=200, facecolor="#fcfcfb")
    plt.close(fig)
    return path


# -- analyses ----------------------------------------------------------

def analyze(results, out, figs):
    md = []
    summary = {}

    def table(df, title, floatfmt=3):
        md.append(f"\n### {title}\n")
        md.append(markdown(df, floatfmt))
        df.to_csv(os.path.join(out, title.lower().replace(" ", "_").replace("/", "_") + ".csv"), index=False)

    def read(name):
        path = os.path.join(results, name)
        return pd.read_csv(path) if os.path.exists(path) else None

    # Experiment 1
    rec = read("recovery.csv")
    if rec is not None:
        rows = []
        for (cfg, sc), g in rec.groupby(["config", "scenario"]):
            done = g[g.status == "complete"]
            n = len(done)
            ok = as_bool(done.correct_outcome).sum()
            pend = as_bool(done.pending_recovered).sum()
            dup = as_bool(done.duplicate).sum()
            p, lo, hi = wilson(ok, n)
            rows.append({"config": cfg, "scenario": sc, "trials": len(g), "failed": len(g) - n,
                         "recovery_success": p, "ci_lo": lo, "ci_hi": hi,
                         "pending_recovered": pend / n if n else np.nan,
                         "duplicate_rate": dup / n if n else np.nan,
                         "deliveries_mean": done.delivered_total.mean(),
                         "rejected_sent_total": int(done.rejected_sent.fillna(0).sum()) if sc.startswith("R2") else "",
                         "median_recovery_s": done.recovery_s.median(),
                         "median_checkpoint_read_ms": done.checkpoint_read_s.median() * 1000})
        t = pd.DataFrame(rows)
        table(t, "Experiment 1 recovery by scenario")
        overall = []
        for cfg, g in rec.groupby("config"):
            done = g[g.status == "complete"]
            ok = as_bool(done.correct_outcome).sum()
            p, lo, hi = wilson(ok, len(done))
            pend = as_bool(done.pending_recovered).sum()
            pp, plo, phi = wilson(pend, len(done))
            dup = as_bool(done.duplicate).sum()
            dp, dlo, dhi = wilson(dup, len(done))
            overall.append({"config": cfg, "trials": len(g), "failed": len(g) - len(done),
                            "recovery_success": p, "rs_ci_lo": lo, "rs_ci_hi": hi,
                            "pending_recovery": pp, "pr_ci_lo": plo, "pr_ci_hi": phi,
                            "duplicate_rate": dp, "dup_ci_lo": dlo, "dup_ci_hi": dhi,
                            "rejected_sent": int(done[done.scenario.str.startswith("R2")].delivered_total.sum())})
        o = pd.DataFrame(overall)
        table(o, "Experiment 1 recovery overall")
        summary["recovery"] = o.to_dict("records")
        fig, ax = plt.subplots(figsize=(8, 3.6))
        oo = o.set_index("config").reindex(ORDER)
        rate_bars(ax, ORDER, oo.recovery_success, oo.rs_ci_lo, oo.rs_ci_hi,
                  "Recovery success: correct outcome after a crash (R1-R5 pooled)", "% of trials")
        save(fig, figs, "fig1_recovery_success.png")

    # Experiment 5
    led = read("ledger.csv")
    if led is not None:
        rows = []
        for (cfg, sc), g in led.groupby(["config", "scenario"]):
            done = g[g.status == "complete"]
            dup = as_bool(done.duplicate).sum()
            amo = as_bool(done.at_most_once).sum()
            p, lo, hi = wilson(amo, len(done))
            rows.append({"config": cfg, "scenario": sc, "trials": len(g), "failed": len(g) - len(done),
                         "attempted_sends": int(done.attempts.sum()), "successful_sends": int(done.delivered.sum()),
                         "duplicate_trials": int(dup), "at_most_once": p, "ci_lo": lo, "ci_hi": hi})
        if rec is not None:
            for cfg, g in rec[rec.scenario == "R5_crash_after_send"].groupby("config"):
                done = g[g.status == "complete"]
                amo = (done.delivered_total <= 1).sum()
                p, lo, hi = wilson(amo, len(done))
                rows.append({"config": cfg, "scenario": "R5_crash_after_send_then_retry (exp 1)",
                             "trials": len(g), "failed": len(g) - len(done),
                             "attempted_sends": int(done.attempts_total.sum()),
                             "successful_sends": int(done.delivered_total.sum()),
                             "duplicate_trials": int((done.delivered_total > 1).sum()),
                             "at_most_once": p, "ci_lo": lo, "ci_hi": hi})
        t = pd.DataFrame(rows).sort_values(["scenario", "config"])
        table(t, "Experiment 5 duplicate-send prevention")
        if rec is not None:
            cons = []
            for cfg, g in rec[rec.scenario.isin(["R1_pause_crash_approve", "R5_crash_after_send"])].groupby("config"):
                if not CONFIGS[cfg]["ledger"]:
                    continue
                done = g[g.status == "complete"]
                ok = ((done.scenario == "R1_pause_crash_approve") & (done.ledger_status == "executed") & (done.delivered_total == 1)) | \
                     ((done.scenario == "R5_crash_after_send") & (done.ledger_status == "executing") & (done.delivered_total == 1))
                p, lo, hi = wilson(int(ok.sum()), len(done))
                cons.append({"config": cfg, "trials": len(done), "consistent": p, "ci_lo": lo, "ci_hi": hi})
            table(pd.DataFrame(cons), "Experiment 5 ledger consistency")
        summary["ledger"] = t.to_dict("records")

    # Experiment 2
    conf = read("confidentiality.csv")
    if conf is not None:
        done = conf[conf.status == "complete"]
        rows = []
        for cfg, g in done.groupby("config"):
            rows.append({"config": cfg, "trials": len(conf[conf.config == cfg]), "failed": len(conf[conf.config == cfg]) - len(g),
                         "canaries": int(g.canaries_total.iloc[0]),
                         "pending_raw_found": g.pending_raw_total.mean(), "pending_decrypted_found": g.pending_dec_total.mean(),
                         "pending_fields_retained": g.pending_fields_count.mean(),
                         "completed_raw_found": g.completed_raw_total.mean(), "completed_rows": g.completed_rows.mean(),
                         "closed_raw_found": g.closed_raw_total.mean(),
                         "pending_blob_bytes": g.pending_blob_bytes.mean(), "pending_blob_sd": g.pending_blob_bytes.std(ddof=1),
                         "pending_file_bytes": g.pending_file_bytes.mean()})
        t = pd.DataFrame(rows)
        base_a = t.set_index("config").loc["A", "pending_blob_bytes"]
        base_e = t.set_index("config").loc["E", "pending_blob_bytes"] if "E" in set(t.config) else np.nan
        t["blob_vs_A_pct"] = (t.pending_blob_bytes / base_a - 1) * 100
        t["blob_vs_E_pct"] = (t.pending_blob_bytes / base_e - 1) * 100
        table(t, "Experiment 2 confidentiality and minimization")
        cls = []
        for cfg, g in done.groupby("config"):
            for c in ["task_email", "doc_email", "api_key", "account", "analysis", "payload_email"]:
                cls.append({"config": cfg, "class": c, "pending_raw": g[f"pending_raw_{c}"].mean(),
                            "pending_decrypted": g[f"pending_dec_{c}"].mean(),
                            "completed_raw": g[f"completed_raw_{c}"].mean(), "closed_raw": g[f"closed_raw_{c}"].mean()})
        table(pd.DataFrame(cls), "Experiment 2 exposure by canary class")
        fields = done.groupby("config").pending_fields_retained.agg(lambda s: s.mode().iloc[0] if len(s) else "")
        table(fields.reset_index(), "Experiment 2 state fields holding canaries at the pause")
        summary["confidentiality"] = t.to_dict("records")
        tt = t.set_index("config").reindex(ORDER)
        n_can = tt.canaries.max()
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
        rate_bars(axes[0], ORDER, tt.pending_raw_found / n_can, tt.pending_raw_found / n_can, tt.pending_raw_found / n_can,
                  "Canaries readable in raw store files", "% of 18 canaries", ci=False)
        rate_bars(axes[1], ORDER, tt.pending_decrypted_found / n_can, tt.pending_decrypted_found / n_can,
                  tt.pending_decrypted_found / n_can, "Canaries in decrypted checkpoint state", "", ci=False)
        save(fig, figs, "fig2_sensitive_retention.png")
        fig, ax = plt.subplots(figsize=(8, 3.4))
        sd = tt.pending_blob_sd.fillna(0)
        rate_bars(ax, ORDER, tt.pending_blob_bytes, tt.pending_blob_bytes - sd, tt.pending_blob_bytes + sd,
                  "Stored checkpoint bytes at the approval pause (mean ± SD)", "bytes", pct=False)
        save(fig, figs, "fig3_storage_size.png")

    # Experiment 3
    enc = read("encryption.csv")
    if enc is not None:
        rows = []
        for (cfg, man), g in enc[enc.manipulation != "setup"].groupby(["config", "manipulation"]):
            done = g[g.status == "complete"]
            n = len(done)
            rej = (done.outcome == "rejected").sum()
            unchanged = (done.outcome == "recovered_unchanged").sum()
            altered = (done.outcome == "recovered_altered").sum()
            p, lo, hi = wilson(rej, n)
            rows.append({"config": cfg, "manipulation": man, "trials": len(g), "failed": len(g) - n,
                         "rejected": p, "ci_lo": lo, "ci_hi": hi,
                         "loaded_unchanged": unchanged / n if n else np.nan, "loaded_altered": altered / n if n else np.nan,
                         "trials_with_send": int((done.delivered > 0).sum()),
                         "top_error": done.error_type.mode().iloc[0] if done.error_type.notna().any() else ""})
        t = pd.DataFrame(rows)
        table(t, "Experiment 3 tamper detection")
        lat = read("encryption_latency.csv")
        if lat is not None:
            lr = []
            for cfg, g in lat.groupby("config"):
                e, d = describe(g.encrypt_us), describe(g.decrypt_us)
                lr.append({"config": cfg, "plaintext_bytes_mean": g.plaintext_bytes.mean(),
                           "encrypt_us_median": e["median"], "encrypt_us_p95": e["p95"],
                           "decrypt_us_median": d["median"], "decrypt_us_p95": d["p95"]})
            table(pd.DataFrame(lr), "Experiment 3 AES-GCM latency")
        summary["encryption"] = t.to_dict("records")

    # Experiment 4
    ds = read("deserialization_store.csv")
    if ds is not None:
        rows = []
        for (cfg, att), g in ds.groupby(["config", "attacker"]):
            done = g[g.status == "complete"]
            k = as_bool(done.probe_constructed).sum()
            p, lo, hi = wilson(k, len(done))
            rows.append({"config": cfg, "attacker": att, "trials": len(g), "failed": len(g) - len(done),
                         "probe_constructed": p, "ci_lo": lo, "ci_hi": hi,
                         "load_raised": (done.error_type.fillna("") != "").mean(),
                         "final_output_type": done.final_output_type.mode().iloc[0] if done.final_output_type.notna().any() else ""})
        table(pd.DataFrame(rows), "Experiment 4 store-level probe injection")
        summary["deserialization"] = rows
    dsr = read("deserialization_serde.csv")
    if dsr is not None:
        rows = []
        for (case, mode), g in dsr.groupby(["case", "mode"]):
            done = g[g.status == "complete"]
            rows.append({"case": case, "mode": mode, "trials": len(g), "failed": len(g) - len(done),
                         "serializable": as_bool(done.dumped).mean(), "loaded": as_bool(done.loaded).mean(),
                         "round_trip_equal": as_bool(done.equal).mean(),
                         "constructed": as_bool(done.constructed).mean() if done.constructed.notna().any() else "",
                         "loaded_type": done.loaded_type.mode().iloc[0] if done.loaded_type.notna().any() else ""})
        table(pd.DataFrame(rows), "Experiment 4 serializer behaviour")

    # Experiment 6
    perf = read("performance.csv")
    if perf is not None:
        p = perf[(perf.status == "complete") & (~as_bool(perf.warmup))]
        metrics = {"workflow_s": ("Workflow (pause + approve)", 1000, "ms"),
                   "to_pause_s": ("Run to pause", 1000, "ms"), "approve_s": ("Approve to completion", 1000, "ms"),
                   "write_mean_ms": ("Checkpoint write", 1, "ms"), "read_mean_ms": ("Checkpoint read", 1, "ms"),
                   "recovery_read_ms": ("Recovery: checkpoint read", 1, "ms"),
                   "recovery_total_ms": ("Recovery: open + build + read", 1, "ms"),
                   "cpu_s": ("CPU time per run", 1000, "ms"), "pause_blob_bytes": ("Stored blob bytes", 1, "B"),
                   "pause_file_bytes": ("DB + WAL + SHM bytes", 1, "B")}
        rows = []
        base = p[p.config == "A"]
        for metric, (label, scale, unit) in metrics.items():
            for cfg in ORDER:
                g = p[p.config == cfg][metric] * scale
                d = describe(g)
                if d["n"] == 0:
                    continue
                b = base[metric].dropna() * scale
                lo, hi = boot_ratio_ci(g.dropna(), b) if len(b) else (np.nan, np.nan)
                rows.append({"metric": label, "unit": unit, "config": cfg, "n": d["n"], "mean": d["mean"],
                             "median": d["median"], "sd": d["sd"], "p95": d["p95"],
                             "median_ci_lo": d["median_ci_lo"], "median_ci_hi": d["median_ci_hi"],
                             "overhead_vs_A_pct": (d["median"] / np.median(b) - 1) * 100 if len(b) else np.nan,
                             "ratio_ci_lo": lo, "ratio_ci_hi": hi})
        t = pd.DataFrame(rows)
        table(t, "Experiment 6 performance", floatfmt=3)
        mem = read("performance_memory.csv")
        if mem is not None:
            mr = [{"config": c, **{k: v for k, v in describe(g.peak_traced_mb).items() if k in ("n", "mean", "median", "sd")}}
                  for c, g in mem[mem.status == "complete"].groupby("config")]
            table(pd.DataFrame(mr), "Experiment 6 peak traced memory MB")
        failed = perf[perf.status != "complete"]
        md.append(f"\nPerformance runs failed: {len(failed)} of {len(perf)} (warm-ups included).")
        bw = p[p.config.isin(["A", "B"])]
        u = stats.mannwhitneyu(bw[bw.config == "B"].workflow_s, bw[bw.config == "A"].workflow_s, alternative="two-sided")
        md.append(f"\nMann-Whitney U, workflow time B vs A: U = {u.statistic:.0f}, p = {u.pvalue:.3g}.")
        summary["performance"] = t.to_dict("records")
        groups = lambda m, s: {c: (p[p.config == c][m] * s).values for c in ORDER}  # noqa: E731
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
        median_iqr(axes[0], ORDER, groups("write_mean_ms", 1), "Checkpoint write (per call)", "ms (median, IQR)")
        median_iqr(axes[1], ORDER, groups("read_mean_ms", 1), "Checkpoint read (per call)", "ms (median, IQR)")
        save(fig, figs, "fig4_write_read_latency.png")
        ov = t[t.metric == "Workflow (pause + approve)"].set_index("config").reindex(ORDER)
        fig, ax = plt.subplots(figsize=(8, 3.6))
        x = np.arange(len(ORDER))
        vals = ov.overhead_vs_A_pct.values
        lo = (ov.ratio_ci_lo.values - 1) * 100
        hi = (ov.ratio_ci_hi.values - 1) * 100
        ax.axhline(0, color=MUTED, linewidth=0.8)
        for xi, c, v, l, h in zip(x, ORDER, vals, lo, hi):
            col = ACCENT if c == "B" else NEUTRAL
            ax.vlines(xi, l, h, color=col, linewidth=2)
            ax.plot(xi, v, "o", color=col, markersize=7)
            ax.text(xi + 0.12, v, f"{v:+.0f}%", va="center", fontsize=8, color=INK)
        ax.set_xticks(x, _xlabels(ORDER))
        _style(ax, "Workflow latency relative to baseline A (median, bootstrap 95% CI)", "% vs A")
        save(fig, figs, "fig5_runtime_overhead.png")

    # Component-level ablation (fig 6)
    panels = []
    if rec is not None:
        r5 = rec[(rec.scenario == "R5_crash_after_send") & (rec.status == "complete")]
        panels.append(("Ledger: duplicate sends after\ncrash + retry (R5)", "F",
                       {c: wilson(int(as_bool(r5[r5.config == c].duplicate).sum()), len(r5[r5.config == c])) for c in ("B", "F")},
                       True))
    if conf is not None:
        d = conf[conf.status == "complete"]
        panels.append(("Encryption: canaries in raw\nstore bytes", "C",
                       {c: (d[d.config == c].pending_raw_total.mean() / 18,) * 3 for c in ("B", "C")}, False))
        panels.append(("Minimization: canaries in\ndecrypted state", "E",
                       {c: (d[d.config == c].pending_dec_total.mean() / 18,) * 3 for c in ("B", "E")}, False))
    if ds is not None:
        kh = ds[(ds.attacker == "key_holder") & (ds.status == "complete")]
        panels.append(("Strict decoding: probe built\n(key-holding attacker)", "D",
                       {c: wilson(int(as_bool(kh[kh.config == c].probe_constructed).sum()), len(kh[kh.config == c])) for c in ("B", "D")},
                       True))
    if panels:
        fig, axes = plt.subplots(1, len(panels), figsize=(3 * len(panels), 3.4), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, (title, other, vals, ci) in zip(axes, panels):
            cfgs = ["B", other]
            rate_bars(ax, cfgs, [vals[c][0] for c in cfgs], [vals[c][1] for c in cfgs], [vals[c][2] for c in cfgs],
                      title, "%" if ax is axes[0] else "", ci=ci)
            ax.title.set_fontsize(9)
        save(fig, figs, "fig6_component_ablation.png")

    # Leave-one-out Fisher tests on binary outcomes
    tests = []
    if rec is not None:
        r5 = rec[(rec.scenario == "R5_crash_after_send") & (rec.status == "complete")]
        for other in ("F", "A"):
            b, o = r5[r5.config == "B"], r5[r5.config == other]
            tests.append({"contrast": f"duplicate after crash+retry, B vs {other}",
                          "B": f"{int(as_bool(b.duplicate).sum())}/{len(b)}",
                          other: f"{int(as_bool(o.duplicate).sum())}/{len(o)}",
                          "fisher_p": fisher(int(as_bool(b.duplicate).sum()), len(b), int(as_bool(o.duplicate).sum()), len(o))})
    if led is not None:
        dc = led[(led.scenario == "L3_double_click") & (led.status == "complete")]
        b, f = dc[dc.config == "B"], dc[dc.config == "F"]
        tests.append({"contrast": "duplicate on double-click, B vs F", "B": f"{int(as_bool(b.duplicate).sum())}/{len(b)}",
                      "F": f"{int(as_bool(f.duplicate).sum())}/{len(f)}",
                      "fisher_p": fisher(int(as_bool(b.duplicate).sum()), len(b), int(as_bool(f.duplicate).sum()), len(f))})
    if ds is not None:
        kh = ds[(ds.attacker == "key_holder") & (ds.status == "complete")]
        b, d = kh[kh.config == "B"], kh[kh.config == "D"]
        tests.append({"contrast": "probe constructed (key holder), B vs D", "B": f"{int(as_bool(b.probe_constructed).sum())}/{len(b)}",
                      "D": f"{int(as_bool(d.probe_constructed).sum())}/{len(d)}",
                      "fisher_p": fisher(int(as_bool(b.probe_constructed).sum()), len(b), int(as_bool(d.probe_constructed).sum()), len(d))})
    if tests:
        table(pd.DataFrame(tests), "Leave-one-out Fisher exact tests", floatfmt=3)

    with open(os.path.join(out, "tables.md"), "w", encoding="utf-8") as f:
        f.write("# Analysis tables (generated by analysis/analyze.py)\n" + "\n".join(md) + "\n")
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default=os.path.join(BASE, "results"))
    p.add_argument("--out", default=os.path.join(HERE, "output"))
    args = p.parse_args()
    figs = os.path.join(os.path.dirname(args.out), "figures") if args.out.endswith("output") else os.path.join(args.out, "figures")
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(figs, exist_ok=True)
    analyze(args.results, args.out, figs)
    print(f"tables: {args.out}\nfigures: {figs}")


if __name__ == "__main__":
    main()
