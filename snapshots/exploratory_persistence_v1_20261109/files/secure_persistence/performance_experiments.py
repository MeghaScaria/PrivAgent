"""
Experiment 6: performance overhead. Runs sequentially in one process
(no parallel load), with the configuration order shuffled in every
repetition and warm-up repetitions recorded but flagged.

Per repetition and configuration, on a fresh store:
  build        TrajectoryMonitor + graph compile (setup, reported apart)
  to_pause     start() until the approval pause
  write        each checkpoint put / put_writes during the run (timed at
               the saver)
  storage      blob bytes and database + WAL + SHM bytes at the pause
  recovery     simulated restart: close the store, reopen it, rebuild the
               graph, and read the pending request (store open, graph
               build and checkpoint read timed separately)
  read         each checkpoint get_tuple during recovery
  approve      submit_review(approve) until the run completes
  workflow     to_pause + approve (the measured execution, setup excluded)
  cpu          process CPU time over the whole repetition

A separate pass measures peak Python allocations (tracemalloc) for the
workflow, because tracing slows execution.
"""
import os
import random
import shutil
import sqlite3
import tempfile
import time
import tracemalloc

import harness
from agents.approval_flow import pending_review, start, submit_review
from agents.state import new_state
from configurations import CONFIGS, ExperimentStore, minimization, store_files

FIELDS = ["config", "rep", "order", "warmup", "status", "error", "build_s", "to_pause_s",
          "write_calls", "write_total_ms", "write_mean_ms", "pause_blob_bytes", "pause_file_bytes",
          "recovery_store_open_ms", "recovery_app_build_ms", "recovery_read_ms", "recovery_total_ms",
          "read_calls", "read_mean_ms", "approve_s", "workflow_s", "cpu_s", "delivered"]
MEMORY_FIELDS = ["config", "rep", "status", "error", "peak_traced_mb"]


def _timed(store, sink):
    saver = store.checkpointer
    for name in ("put", "put_writes", "get_tuple"):
        original = getattr(saver, name)

        def wrapper(*a, _orig=original, _name=name, **k):
            t = time.perf_counter()
            try:
                return _orig(*a, **k)
            finally:
                sink.append((_name, (time.perf_counter() - t) * 1000))
        setattr(saver, name, wrapper)


def _sizes(directory, checkpoint_path):
    with sqlite3.connect(checkpoint_path) as conn:
        blob = (conn.execute("SELECT COALESCE(SUM(LENGTH(checkpoint)),0) FROM checkpoints").fetchone()[0]
                + conn.execute("SELECT COALESCE(SUM(LENGTH(value)),0) FROM writes").fetchone()[0])
    files = sum(os.path.getsize(p) for p in store_files(directory)
                if os.path.basename(p).startswith("checkpoints"))
    return blob, files


def one_run(config, rep, order, warmup):
    base = tempfile.mkdtemp(prefix=f"sp_perf_{config}_")
    row = {"config": config, "rep": rep, "order": order, "warmup": warmup, "status": "complete", "error": ""}
    store = None
    try:
        c = harness.canaries(f"perf-{rep}")
        tx = os.path.join(base, "tx.jsonl")
        harness.install_mcp(c, tx)
        directory, logs, thread = os.path.join(base, "store"), os.path.join(base, "logs"), f"t-{rep}"
        cpu0 = time.process_time()
        store = ExperimentStore(config, directory)
        calls = []
        _timed(store, calls)
        with minimization(CONFIGS[config]["minim"]):
            t0 = time.perf_counter()
            app = harness.build_app(store, f"perf-{rep}", logs, c)
            t1 = time.perf_counter()
            start(app, new_state(task=harness.task_text(c), run_id=f"perf-{rep}"), thread)
            t2 = time.perf_counter()
            writes = [ms for name, ms in calls if name in ("put", "put_writes")]
            row["pause_blob_bytes"], row["pause_file_bytes"] = _sizes(directory, store.checkpoint_path)
            store.close()
            store = None
            # Simulated restart
            r0 = time.perf_counter()
            store = ExperimentStore(config, directory)
            reads = []
            _timed(store, reads)
            r1 = time.perf_counter()
            app2 = harness.build_app(store, "recovery", logs)
            r2 = time.perf_counter()
            request = pending_review(app2, thread)
            r3 = time.perf_counter()
            submit_review(app2, thread, {"action_id": request["action_id"],
                                         "action_digest": request["action_digest"],
                                         "decision": "approve", "reviewer": "experiment"})
            r4 = time.perf_counter()
        read_ms = [ms for name, ms in reads if name == "get_tuple"]
        row.update(
            build_s=t1 - t0, to_pause_s=t2 - t1, write_calls=len(writes),
            write_total_ms=sum(writes), write_mean_ms=sum(writes) / len(writes) if writes else None,
            recovery_store_open_ms=(r1 - r0) * 1000, recovery_app_build_ms=(r2 - r1) * 1000,
            recovery_read_ms=(r3 - r2) * 1000, recovery_total_ms=(r3 - r0) * 1000,
            read_calls=len(read_ms), read_mean_ms=sum(read_ms) / len(read_ms) if read_ms else None,
            approve_s=r4 - r3, workflow_s=(t2 - t1) + (r4 - r3), cpu_s=time.process_time() - cpu0,
            delivered=harness.count_events(tx, "delivered"))
    except Exception as e:
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if store is not None:
            store.close()
        shutil.rmtree(base, ignore_errors=True)
    return row


def memory_run(config, rep):
    base = tempfile.mkdtemp(prefix=f"sp_mem_{config}_")
    row = {"config": config, "rep": rep, "status": "complete", "error": ""}
    store = None
    try:
        c = harness.canaries(f"mem-{rep}")
        harness.install_mcp(c, os.path.join(base, "tx.jsonl"))
        store = ExperimentStore(config, os.path.join(base, "store"))
        with minimization(CONFIGS[config]["minim"]):
            app = harness.build_app(store, f"mem-{rep}", os.path.join(base, "logs"), c)
            tracemalloc.start()
            start(app, new_state(task=harness.task_text(c), run_id=f"mem-{rep}"), f"t-{rep}")
            request = pending_review(app, f"t-{rep}")
            submit_review(app, f"t-{rep}", {"action_id": request["action_id"],
                                            "action_digest": request["action_digest"],
                                            "decision": "approve", "reviewer": "experiment"})
            row["peak_traced_mb"] = tracemalloc.get_traced_memory()[1] / 1e6
            tracemalloc.stop()
    except Exception as e:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if store is not None:
            store.close()
        shutil.rmtree(base, ignore_errors=True)
    return row


def schedule(configs, reps, warmups, seed=20261110):
    rng = random.Random(seed)
    plan = []
    for rep in range(warmups + reps):
        order = list(configs)
        rng.shuffle(order)
        plan += [(cfg, rep, i, rep < warmups) for i, cfg in enumerate(order)]
    return plan
