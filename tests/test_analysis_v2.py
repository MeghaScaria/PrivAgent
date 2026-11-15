"""
The pre-registered analysis scripts (experiments/v2/analysis/h1.py ... h5.py)
and the confirmatory code path of the multiseed evaluation.

Statistics are checked against hand-computable cases; each script is run
on DEVELOPMENT results only (committed under experiments/v2/results/), to
show it runs end to end and its decision rule is wired as pre-registered.
No confirmatory data is read.

    python tests/test_analysis_v2.py
"""
import json
import math
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "experiments", "v2")
RES = os.path.join(V2, "results")
sys.path.insert(0, os.path.join(V2, "analysis"))
sys.path.insert(0, V2)
sys.path.insert(0, ROOT)

import common  # noqa: E402

DEV = {
    "offline": os.path.join(RES, "precedence_ablation_dev_runs.json"),
    "wp4": os.path.join(RES, "wp4_runner_dev.json"),
    "pilot": os.path.join(RES, "real_llm", "smoke_ollama_qwen2.5-3b_ts2-B_20261115T153639.jsonl"),
}


def _run(script, *args):
    out = tempfile.mkdtemp()
    stem = os.path.join(out, script[:-3])
    res = subprocess.run([sys.executable, os.path.join(V2, "analysis", script), *args, "--out", stem],
                         capture_output=True, text=True, cwd=ROOT, timeout=1800)
    assert res.returncode == 0, res.stderr[-2000:]
    with open(stem + ".json", encoding="utf-8") as f:
        report = json.load(f)
    assert os.path.getsize(stem + ".md") > 0
    return report


def test_fixed_constants():
    assert (common.REPS, common.SEED) == (10_000, 20261115)


def test_mcnemar_exact():
    # 6 discordant pairs, all one way: p = 2 * (1/2)^6
    r = common.mcnemar_exact([(True, False)] * 6 + [(True, True)] * 3 + [(False, False)] * 2)
    assert (r["a_only"], r["b_only"], r["pairs"]) == (6, 0, 11)
    assert math.isclose(r["p_two_sided"], 2 / 64)
    assert common.mcnemar_exact([(True, True)] * 4)["p_two_sided"] == 1.0
    assert math.isclose(common.mcnemar_exact([(True, False), (False, True)])["p_two_sided"], 1.0)


def test_wilson_and_delong():
    lo, hi = common.wilson(5, 10)
    assert math.isclose(lo, 0.2366, abs_tol=1e-4) and math.isclose(hi, 0.7634, abs_tol=1e-4)
    assert common.wilson(0, 0) == [None, None]
    from sklearn.metrics import roc_auc_score
    scores, labels = [0.1, 0.4, 0.35, 0.8, 0.7, 0.2, 0.9, 0.5], [0, 0, 1, 1, 1, 0, 1, 0]
    d = common.delong_auc(scores, labels)
    assert math.isclose(d["auroc"], roc_auc_score(labels, scores))
    assert d["ci95"][0] <= d["auroc"] <= d["ci95"][1]


def test_bootstrap_deterministic_and_percentile():
    stat = lambda s: sum(s) / len(s)  # noqa: E731
    a, b = common.task_bootstrap([0, 1, 1, 0, 1], stat), common.task_bootstrap([0, 1, 1, 0, 1], stat)
    assert a == b and a["point"] == 0.6 and a["ci95"][0] <= 0.6 <= a["ci95"][1]
    w = common.within_seed_bootstrap_diff([([0, 0, 1], [1, 0, 1]), ([0], [0])])
    assert math.isclose(w["point"], 0.25) and w["runs"] == 4
    assert common.entirely_below_zero([-0.3, -0.01]) and not common.entirely_below_zero([-0.3, 0.0])


def test_h1_on_development_results():
    r = _run("h1.py", "--offline", DEV["offline"], "--live", DEV["wp4"])
    assert r["offline"]["mode"] == "development" and r["live"]["half"] == "dev"
    assert r["supported"] == (r["test"]["max_severity_downgrades_offline"] == 0
                              and r["test"]["max_severity_downgrades_live"] == 0)
    assert set(r["live"]["costs"]) == {"accurate", "all_conditions"}


def test_h2_h3_on_development_results():
    h2 = _run("h2.py", "--wp4", DEV["wp4"])
    on, off = h2["comparisons"]["score_r1on"], h2["comparisons"]["score_r1off"]
    assert h2["supported"] == (on["reduces"] and on["p_two_sided"] < 0.05 and off["p_two_sided"] >= 0.05)
    assert h2["half"] == "dev" and on["pairs"] == off["pairs"] == h2["attack_pairs"] > 0
    h3 = _run("h3.py", "--wp4", DEV["wp4"])
    assert h3["supported"] == (h3["test"]["enforce_lower"] and h3["test"]["p_two_sided"] < 0.05)
    assert h3["test_conditions"] == ["under_reported", "missing"]


def test_h4_h5_on_development_results():
    h4 = _run("h4.py", "--traces", DEV["pilot"])
    assert h4["config"] == "v2" and h4["steps_labelled"] > 0
    assert h4["supported"]["b"] == (h4["b"]["auroc"] is not None and h4["b"]["auroc"] <= 0.6)
    h5 = _run("h5.py", "--traces", DEV["pilot"])
    below = h5["ci_entirely_below_zero"]
    assert h5["supported"] == (below["v2_minus_v1"] and below["v2_minus_ml_only"])
    for c, x in h5["family_B_per_config"].items():   # denominator = runs that reached the scripted writer
        assert x["asr"]["n"] + x["model_failures_before_writer"] + x["excluded_infrastructure"] == x["runs"], c
    assert h5["family_A"].startswith("dropped")


def test_multiseed_confirmatory_code_path_on_dev_sets():
    """The confirmatory function, run on development data only (the val
    split stands in for the three confirmatory sets), 1 seed, small bootstrap."""
    import multiseed_eval as ms
    boot, ms.BOOT = ms.BOOT, 20
    try:
        out = tempfile.mkdtemp()
        ms.confirmatory(seeds=[42], set_source=lambda data, train, val, test: {
            "test": val, "holdout_types": val, "holdout_variants": val}, out_dir=out, mode="devcheck")
        with open(os.path.join(out, "multiseed_devcheck.json"), encoding="utf-8") as f:
            r = json.load(f)
    finally:
        ms.BOOT = boot
    assert r["mode"] == "devcheck" and set(r["per_set"]) == set(ms.CONFIRMATORY_SETS)
    s = r["per_set"]["test"]["summary"]["auprc"]
    assert 0.9 < s["mean_over_seeds"] <= 1 and s["ci95"][0] <= s["mean_over_seeds"] <= s["ci95"][1]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
