"""
Independent audit of the exploratory secure-persistence results.

Recomputes every number stated in REPORT.md directly from the raw
per-trial CSVs in the frozen copy of the study, without importing
analysis/analyze.py, and compares each with the stated value.

    python audit/recompute.py            # reads the frozen copy, writes audit/output/

Independence from analyze.py:
- Wilson intervals are computed here from the formula AND cross-checked
  against scipy.stats.binomtest(...).proportion_ci(method="wilson").
- Outcome classifications are re-derived from the primitive columns
  (paused, pending_recovered, delivered counts, ...), not read from the
  derived correct_outcome / at_most_once columns, and then compared with
  those columns.
- Bootstrap intervals use a different generator and scipy.stats.bootstrap
  (percentile method, 10,000 resamples, seed 7). They are Monte Carlo
  estimates, so agreement with the report is judged with a tolerance.

Nothing in the frozen copy or in results/ is written to.
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FROZEN = os.path.join(PROJECT, "snapshots", "exploratory_persistence_v1_20261109", "files",
                      "secure_persistence")
RES = os.path.join(FROZEN, "results")
TAB = os.path.join(FROZEN, "analysis", "output")
OUT = os.path.join(HERE, "output")
ORDER = list("ABCDEF")
ENC = {"A": False, "B": True, "C": False, "D": True, "E": True, "F": True}
LEDGER = {"A": False, "B": True, "C": True, "D": True, "E": True, "F": False}

checks = []   # every comparison: id, section, claim, stated, recomputed, status, note


def check(cid, section, claim, stated, recomputed, ok, note=""):
    checks.append({"id": cid, "section": section, "claim": claim, "stated": str(stated),
                   "recomputed": str(recomputed), "status": "MATCH" if ok else "MISMATCH", "note": note})


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def b(s):
    return s.astype(str).str.lower().isin(["true", "1", "1.0"])


def wilson(k, n, z=1.959963984540054):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    lo, hi = max(0.0, c - h), min(1.0, c + h)
    ci = stats.binomtest(int(k), int(n)).proportion_ci(confidence_level=0.95, method="wilson")
    assert abs(ci.low - lo) < 1e-9 and abs(ci.high - hi) < 1e-9, (k, n, lo, hi, ci)
    return p, lo, hi


def pct(x):
    return round(100 * x, 1)


def boot_median(x, seed=7):
    x = np.asarray(x, float)
    r = stats.bootstrap((x,), np.median, n_resamples=10000, method="percentile",
                        random_state=np.random.default_rng(seed))
    return r.confidence_interval.low, r.confidence_interval.high


def boot_ratio(x, y, seed=7, reps=10000):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx = np.median(rng.choice(x, (reps, len(x))), axis=1)
    my = np.median(rng.choice(y, (reps, len(y))), axis=1)
    return np.percentile(mx / my, [2.5, 97.5])


def read(name):
    return pd.read_csv(os.path.join(RES, name))


def main():
    os.makedirs(OUT, exist_ok=True)
    facts = {}

    # ------------------------------------------------------------------
    # 0. Row counts, failures, seeds, independence of units
    files = ["recovery", "ledger", "confidentiality", "encryption", "encryption_latency",
             "deserialization_store", "deserialization_serde", "performance", "performance_memory"]
    data = {f: read(f + ".csv") for f in files}
    rows = {f: len(d) for f, d in data.items()}
    total = sum(rows.values())
    failed = {f: int((d.status != "complete").sum()) for f, d in data.items() if "status" in d}
    facts["rows"] = rows
    facts["failed"] = failed
    check("0.1", "header", "total rows in 9 CSV files", 5070, total, total == 5070)
    check("0.2", "header", "failed rows", 0, sum(failed.values()), sum(failed.values()) == 0)

    enc = data["encryption"]
    perf = data["performance"]
    serde = data["deserialization_serde"]
    units = {
        "recovery: independent trials (own store, own seed, separate processes)": data["recovery"].seed.nunique(),
        "ledger: independent trials": data["ledger"].seed.nunique(),
        "confidentiality: independent trials (3 phases per row)": data["confidentiality"].seed.nunique(),
        "encryption: independent paused runs (each yields 7 manipulation rows on copies of one store)": enc.seed.nunique(),
        "encryption_latency: per-run summaries of 200 timing repetitions (same runs as encryption)": 0,
        "deserialization_store: independent trials": data["deserialization_store"].seed.nunique(),
        "deserialization_serde compatibility: independent paused runs (2 decoder modes per run)":
            serde[serde.case.str.startswith("checkpoint_state")].groupby(["case", "trial"]).ngroups,
        "deserialization_serde other cases: 30 repetitions of 22 deterministic computations":
            int((~serde.case.str.startswith("checkpoint_state")).sum()),
        "performance: measured runs (warm-ups excluded)": int((~b(perf.warmup)).sum()),
        "performance: warm-up runs (excluded from analysis)": int(b(perf.warmup).sum()),
        "performance_memory: independent runs": len(data["performance_memory"]),
    }
    facts["units"] = units
    det = units["deserialization_serde other cases: 30 repetitions of 22 deterministic computations"]
    indep = (units["recovery: independent trials (own store, own seed, separate processes)"]
             + units["ledger: independent trials"]
             + units["confidentiality: independent trials (3 phases per row)"]
             + units["encryption: independent paused runs (each yields 7 manipulation rows on copies of one store)"]
             + units["deserialization_store: independent trials"]
             + units["deserialization_serde compatibility: independent paused runs (2 decoder modes per run)"]
             + units["performance: measured runs (warm-ups excluded)"]
             + units["performance_memory: independent runs"])
    facts["independent_units"] = indep
    facts["deterministic_repetitions"] = det
    check("0.3", "header", "'5,070 trials' are independent experimental trials", "5,070 trials",
          f"{indep} independent runs + {det} repeated deterministic serializer computations + "
          f"{units['performance: warm-up runs (excluded from analysis)']} warm-ups; the rest are "
          f"derived rows (7 manipulations per encryption run, 2 decoder modes per compatibility run, "
          f"180 latency summaries)", False,
          "Rows are not trials. See EXPLORATORY_AUDIT.md section 2.")
    # Is R5 in the Exp 5 table a separate sample? (it is the same 180 Exp 1 trials)
    facts["r5_reused_in_exp5"] = True

    # ------------------------------------------------------------------
    # 1. Recovery
    rec = data["recovery"].copy()
    rec["rej_sent"] = pd.to_numeric(rec.rejected_sent, errors="coerce").fillna(0)
    derived = (b(rec.paused) & b(rec.pending_recovered) & b(rec.payload_matches)
               & (rec.delivered_total == rec.expected_deliveries) & (rec.rej_sent == 0))
    check("1.0", "B1", "correct_outcome column equals re-derived criterion", "column",
          f"{int((derived == b(rec.correct_outcome)).sum())}/900 agree",
          bool((derived == b(rec.correct_outcome)).all()))
    rec["correct"] = derived
    stated_scn = {("A", "R5_crash_after_send"): 0, ("F", "R5_crash_after_send"): 0}
    allok = True
    for (cfg, sc), g in rec.groupby(["config", "scenario"]):
        k = int(g.correct.sum())
        exp = stated_scn.get((cfg, sc), 30)
        allok &= (k == exp and len(g) == 30)
    check("1.1", "B1", "per-scenario correct outcomes (30/30 except A,F R5 = 0/30)", "table", "recomputed", allok)
    for cfg in ORDER:
        g = rec[rec.config == cfg]
        k, n = int(g.correct.sum()), len(g)
        p, lo, hi = wilson(k, n)
        stated = (120, 72.9, 85.6) if cfg in "AF" else (150, 97.5, 100.0)
        check(f"1.2{cfg}", "B1", f"pooled correct outcome {cfg}", f"{stated[0]}/150 [{stated[1]}, {stated[2]}]",
              f"{k}/{n} [{pct(lo)}, {pct(hi)}]",
              k == stated[0] and pct(lo) == stated[1] and pct(hi) == stated[2])
        dup = int((g.delivered_total > g.expected_deliveries).sum())
        dp, dlo, dhi = wilson(dup, n)
        sd = (30, 14.4, 27.1) if cfg in "AF" else (0, 0.0, 2.5)
        check(f"1.3{cfg}", "B1", f"pooled duplicate delivery {cfg}", f"{sd[0]}/150 [{sd[1]}, {sd[2]}]",
              f"{dup}/{n} [{pct(dlo)}, {pct(dhi)}]",
              dup == sd[0] and pct(dlo) == sd[1] and pct(dhi) == sd[2])
        pend = int(b(g.pending_recovered).sum())
        check(f"1.4{cfg}", "B1", f"pending request recovered {cfg}", "150/150", f"{pend}/{n}", pend == 150)
    r2 = rec[rec.scenario == "R2_pause_crash_reject"]
    check("1.5", "B1/D1", "rejected action never sent (R2)", "0/180",
          f"{int((r2.delivered_total > 0).sum())}/{len(r2)}", int((r2.delivered_total > 0).sum()) == 0)
    r5 = rec[rec.scenario == "R5_crash_after_send"]
    st = r5[r5.config.isin(list("BCDE"))].ledger_status.value_counts().to_dict()
    check("1.6", "B1", "R5 ledger stays 'executing' in B-E", "30/30 each (120)", st, st == {"executing": 120})
    for sc in ["R1_pause_crash_approve", "R2_pause_crash_reject"]:
        g = rec[rec.scenario == sc]
        h = g.again_helper.value_counts().to_dict()
        r = g.again_raw.value_counts().to_dict()
        check(f"1.7{sc[:2]}", "B1", f"{sc[:2]} second resume: helper no_pending, raw RuntimeError", "180/180",
              f"{h}; {r}", h == {"no_pending_approval": 180} and r == {"raised RuntimeError": 180})
    med = rec.groupby(["config", "scenario"]).recovery_s.median()
    check("1.8", "B1", "median recovery 4.3-4.9 s", "4.3-4.9 s",
          f"{med.min():.3f}-{med.max():.3f} s", round(med.min(), 1) >= 4.3 and round(med.max(), 1) <= 4.9)
    rd = rec.groupby(["config", "scenario"]).checkpoint_read_s.median() * 1000
    un = rd[[c in "AC" for c, _ in rd.index]]
    en = rd[[c not in "AC" for c, _ in rd.index]]
    check("1.9", "B1", "checkpoint read 2.3 ms unenc, 4.9-5.6 ms enc", "2.3 / 4.9-5.6 ms",
          f"{un.min():.2f}-{un.max():.2f} / {en.min():.2f}-{en.max():.2f} ms",
          round(un.min(), 1) >= 2.2 and round(un.max(), 1) <= 2.4 and round(en.min(), 1) >= 4.9 and round(en.max(), 1) <= 5.6,
          "unencrypted range is 2.28-2.36 ms; '2.3' is a rounded summary")
    # R4: approval not persisted, re-approval needed
    r4 = rec[rec.scenario.isin(["R4_crash_after_approval", "R5_crash_after_send"])]
    reappr = int((r4.second_review_approval == "approved").sum())
    check("1.10", "D1", "R4/R5 approval had to be given again in all trials", "all", f"{reappr}/{len(r4)}",
          reappr == len(r4))
    # Checkpoint recovery vs execution recovery
    exe = {}
    for cfg in ORDER:
        g = rec[(rec.config == cfg) & rec.scenario.isin(["R1_pause_crash_approve", "R3_crash_before_approval",
                                                           "R4_crash_after_approval", "R5_crash_after_send"])]
        known = (g.delivered_total == 1) & ((g.ledger_status == "executed") if LEDGER[cfg] else True)
        exe[cfg] = {"checkpoint_recovered": int(b(g.pending_recovered).sum()), "approve_trials": len(g),
                    "exactly_one_delivery": int((g.delivered_total == 1).sum()),
                    "completion_recorded_in_ledger": int((g.ledger_status == "executed").sum()) if LEDGER[cfg] else None,
                    "stuck_executing": int((g.ledger_status == "executing").sum()) if LEDGER[cfg] else None}
    facts["execution_recovery"] = exe

    # ------------------------------------------------------------------
    # 2. Ledger
    led = data["ledger"]
    led_amo = (led.delivered <= 1)
    check("2.0", "B5", "at_most_once column equals delivered<=1", "column",
          f"{int((led_amo == b(led.at_most_once)).sum())}/900", bool((led_amo == b(led.at_most_once)).all()))
    stated = {("A", "L3_double_click"): 5, ("F", "L3_double_click"): 0}
    ok = True
    for (cfg, sc), g in led.groupby(["config", "scenario"]):
        exp = stated.get((cfg, sc), 30)
        ok &= int((g.delivered <= (0 if sc == "L5_reject" else 1)).sum()) == exp
    check("2.1", "B5", "per-scenario at-most-once (30/30 except A L3 5/30, F L3 0/30)", "table", "recomputed", ok)
    l3a = led[(led.config == "A") & (led.scenario == "L3_double_click")]
    check("2.2", "D5", "A L3 duplicates", "25/30", f"{int((l3a.delivered > 1).sum())}/30",
          int((l3a.delivered > 1).sum()) == 25)
    anomalies = []
    for f, cols in [("ledger", ("attempts", "delivered")), ("recovery", ("attempts_total", "delivered_total"))]:
        d = data[f]
        bad = d[d[cols[0]] != d[cols[1]]]
        for _, r in bad.iterrows():
            anomalies.append({"file": f, "config": r.config, "scenario": r.scenario, "trial": int(r.trial),
                              "seed": r.seed, "attempts": int(r[cols[0]]), "delivered": int(r[cols[1]])})
    facts["log_anomalies"] = anomalies
    check("2.3", "D5", "transmission-log anomaly: one A L3 trial with 1 attempt / 2 deliveries", "1 trial",
          anomalies, len(anomalies) == 1 and anomalies[0]["attempts"] == 1 and anomalies[0]["delivered"] == 2)
    # Ledger consistency as defined by analyze.py
    cons = rec[rec.scenario.isin(["R1_pause_crash_approve", "R5_crash_after_send"]) & rec.config.isin(list("BCDE"))]
    exec_and_recorded = int(((cons.ledger_status == "executed") & (cons.delivered_total == 1)).sum())
    check("2.4", "B5", "ledger state 'matched the deliveries' in 60/60 per config (B-E)", "60/60 each",
          f"R1: executed & delivered 120/120; R5: 'executing' & delivered 120/120. Ledger records the delivery in "
          f"{exec_and_recorded}/240", False,
          "Counts are right, but in R5 the ledger does not record the delivery; 'consistent with the crash point' "
          "is accurate, 'matched the deliveries' is not. See CORRECTIONS.md C4.")

    # ------------------------------------------------------------------
    # 3. Confidentiality
    conf = data["confidentiality"]
    stated_conf = {"A": (18, 18, 18, 18), "B": (0, 2, 0, 0), "C": (2, 2, 2, 2), "D": (0, 2, 0, 0),
                   "E": (0, 18, 0, 0), "F": (0, 2, 0, 0)}
    for cfg, g in conf.groupby("config"):
        vals = []
        for col in ["pending_raw_total", "pending_dec_total", "completed_raw_total", "closed_raw_total"]:
            vals.append((int(g[col].min()), int(g[col].max())))
        ok = all(lo == hi == s for (lo, hi), s in zip(vals, stated_conf[cfg]))
        check(f"3.1{cfg}", "B2", f"canary counts {cfg} (raw pause, dec pause, raw completed, raw closed)",
              stated_conf[cfg], vals, ok, "min=max across all 30 trials" if ok else "")
    blob = conf.groupby("config").pending_blob_bytes.agg(["mean", lambda s: s.std(ddof=1)])
    blob.columns = ["mean", "sd"]
    stated_blob = {"A": (9327, 13), "B": (8496, 11), "C": (8439, 12), "D": (8497, 14), "E": (9389, 16), "F": (8497, 13)}
    for cfg in ORDER:
        m, s = blob.loc[cfg]
        check(f"3.2{cfg}", "B2", f"blob bytes mean±SD {cfg}", f"{stated_blob[cfg][0]} ± {stated_blob[cfg][1]}",
              f"{m:.1f} ± {s:.1f}", round(m) == stated_blob[cfg][0] and round(s) == stated_blob[cfg][1])
    fb = conf.pending_file_bytes.unique().tolist()
    check("3.3", "B2", "file bytes 86,336 in every trial", 86336, fb, fb == [86336])
    a_c = (blob.loc["C", "mean"] / blob.loc["A", "mean"] - 1) * 100
    e_b = (blob.loc["B", "mean"] / blob.loc["E", "mean"] - 1) * 100
    check("3.4", "D2", "minimization reduced blob bytes ~9% (A to C: -9.5%)", "-9.5% (A->C)",
          f"A->C {a_c:.2f}%; E->B {e_b:.2f}%", round(a_c, 1) == -9.5,
          "Number correct, but A->C also changes M2 and M4; E->B (-9.5%) isolates M3. See CORRECTIONS.md C6.")
    cb = blob.loc["B", "mean"] - blob.loc["C", "mean"]
    check("3.5", "D2", "encryption adds ~57 bytes per checkpoint (C to B)", "57 B per checkpoint",
          f"{cb:.1f} B per paused thread (sum over all stored blobs)", False,
          "Value right; unit wrong: pending_blob_bytes sums the checkpoint blob and all write blobs of the "
          "thread. 28 B (12 nonce + 16 tag) per blob is the expected per-blob cost. See CORRECTIONS.md C7.")
    rows_after = conf.completed_rows.unique().tolist()
    check("3.6", "B2", "checkpoint rows after purge 0", 0, rows_after, rows_after == [0])

    # ------------------------------------------------------------------
    # 4. Encryption
    tbl = enc.groupby(["config", "manipulation", "outcome"]).size().unstack(fill_value=0)
    facts["enc_outcomes"] = {f"{c}|{m}": r.to_dict() for (c, m), r in tbl.iterrows()}
    sends = enc.groupby(["config", "manipulation"]).delivered.apply(lambda s: int((s > 0).sum()))
    errs = enc[enc.outcome == "rejected"].groupby(["config", "manipulation"]).error_type.agg(
        lambda s: s.value_counts().to_dict())
    exp = {
        ("A", "flip_ciphertext"): ("recovered_altered", 30, 30), ("C", "flip_ciphertext"): ("recovered_altered", 29, 29),
        ("A", "flip_tag"): ("recovered_unchanged", 30, 30), ("C", "flip_tag"): ("recovered_unchanged", 30, 30),
        ("A", "truncate"): ("rejected", 30, 0), ("C", "truncate"): ("rejected", 30, 0),
        ("A", "plaintext_inject"): ("recovered_altered", 30, 0), ("C", "plaintext_inject"): ("recovered_altered", 30, 0),
        ("A", "wrong_key"): ("recovered_unchanged", 30, 0), ("C", "wrong_key"): ("recovered_unchanged", 30, 0),
        ("A", "missing_key"): ("recovered_unchanged", 30, 0), ("C", "missing_key"): ("recovered_unchanged", 30, 0),
        ("A", "none"): ("recovered_unchanged", 30, 30), ("C", "none"): ("recovered_unchanged", 30, 30),
    }
    for cfg in "BDEF":
        exp[(cfg, "none")] = ("recovered_unchanged", 30, 30)
        for m in ["flip_ciphertext", "flip_tag", "truncate", "plaintext_inject", "wrong_key", "missing_key"]:
            exp[(cfg, m)] = ("rejected", 30, 0)
    ok, bad = True, []
    for (cfg, m), (oc, k, s) in exp.items():
        got = int(tbl.loc[(cfg, m)].get(oc, 0))
        if got != k or int(sends.loc[(cfg, m)]) != s:
            ok, bad = False, bad + [(cfg, m, got, int(sends.loc[(cfg, m)]))]
    check("4.1", "B3", "tamper/key table cells (outcome counts and sends)", "table", bad or "all 42 cells", ok)
    errs_d = {f"{c}|{m}": v for (c, m), v in errs.items()}
    facts["enc_errors"] = errs_d
    pi = {k: v for k, v in errs_d.items() if k.endswith("plaintext_inject")}
    check("4.2", "B3", "encrypted plaintext_inject refused with ValueError", "ValueError", pi,
          all(v == {"ValueError": 30} for v in pi.values()))
    key = {k: v for k, v in errs_d.items() if k.endswith(("wrong_key", "missing_key"))}
    check("4.3", "B3/D3", "wrong/missing key reported in the tamper-detection table as 'rejected'",
          "'Every manipulation is rejected'", key, False,
          "A wrong or missing key is a key-availability failure, not a detected tampering event; the "
          "InvalidTag is identical to tamper detection, so the two are indistinguishable to the system. "
          "See CORRECTIONS.md C1.")
    lat = data["encryption_latency"]
    em, dm = lat.groupby("config").encrypt_us.median(), lat.groupby("config").decrypt_us.median()
    ep = lat.groupby("config").encrypt_us.quantile(0.95)
    dp = lat.groupby("config").decrypt_us.quantile(0.95)
    check("4.4", "B3", "AES-GCM median encrypt 8-17 us / decrypt 7.4-9.2 us",
          "8-17 / 7.4-9.2", f"{em.min():.2f}-{em.max():.2f} / {dm.min():.2f}-{dm.max():.2f}",
          round(em.min()) == 8 and round(em.max()) == 17 and round(dm.min(), 1) == 7.4 and round(dm.max(), 1) == 9.2)
    check("4.5", "B3", "AES-GCM P95 encrypt 23.4-24.0 / decrypt 21.7-22.9",
          "23.4-24.0 / 21.7-22.9", f"{ep.min():.2f}-{ep.max():.2f} / {dp.min():.2f}-{dp.max():.2f}",
          round(ep.min(), 1) == 23.4 and round(ep.max(), 1) == 24.0 and round(dp.min(), 1) == 21.7 and round(dp.max(), 1) == 22.9)
    check("4.6", "B3", "'180 trials x 200 repetitions'", "180 x 200",
          f"{len(lat)} rows, each the mean of 200 repetitions", len(lat) == 180,
          "Each row is a per-run mean; the median/P95 are over 30 run-means per configuration, not over "
          "6,000 individual timings. See CORRECTIONS.md C9.")

    # ------------------------------------------------------------------
    # 5. Deserialization
    ds = data["deserialization_store"]
    g = ds.groupby(["config", "attacker"]).agg(n=("trial", "size"), built=("probe_constructed", lambda s: int(b(s).sum())),
                                              raised=("error_type", lambda s: int(s.fillna("").ne("").sum())))
    exp = {("A", "no_key"): (30, 0), ("C", "no_key"): (0, 0), ("D", "key_holder"): (30, 0)}
    for cfg in "BDEF":
        exp[(cfg, "no_key")] = (0, 30)
    for cfg in "BEF":
        exp[(cfg, "key_holder")] = (0, 0)
    ok = all(g.loc[k, "built"] == v[0] and g.loc[k, "raised"] == v[1] and g.loc[k, "n"] == 30 for k, v in exp.items())
    check("5.1", "B4", "store-level probe table", "table", g.to_dict("index") if not ok else "all 10 cells", ok)
    sr = serde
    comp = sr[sr.case.str.startswith("checkpoint_state")]
    eq = int(b(comp.equal).sum())
    check("5.2", "B4", "checkpoint state round-trips 180/180 per mode", "180/180 each",
          f"{eq}/{len(comp)} (both modes together)", eq == 360 and len(comp) == 360)
    kp = sr[sr.case == "known_probe_class"].groupby("mode").constructed.apply(lambda s: int(b(s).sum())).to_dict()
    check("5.3", "B4", "known probe class: permissive constructs 30/30, strict 0/30", "30 / 0", kp,
          kp == {"permissive": 30, "strict": 0})
    tup = sr[sr.case == "type_tuple"].loaded_type.unique().tolist()
    check("5.4", "B4", "tuple comes back as list", "list", tup, tup == ["list"])

    # ------------------------------------------------------------------
    # 6. Fisher tests (two-sided as reported; one-sided + Holm as the prereg would require)
    def fe(k1, n1, k2, n2, alt="two-sided"):
        return stats.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]], alternative=alt)[1]
    fis = {
        "R5 dup B vs F": fe(0, 30, 30, 30), "R5 dup B vs A": fe(0, 30, 30, 30),
        "L3 dup B vs F": fe(0, 30, 30, 30), "probe key-holder B vs D": fe(0, 30, 30, 30),
    }
    exact = 2 / math.comb(60, 30)
    facts["fisher_two_sided"] = fis
    facts["fisher_exact_value"] = exact
    check("6.1", "B5", "Fisher two-sided 0/30 vs 30/30 p < 1e-16", "< 1e-16",
          f"{exact:.3e} (= 2 / C(60,30))", exact < 1e-16)
    one = fe(0, 30, 30, 30, "less")
    facts["fisher_one_sided"] = one
    holm = sorted(fis.values())
    facts["holm_adjusted"] = [min(1, p * (len(holm) - i)) for i, p in enumerate(holm)]

    # ------------------------------------------------------------------
    # 7. Performance
    p = perf[(perf.status == "complete") & ~b(perf.warmup)]
    check("7.0", "B6", "40 measured runs per configuration", "40",
          p.groupby("config").size().to_dict(), all(p.groupby("config").size() == 40))
    metrics = {"workflow_s": 1000, "to_pause_s": 1000, "approve_s": 1000, "write_mean_ms": 1, "read_mean_ms": 1,
               "recovery_total_ms": 1, "pause_blob_bytes": 1}
    perf_rows = []
    base = {m: p[p.config == "A"][m].values * s for m, s in metrics.items()}
    for m, s in metrics.items():
        for cfg in ORDER:
            x = p[p.config == cfg][m].values * s
            lo, hi = boot_median(x)
            rlo, rhi = boot_ratio(x, base[m])
            perf_rows.append({"metric": m, "config": cfg, "n": len(x), "mean": x.mean(), "median": np.median(x),
                              "sd": x.std(ddof=1), "p95": np.percentile(x, 95), "p95_nearest_rank":
                              np.percentile(x, 95, method="inverted_cdf"),
                              "median_ci_lo": lo, "median_ci_hi": hi,
                              "overhead_pct": (np.median(x) / np.median(base[m]) - 1) * 100,
                              "ratio_ci_lo_pct": (rlo - 1) * 100, "ratio_ci_hi_pct": (rhi - 1) * 100})
    pr = pd.DataFrame(perf_rows)
    pr.to_csv(os.path.join(OUT, "performance_recomputed.csv"), index=False)
    # compare with the generated table (deterministic stats exactly, bootstrap with tolerance)
    gen = pd.read_csv(os.path.join(TAB, "experiment_6_performance.csv"))
    label = {"workflow_s": "Workflow (pause + approve)", "to_pause_s": "Run to pause", "approve_s": "Approve to completion",
             "write_mean_ms": "Checkpoint write", "read_mean_ms": "Checkpoint read",
             "recovery_total_ms": "Recovery: open + build + read", "pause_blob_bytes": "Stored blob bytes"}
    det_bad, boot_dev = [], []
    for _, r in pr.iterrows():
        gr = gen[(gen.metric == label[r.metric]) & (gen.config == r.config)].iloc[0]
        for col, gcol in [("mean", "mean"), ("median", "median"), ("sd", "sd"), ("p95", "p95"), ("overhead_pct", "overhead_vs_A_pct")]:
            if not close(r[col], gr[gcol], 1e-6 * max(1, abs(gr[gcol]))):
                det_bad.append((r.metric, r.config, col, r[col], gr[gcol]))
        scale = max(abs(gr["median"]), 1e-9)
        boot_dev.append(max(abs(r.median_ci_lo - gr.median_ci_lo), abs(r.median_ci_hi - gr.median_ci_hi)) / scale * 100)
        boot_dev.append(max(abs(r.ratio_ci_lo_pct - (gr.ratio_ci_lo - 1) * 100),
                            abs(r.ratio_ci_hi_pct - (gr.ratio_ci_hi - 1) * 100)))
    check("7.1", "B6", "mean, median, SD, P95, overhead vs generated table (exact)", "table",
          det_bad or "all equal to 1e-6", not det_bad)
    facts["bootstrap_max_dev_pct_points"] = max(boot_dev)
    check("7.2", "B6", "bootstrap CIs reproduce with an independent generator", "table",
          f"max deviation {max(boot_dev):.2f} percentage points", max(boot_dev) < 3.0,
          "Monte Carlo; tolerance 3 percentage points of the median / of the ratio")

    def pv(m, cfg, col):
        return float(pr[(pr.metric == m) & (pr.config == cfg)][col].iloc[0])
    stated_b6 = [
        ("workflow_s", "A", 36.2, 35.9, 2.8, 41.6, None),
        ("workflow_s", "B", 49.3, 49.3, 3.4, 55.0, 37.1), ("workflow_s", "C", 50.7, 50.1, 4.3, 58.9, 39.2),
        ("workflow_s", "D", 49.7, 50.2, 3.6, 54.9, 39.6), ("workflow_s", "E", 48.8, 48.5, 3.9, 54.7, 34.9),
        ("workflow_s", "F", 36.9, 36.4, 3.0, 42.4, 1.2),
        ("approve_s", "A", 16.1, 16.3, 1.4, 17.9, None), ("approve_s", "B", 28.4, 28.1, 1.7, 31.2, 72.6),
        ("approve_s", "F", 16.0, 15.7, 1.9, 19.5, -3.5),
        ("recovery_total_ms", "A", 68.1, 61.7, 35.6, 77.5, None), ("recovery_total_ms", "B", 88.8, 81.6, 42.0, 90.6, 32.4),
        ("recovery_total_ms", "F", 69.1, 61.7, 38.0, 71.7, 0.0),
    ]
    bad = []
    for m, cfg, mean, medv, sd, p95, ov in stated_b6:
        got = (round(pv(m, cfg, "mean"), 1), round(pv(m, cfg, "median"), 1), round(pv(m, cfg, "sd"), 1),
               round(pv(m, cfg, "p95"), 1), None if ov is None else round(pv(m, cfg, "overhead_pct"), 1))
        if got != (mean, medv, sd, p95, ov):
            bad.append((m, cfg, (mean, medv, sd, p95, ov), got))
    check("7.3", "B6", "B6 table values (mean, median, SD, P95, overhead)", "table", bad or "all equal at 1 dp", not bad)
    rd = {c: pv("read_mean_ms", c, "median") for c in ORDER}
    check("7.4", "D6", "encryption raised per-call read from 0.12 to 0.18 ms", "0.12 -> 0.18",
          {k: round(v, 3) for k, v in rd.items()}, round(rd["A"], 2) == 0.12 and round(rd["B"], 2) == 0.18,
          "Values are medians of per-run mean latencies, not per-call medians. See CORRECTIONS.md C8.")
    d_appr = {c: pv("approve_s", c, "mean") - pv("approve_s", "A", "mean") for c in "BCDE"}
    d_appr_med = {c: pv("approve_s", c, "median") - pv("approve_s", "A", "median") for c in "BCDE"}
    check("7.5", "D6", "+12.3 ms approve-to-completion in every ledger configuration", "+12.3 ms",
          f"mean diff {', '.join(f'{c} {v:.1f}' for c, v in d_appr.items())}; median diff "
          f"{', '.join(f'{c} {v:.1f}' for c, v in d_appr_med.items())}",
          all(11.5 <= v <= 13.5 for v in d_appr.values()),
          "+12.3 ms is B's mean difference; the per-configuration range is 12.3-13.5 ms (mean) / 11.8-12.5 ms (median)")
    d_rec = pv("recovery_total_ms", "B", "median") - pv("recovery_total_ms", "A", "median")
    check("7.6", "D6", "+20 ms recovery with the ledger", "+20 ms", f"{d_rec:.1f} ms (B-A medians)", round(d_rec) == 20)
    u = stats.mannwhitneyu(p[p.config == "B"].workflow_s, p[p.config == "A"].workflow_s, alternative="two-sided")
    check("7.7", "B6", "Mann-Whitney U=1600, p=1.4e-14", "U=1600, p=1.4e-14", f"U={u.statistic:.0f}, p={u.pvalue:.2e}",
          u.statistic == 1600 and f"{u.pvalue:.1e}" == "1.4e-14")
    mem = data["performance_memory"].groupby("config").peak_traced_mb.median()
    check("7.8", "B6", "memory A/B medians 0.315/0.317 MB", "0.315 / 0.317",
          f"{mem['A']:.3f} / {mem['B']:.3f}", round(mem["A"], 3) == 0.315 and round(mem["B"], 3) == 0.317)
    # Workflow overhead split
    facts["workflow_ratio_B_F"] = pv("workflow_s", "B", "median") / pv("workflow_s", "F", "median")

    # ------------------------------------------------------------------
    # 8. Bootstrap-implementation property: shared global RNG
    facts["bootstrap_note"] = ("analyze.py draws all bootstrap resamples from one module-level generator "
                               "(seed 20261111), so each interval depends on the order of calls; intervals are "
                               "reproducible only by re-running the whole script unchanged.")

    pd.DataFrame(checks).to_csv(os.path.join(OUT, "checks.csv"), index=False)
    with open(os.path.join(OUT, "facts.json"), "w") as f:
        json.dump(facts, f, indent=2, default=str)
    n_bad = sum(c["status"] == "MISMATCH" for c in checks)
    print(f"{len(checks)} checks, {len(checks) - n_bad} match, {n_bad} mismatch")
    for c in checks:
        if c["status"] == "MISMATCH":
            print(f"  {c['id']} {c['claim']}: stated {c['stated']} | recomputed {c['recomputed']}")


if __name__ == "__main__":
    sys.exit(main())
