"""
Experiment 4: strict versus permissive MsgPack deserialization.

Part 1, per configuration (store-level): a paused run's checkpoint is
rewritten so that its final_output holds a SideEffectProbe object, then
the thread is recovered in a separate process (probe_worker.py). Two
attacker models:
  no_key       the attacker can write the store but has no key, so the
               blob is stored unencrypted (what A2/A4 can do)
  key_holder   the attacker also holds the checkpoint key and encrypts the
               blob properly (attacker B); only meaningful when encryption
               is on
Measured: whether the probe was constructed (marker file written),
whether recovery raised, and what type final_output came back as.

Part 2, serializer-level (no store): how permissive and strict decoding
treat an importable probe class, a class whose module doesn't exist in
the loading process, a set of standard Python types, and real
checkpoint state from a paused run (compatibility). Probe loads always
run in a subprocess.
"""
import datetime
import decimal
import json
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import uuid

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

import harness
from configurations import CONFIGS, ExperimentStore, minimization
from gadget import SideEffectProbe
from governance.checkpoint_store import CHECKPOINT_DB, AesGcmCipher, derive_key
from procs import run

STORE_FIELDS = ["config", "attacker", "trial", "seed", "status", "error", "blob_encrypted",
                "probe_constructed", "markers", "loaded", "error_type", "final_output_type"]
SERDE_FIELDS = ["case", "mode", "trial", "status", "error", "dumped", "loaded",
                "equal", "constructed", "loaded_type", "error_type"]
PERMISSIVE = dict(allowed_msgpack_modules=True)
STRICT = dict(pickle_fallback=False, allowed_json_modules=None, allowed_msgpack_modules=None)


def _probe_checkpoint_blob(store, thread, label):
    tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
    cp = dict(tup.checkpoint)
    cp["channel_values"] = {**cp["channel_values"], "final_output": SideEffectProbe(label)}
    return JsonPlusSerializer(**PERMISSIVE).dumps_typed(cp)


def prepare_store_trial(config, attacker, trial, seed):
    """In-process setup (sequential): a paused run whose checkpoint now
    holds a probe object. Returns the row and what the load step needs."""
    base = tempfile.mkdtemp(prefix=f"sp_des_{config}_")
    row = {"config": config, "attacker": attacker, "trial": trial, "seed": seed,
           "status": "complete", "error": ""}
    job = {"base": base, "row": row}
    try:
        c = harness.canaries(seed)
        harness.install_mcp(c, os.path.join(base, "tx.jsonl"))
        directory = os.path.join(base, "store")
        store = ExperimentStore(config, directory)
        thread = f"thread-{seed}"
        with minimization(CONFIGS[config]["minim"]):
            harness.run_to_pause(store, c, thread, os.path.join(base, "logs"))
        typ, blob = _probe_checkpoint_blob(store, thread, f"probe-{seed}")
        encrypt = attacker == "key_holder" and CONFIGS[config]["enc"]
        if encrypt:
            name, blob = AesGcmCipher(derive_key(store.master_key, "checkpoint-aes-gcm")).encrypt(blob)
            typ = f"{typ}+{name}"
        store.close()
        with sqlite3.connect(os.path.join(directory, CHECKPOINT_DB)) as conn:
            conn.execute("UPDATE checkpoints SET type = ?, checkpoint = ? WHERE thread_id = ?",
                         (typ, blob, thread))
        row["blob_encrypted"] = encrypt
        job.update(directory=directory, thread=thread)
    except Exception as e:
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    return job


def load_store_trial(job):
    """Recovery in a separate process (safe to run in parallel)."""
    row, base = job["row"], job["base"]
    try:
        if row["status"] != "complete":
            return row
        probe_dir = os.path.join(base, "markers")
        os.makedirs(probe_dir)
        events, _ = run("probe_worker.py", "--config", row["config"], "--dir", job["directory"],
                        "--thread", job["thread"], extra_env={"PRIVAGENT_PROBE_DIR": probe_dir})
        result = next((e for e in events if e.get("event") == "probe_load"), {})
        markers = len(os.listdir(probe_dir))
        row.update(probe_constructed=markers > 0, markers=markers, loaded=result.get("loaded"),
                   error_type=result.get("error_type"), final_output_type=result.get("final_output_type"))
    except Exception as e:
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return row


def store_trial(config, attacker, trial, seed):
    return load_store_trial(prepare_store_trial(config, attacker, trial, seed))


# -- serializer level --------------------------------------------------

SERDE_LOADER = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
mode = sys.argv[2]
kw = dict(allowed_msgpack_modules=True) if mode == "permissive" else dict(
    pickle_fallback=False, allowed_json_modules=None, allowed_msgpack_modules=None)
typ, data = sys.argv[3], bytes.fromhex(open(sys.argv[4]).read())
out = {"event": "serde", "loaded": False, "loaded_type": "", "error_type": ""}
try:
    obj = JsonPlusSerializer(**kw).loads_typed((typ, data))
    out.update(loaded=True, loaded_type=type(obj).__name__)
except Exception as e:
    out["error_type"] = type(e).__name__
print(json.dumps(out), flush=True)
'''


def _subprocess_load(typ, data, mode, extra_path, probe_dir):
    tmp = tempfile.mkdtemp(prefix="sp_serde_")
    try:
        loader = os.path.join(tmp, "loader.py")
        with open(loader, "w") as f:
            f.write(SERDE_LOADER)
        blob = os.path.join(tmp, "blob.hex")
        with open(blob, "w") as f:
            f.write(data.hex())
        events, _ = run_script(loader, extra_path, mode, typ, blob,
                               env={"PRIVAGENT_PROBE_DIR": probe_dir})
        return next((e for e in events if e.get("event") == "serde"), {})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_script(path, *args, env=None):
    import subprocess
    e = {k: v for k, v in os.environ.items() if k not in ("PRIVAGENT_MASTER_KEY", "GOOGLE_API_KEY")}
    e.update(env or {})
    p = subprocess.run([sys.executable, path, *args], capture_output=True, text=True, env=e, timeout=180)
    events = [json.loads(line) for line in p.stdout.splitlines() if line.startswith("{")]
    return events, p.returncode


STANDARD_VALUES = {
    "set": {1, 2, 3},
    "frozenset": frozenset({"a", "b"}),
    "tuple": (1, "two"),
    "bytes": b"\x00\x01",
    "complex": complex(1, 2),
    "decimal": decimal.Decimal("1.10"),
    "datetime": datetime.datetime(2026, 11, 9, 12, 0, tzinfo=datetime.timezone.utc),
    "uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"),
    "path": pathlib.PurePosixPath("/tmp/x"),
}


def serde_trials(trial, seed):
    """One repetition of every serializer-level case, both modes."""
    rows = []
    here = os.path.dirname(os.path.abspath(__file__))
    # Importable probe class
    typ, data = JsonPlusSerializer(**PERMISSIVE).dumps_typed(SideEffectProbe(f"serde-{seed}"))
    for mode in ("permissive", "strict"):
        probe_dir = tempfile.mkdtemp(prefix="sp_markers_")
        res = _subprocess_load(typ, data, mode, here, probe_dir)
        rows.append({"case": "known_probe_class", "mode": mode, "trial": trial, "status": "complete",
                     "dumped": True, "loaded": res.get("loaded"), "loaded_type": res.get("loaded_type"),
                     "error_type": res.get("error_type"), "constructed": len(os.listdir(probe_dir)) > 0,
                     "equal": ""})
        shutil.rmtree(probe_dir, ignore_errors=True)
    # Class whose module the loading process can't import
    tmp = tempfile.mkdtemp(prefix="sp_ephemeral_")
    mod = f"ephemeral_probe_{uuid.uuid4().hex[:8]}"
    with open(os.path.join(tmp, f"{mod}.py"), "w") as f:
        f.write("from dataclasses import dataclass\n@dataclass\nclass Unknown:\n    x: int = 1\n")
    sys.path.insert(0, tmp)
    try:
        module = __import__(mod)
        typ, data = JsonPlusSerializer(**PERMISSIVE).dumps_typed(module.Unknown())
    finally:
        sys.path.remove(tmp)
        sys.modules.pop(mod, None)
        shutil.rmtree(tmp, ignore_errors=True)
    for mode in ("permissive", "strict"):
        probe_dir = tempfile.mkdtemp(prefix="sp_markers_")
        res = _subprocess_load(typ, data, mode, here, probe_dir)
        rows.append({"case": "unknown_class", "mode": mode, "trial": trial, "status": "complete",
                     "dumped": True, "loaded": res.get("loaded"), "loaded_type": res.get("loaded_type"),
                     "error_type": res.get("error_type"), "constructed": False, "equal": ""})
        shutil.rmtree(probe_dir, ignore_errors=True)
    # Standard types, in-process (no side effects possible)
    for name, value in STANDARD_VALUES.items():
        for mode, kw in (("permissive", PERMISSIVE), ("strict", STRICT)):
            row = {"case": f"type_{name}", "mode": mode, "trial": trial, "status": "complete",
                   "constructed": "", "dumped": False}
            try:
                typ, data = JsonPlusSerializer(**PERMISSIVE).dumps_typed(value)
                row["dumped"] = True
                obj = JsonPlusSerializer(**kw).loads_typed((typ, data))
                row.update(loaded=True, loaded_type=type(obj).__name__, equal=obj == value)
            except Exception as e:
                row.update(loaded=False, error_type=type(e).__name__, equal=False)
            rows.append(row)
    return rows


def compatibility_trial(config, trial, seed):
    """Real checkpoint state from a paused run, decoded by both modes."""
    base = tempfile.mkdtemp(prefix=f"sp_compat_{config}_")
    rows = []
    try:
        c = harness.canaries(seed)
        harness.install_mcp(c, os.path.join(base, "tx.jsonl"))
        store = ExperimentStore(config, os.path.join(base, "store"))
        thread = f"thread-{seed}"
        with minimization(CONFIGS[config]["minim"]):
            harness.run_to_pause(store, c, thread, os.path.join(base, "logs"))
        tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
        store.close()
        typ, data = JsonPlusSerializer(**PERMISSIVE).dumps_typed(tup.checkpoint)
        reference = json.dumps(tup.checkpoint, sort_keys=True, default=str)
        for mode, kw in (("permissive", PERMISSIVE), ("strict", STRICT)):
            row = {"case": f"checkpoint_state_{config}", "mode": mode, "trial": trial,
                   "status": "complete", "dumped": True, "constructed": ""}
            try:
                obj = JsonPlusSerializer(**kw).loads_typed((typ, data))
                row.update(loaded=True, loaded_type=type(obj).__name__,
                           equal=json.dumps(obj, sort_keys=True, default=str) == reference)
            except Exception as e:
                row.update(loaded=False, error_type=type(e).__name__, equal=False)
            rows.append(row)
    except Exception as e:
        rows.append({"case": f"checkpoint_state_{config}", "mode": "setup", "trial": trial,
                     "status": "failed", "error": f"{type(e).__name__}: {e}"[:300]})
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows
