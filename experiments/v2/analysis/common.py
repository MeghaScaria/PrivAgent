"""
Shared statistics for the pre-registered analyses (PREREGISTRATION_v2.md).

Fixed choices, used by every script:
  bootstrap   10,000 resamples, seed 20261115, percentile 95% intervals
              (2.5th and 97.5th percentiles). The resampling unit is the
              task (a WP6 task, a WP4 scenario) or, offline, the run within
              its seed.
  McNemar     exact (binomial on the discordant pairs), two-sided.
  Wilson      95% score interval, z = 1.96, for measured costs and rates.
  DeLong      95% CI for one AUROC (DeLong et al., 1988; fast algorithm of
              Sun and Xu, 2014), normal approximation.

The scripts read result files only and write a Markdown and a JSON report.
"""
import json
import math
import os

import numpy as np

REPS = 10_000
SEED = 20261115
Z = 1.959963984540054


def rng():
    return np.random.default_rng(SEED)


def percentile_ci(values):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if not len(v):
        return [None, None]
    lo, hi = np.percentile(v, [2.5, 97.5])
    return [float(lo), float(hi)]


def wilson(k, n, z=Z):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def rate(k, n):
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None, "wilson95": wilson(k, n)}


def mcnemar_exact(pairs):
    """pairs: [(a, b)] of booleans for the same unit under conditions A and B.
    Returns the discordant counts and the exact two-sided p-value.
    a_only = A true & B false; b_only = A false & B true."""
    a_only = sum(1 for a, b in pairs if a and not b)
    b_only = sum(1 for a, b in pairs if b and not a)
    n = a_only + b_only
    if n == 0:
        p = 1.0
    else:
        k = min(a_only, b_only)
        tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
        p = min(1.0, 2 * tail)
    return {"pairs": len(pairs), "a_true": sum(1 for a, _ in pairs if a), "b_true": sum(1 for _, b in pairs if b),
            "a_only": a_only, "b_only": b_only, "discordant": n, "p_two_sided": p}


def task_bootstrap(units, statistic, reps=REPS):
    """Resamples units (e.g. task ids) with replacement; statistic(list of
    drawn units) -> float or dict of floats (NaN allowed). Returns the point
    statistic, percentile CIs and the number of NaN replicates per key."""
    r = rng()
    units = list(units)
    point = statistic(units)
    keys = list(point) if isinstance(point, dict) else None
    draws = {k: np.empty(reps) for k in keys} if keys else np.empty(reps)
    for i in range(reps):
        sample = [units[j] for j in r.integers(0, len(units), len(units))]
        s = statistic(sample)
        if keys:
            for k in keys:
                draws[k][i] = np.nan if s[k] is None else s[k]
        else:
            draws[i] = np.nan if s is None else s
    if keys:
        return {k: {"point": point[k], "ci95": percentile_ci(draws[k]),
                    "nan_replicates": int(np.isnan(draws[k]).sum())} for k in keys}
    return {"point": point, "ci95": percentile_ci(draws), "nan_replicates": int(np.isnan(draws).sum())}


def within_seed_bootstrap_diff(per_seed_pairs, reps=REPS):
    """per_seed_pairs: [(a, b)] per seed, arrays over the same runs in the
    same order. Pooled mean of (b - a) over all runs; replicates resample
    runs within each seed."""
    r = rng()
    diffs = [np.asarray(b, dtype=float) - np.asarray(a, dtype=float) for a, b in per_seed_pairs]
    diffs = [d for d in diffs if len(d)]
    total = sum(len(d) for d in diffs)
    if not total:
        return {"point": None, "ci95": [None, None], "runs": 0}
    point = float(sum(d.sum() for d in diffs) / total)
    sums = np.zeros(reps)
    for d in diffs:
        idx = r.integers(0, len(d), (reps, len(d)))
        sums += d[idx].sum(axis=1)
    return {"point": point, "ci95": percentile_ci(sums / total), "runs": int(total)}


def delong_auc(scores, labels):
    """AUROC and its DeLong 95% CI (labels 1 = positive)."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    pos, neg = s[y == 1], s[y == 0]
    m, n = len(pos), len(neg)
    if m == 0 or n == 0:
        return {"auroc": None, "ci95": [None, None], "positives": int(m), "negatives": int(n)}

    def midrank(x):
        order = np.argsort(x, kind="mergesort")
        xs = x[order]
        ranks = np.empty(len(x))
        i = 0
        while i < len(x):
            j = i
            while j < len(x) and xs[j] == xs[i]:
                j += 1
            ranks[i:j] = 0.5 * (i + j - 1) + 1
            i = j
        out = np.empty(len(x))
        out[order] = ranks
        return out
    tx, ty, tz = midrank(pos), midrank(neg), midrank(np.concatenate([pos, neg]))
    auc = (tz[:m].sum() - m * (m + 1) / 2) / (m * n)
    v01 = (tz[:m] - tx) / n
    v10 = 1 - (tz[m:] - ty) / m
    var = (np.var(v01, ddof=1) / m if m > 1 else 0.0) + (np.var(v10, ddof=1) / n if n > 1 else 0.0)
    se = math.sqrt(var) if var > 0 else 0.0
    return {"auroc": float(auc), "ci95": [float(max(0.0, auc - Z * se)), float(min(1.0, auc + Z * se))],
            "se": se, "positives": int(m), "negatives": int(n)}


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_report(stem, report, markdown):
    os.makedirs(os.path.dirname(stem) or ".", exist_ok=True)
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=float)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(markdown.rstrip() + "\n")
    print("wrote", stem + ".json and .md")


def fmt(x, digits=3):
    return "–" if x is None else f"{x:.{digits}f}"


def fmt_ci(ci, digits=3):
    return "–" if ci is None or ci[0] is None else f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"


def entirely_below_zero(ci):
    return ci is not None and ci[1] is not None and ci[1] < 0
