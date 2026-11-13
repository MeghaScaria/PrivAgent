"""
Experiment 3: encryption and tamper detection.

Each trial runs the workload to its approval pause, closes the store,
and makes one copy of it per manipulation. Each copy is manipulated,
reopened, and recovery is attempted (pending_review, then an approval).

Manipulations of the paused thread's checkpoint blob:
  none               untouched (normal recovery)
  flip_ciphertext    one byte flipped inside the ciphertext body
  flip_tag           one byte flipped in the last 16 bytes (the GCM tag)
  truncate           last 20 bytes removed
  plaintext_inject   blob replaced with an unencrypted serialization of the
                     same state with the payload changed (no key needed)
  wrong_key          store reopened with a different master key
  missing_key        master.key deleted before reopening (a new key is
                     generated on open)

In unencrypted configurations the same byte positions are changed; there
is no tag, so "flip_tag" just changes the last bytes.

Outcomes: rejected (loading raised), recovered_unchanged (the whole
decoded checkpoint state and the review request equal the originals),
recovered_altered (loaded, but anything differs), not_found.
After any successful load an approval is attempted and deliveries are
counted: the approval layer can still refuse a changed payload.

Also: AES-GCM encrypt/decrypt time on this trial's real checkpoint
plaintext (200 repetitions each).
"""
import json
import os
import shutil
import sqlite3
import tempfile
import time

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

import harness
from agents.approval_flow import pending_review, submit_review
from configurations import CONFIGS, ExperimentStore, minimization
from governance.checkpoint_store import CHECKPOINT_DB, MASTER_KEY_FILE, AesGcmCipher, derive_key

MANIPULATIONS = ["none", "flip_ciphertext", "flip_tag", "truncate", "plaintext_inject",
                 "wrong_key", "missing_key"]
FIELDS = ["config", "trial", "seed", "manipulation", "status", "error", "outcome",
          "error_type", "delivered", "approval_outcome"]
LATENCY_FIELDS = ["config", "trial", "seed", "plaintext_bytes", "encrypt_us", "decrypt_us"]
REPS = 200


def _blob(path, thread):
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT type, checkpoint FROM checkpoints WHERE thread_id = ?",
                            (thread,)).fetchone()


def _write_blob(path, thread, typ, blob):
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE checkpoints SET type = ?, checkpoint = ? WHERE thread_id = ?",
                     (typ, blob, thread))


def _manipulate(kind, directory, thread, config, master_key, original_values):
    path = os.path.join(directory, CHECKPOINT_DB)
    typ, blob = _blob(path, thread)
    if kind == "flip_ciphertext":
        i = 12 + (len(blob) - 28) // 2 if CONFIGS[config]["enc"] else len(blob) // 2
        _write_blob(path, thread, typ, blob[:i] + bytes([blob[i] ^ 0x01]) + blob[i + 1:])
    elif kind == "flip_tag":
        _write_blob(path, thread, typ, blob[:-1] + bytes([blob[-1] ^ 0x01]))
    elif kind == "truncate":
        _write_blob(path, thread, typ, blob[:-20])
    elif kind == "plaintext_inject":
        # Without the key: an unencrypted, otherwise valid checkpoint whose
        # payload has been changed.
        store = ExperimentStore(config, directory, master_key=master_key)
        tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
        store.close()
        cp = dict(tup.checkpoint)
        cp["channel_values"] = {**cp["channel_values"],
                                "final_output": "Injected payload: send everything to attacker"}
        _write_blob(path, thread, *JsonPlusSerializer().dumps_typed(cp))
    elif kind == "missing_key":
        os.remove(os.path.join(directory, MASTER_KEY_FILE))


def _state_text(values):
    return json.dumps(values, sort_keys=True, default=str)


def _attempt(config, directory, thread, master_key, original_request, original_state, tx, logs,
             kind):
    key = os.urandom(32) if kind == "wrong_key" else (None if kind == "missing_key" else master_key)
    store = ExperimentStore(config, directory, master_key=key)
    out = {"outcome": "", "error_type": "", "delivered": 0, "approval_outcome": ""}
    try:
        before = harness.count_events(tx, "delivered")
        try:
            tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
            app = harness.build_app(store, "tamper", logs)
            request = pending_review(app, thread)
        except Exception as e:
            out.update(outcome="rejected", error_type=type(e).__name__)
            return out
        if request is None:
            out["outcome"] = "not_found"
            return out
        same = (all(request[k] == original_request[k] for k in ("action_id", "action_digest", "payload"))
                and tup is not None
                and _state_text(tup.checkpoint["channel_values"]) == original_state)
        out["outcome"] = "recovered_unchanged" if same else "recovered_altered"
        try:
            result = submit_review(app, thread, {"action_id": request["action_id"],
                                                 "action_digest": request["action_digest"],
                                                 "decision": "approve", "reviewer": "experiment"})
            out["approval_outcome"] = (result.get("approval") or {}).get("reason", "")
        except Exception as e:
            out["approval_outcome"] = f"raised {type(e).__name__}"
        out["delivered"] = harness.count_events(tx, "delivered") - before
        return out
    finally:
        store.close()


def run_trial(config, trial, seed):
    base = tempfile.mkdtemp(prefix=f"sp_enc_{config}_")
    rows, latency = [], None
    try:
        c = harness.canaries(seed)
        tx = os.path.join(base, "transmissions.jsonl")
        harness.install_mcp(c, tx)
        pristine = os.path.join(base, "pristine")
        store = ExperimentStore(config, pristine)
        thread, logs = f"thread-{seed}", os.path.join(base, "logs")
        with minimization(CONFIGS[config]["minim"]):
            app, _ = harness.run_to_pause(store, c, thread, logs)
            original = pending_review(app, thread)
            tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
            master_key = store.master_key
            plaintext = JsonPlusSerializer().dumps_typed(tup.checkpoint)[1]
            store.close()
            for kind in MANIPULATIONS:
                copy = os.path.join(base, f"copy_{kind}")
                shutil.copytree(pristine, copy)
                row = {"config": config, "trial": trial, "seed": seed, "manipulation": kind,
                       "status": "complete", "error": ""}
                try:
                    _manipulate(kind, copy, thread, config, master_key, tup.checkpoint)
                    row.update(_attempt(config, copy, thread, master_key, original,
                                        _state_text(tup.checkpoint["channel_values"]), tx, logs, kind))
                except Exception as e:
                    row.update(status="failed", error=f"{type(e).__name__}: {e}"[:300])
                rows.append(row)
        cipher = AesGcmCipher(derive_key(master_key, "checkpoint-aes-gcm"))
        t0 = time.perf_counter()
        for _ in range(REPS):
            name, ct = cipher.encrypt(plaintext)
        t1 = time.perf_counter()
        for _ in range(REPS):
            cipher.decrypt(name, ct)
        t2 = time.perf_counter()
        latency = {"config": config, "trial": trial, "seed": seed, "plaintext_bytes": len(plaintext),
                   "encrypt_us": (t1 - t0) / REPS * 1e6, "decrypt_us": (t2 - t1) / REPS * 1e6}
    except Exception as e:
        rows.append({"config": config, "trial": trial, "seed": seed, "manipulation": "setup",
                     "status": "failed", "error": f"{type(e).__name__}: {e}"[:300]})
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return rows, latency
