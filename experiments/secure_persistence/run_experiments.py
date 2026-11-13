"""
Runs the secure-persistence experiments and writes every individual
trial to CSV.

    python run_experiments.py --quick            # harness validation, n=2, results/validation/
    python run_experiments.py                    # full run, results/
    python run_experiments.py --only recovery ledger --workers 8

Trials that patch process-wide state (the synthetic MCP server, the
minimization switch) run sequentially in this process; only work that
happens in separate processes (crash-recovery workers, probe loads) runs
in parallel. Performance runs last, alone. Failed trials are written
like any other, with status=failed and the error.
"""
import argparse
import concurrent.futures as cf
import csv
import datetime
import importlib.metadata as md
import json
import logging
import os
import platform
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import psutil  # noqa: E402

import harness  # noqa: E402,F401  (puts the project root on sys.path first)
import confidentiality_experiments as conf  # noqa: E402
import deserialization_experiments as deser  # noqa: E402
import encryption_experiments as enc  # noqa: E402
import ledger_experiments as ledger  # noqa: E402
import performance_experiments as perf  # noqa: E402
import recovery_experiments as recovery  # noqa: E402
from configurations import CONFIGS  # noqa: E402

EXPERIMENTS = ["recovery", "ledger", "confidentiality", "encryption", "deserialization", "performance"]
SEED = 20261109


class CsvSink:
    def __init__(self, path, fields=None):
        self.path, self.fields, self.rows = path, fields, 0
        if os.path.exists(path):
            os.remove(path)

    def write(self, rows):
        rows = [rows] if isinstance(rows, dict) else rows
        if not rows:
            return
        if self.fields is None:
            self.fields = list(rows[0].keys())
        new = not os.path.exists(self.path)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.fields, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerows(rows)
        self.rows += len(rows)


def environment():
    pkgs = ["langgraph", "langgraph-checkpoint", "langgraph-checkpoint-sqlite", "cryptography",
            "ormsgpack", "numpy", "pandas", "scipy", "matplotlib", "psutil"]
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "platform": platform.platform(), "processor": platform.processor(),
        "cpu_logical": psutil.cpu_count(), "cpu_physical": psutil.cpu_count(logical=False),
        "memory_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
        "packages": {p: md.version(p) for p in pkgs},
        "power_plan_note": "not controlled; laptop/desktop default",
    }


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def run_recovery(out, configs, n, workers):
    sink = CsvSink(os.path.join(out, "recovery.csv"), recovery.FIELDS)
    jobs = recovery.plan(configs, n, SEED)
    log(f"recovery: {len(jobs)} trials, {workers} in parallel")
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(recovery.run_trial, *job) for job in jobs]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            sink.write(fut.result())
            if i % 50 == 0:
                log(f"recovery: {i}/{len(jobs)}")


def run_ledger(out, configs, n):
    sink = CsvSink(os.path.join(out, "ledger.csv"), ledger.FIELDS)
    for t in range(n):
        for config in configs:
            for scenario in ledger.SCENARIOS:
                sink.write(ledger.run_trial(config, scenario, t, f"{SEED}-L-{config}-{scenario}-{t}"))
    log(f"ledger: {sink.rows} trials")


def run_confidentiality(out, configs, n):
    sink = CsvSink(os.path.join(out, "confidentiality.csv"))
    rows = [conf.run_trial(config, t, f"{SEED}-C-{config}-{t}") for t in range(n) for config in configs]
    fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("config", "trial", "seed",
                                                                          "status", "error"), k))
    sink.fields = fields
    sink.write(rows)
    log(f"confidentiality: {sink.rows} trials")


def run_encryption(out, configs, n):
    sink = CsvSink(os.path.join(out, "encryption.csv"), enc.FIELDS)
    lat = CsvSink(os.path.join(out, "encryption_latency.csv"), enc.LATENCY_FIELDS)
    for t in range(n):
        for config in configs:
            rows, latency = enc.run_trial(config, t, f"{SEED}-E-{config}-{t}")
            sink.write(rows)
            if latency:
                lat.write(latency)
    log(f"encryption: {sink.rows} manipulation rows")


def run_deserialization(out, configs, n, workers):
    store_sink = CsvSink(os.path.join(out, "deserialization_store.csv"), deser.STORE_FIELDS)
    jobs = []
    for t in range(n):
        for config in configs:
            attackers = ["no_key", "key_holder"] if CONFIGS[config]["enc"] else ["no_key"]
            for attacker in attackers:
                jobs.append(deser.prepare_store_trial(config, attacker, t, f"{SEED}-D-{config}-{attacker}-{t}"))
    log(f"deserialization: {len(jobs)} store trials prepared; loading in {workers} processes")
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(deser.load_store_trial, jobs):
            store_sink.write(row)
    serde_sink = CsvSink(os.path.join(out, "deserialization_serde.csv"), deser.SERDE_FIELDS)
    for t in range(n):
        serde_sink.write(deser.serde_trials(t, f"{SEED}-S-{t}"))
        for config in configs:
            serde_sink.write(deser.compatibility_trial(config, t, f"{SEED}-K-{config}-{t}"))
    log(f"deserialization: {store_sink.rows} store rows, {serde_sink.rows} serializer rows")


def run_performance(out, configs, n, warmups, memory_n):
    sink = CsvSink(os.path.join(out, "performance.csv"), perf.FIELDS)
    for config, rep, order, warm in perf.schedule(configs, n, warmups):
        sink.write(perf.one_run(config, rep, order, warm))
    mem = CsvSink(os.path.join(out, "performance_memory.csv"), perf.MEMORY_FIELDS)
    for rep in range(memory_n):
        for config in configs:
            mem.write(perf.memory_run(config, rep))
    log(f"performance: {sink.rows} runs, {mem.rows} memory runs")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="validation run: n=2, results/validation/")
    p.add_argument("--only", nargs="*", choices=EXPERIMENTS)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--perf-n", type=int, default=40)
    args = p.parse_args()
    logging.disable(logging.WARNING)

    n, perf_n, warm, mem_n = (2, 3, 1, 2) if args.quick else (args.n, args.perf_n, 5, 10)
    out = os.path.join(HERE, "results", "validation" if args.quick else "")
    os.makedirs(out, exist_ok=True)
    configs = sorted(CONFIGS)
    selected = args.only or EXPERIMENTS
    with open(os.path.join(out, "environment.json"), "w") as f:
        json.dump({**environment(), "n": n, "perf_n": perf_n, "warmups": warm,
                   "memory_n": mem_n, "workers": args.workers, "experiments": selected,
                   "seed": SEED}, f, indent=2)
    t0 = time.time()
    if "recovery" in selected:
        run_recovery(out, configs, n, args.workers)
    if "ledger" in selected:
        run_ledger(out, configs, n)
    if "confidentiality" in selected:
        run_confidentiality(out, configs, n)
    if "encryption" in selected:
        run_encryption(out, configs, n)
    if "deserialization" in selected:
        run_deserialization(out, configs, n, args.workers)
    if "performance" in selected:
        run_performance(out, configs, perf_n, warm, mem_n)
    log(f"done in {time.time() - t0:.0f}s; results in {out}")


if __name__ == "__main__":
    main()
