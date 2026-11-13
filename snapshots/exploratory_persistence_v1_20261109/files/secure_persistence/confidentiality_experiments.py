"""
Experiment 2: checkpoint confidentiality and data minimization.

Each trial seeds the workload with unique synthetic canaries (requester
email in the task; employee emails, API-key-like tokens and account
numbers in the documents; an analysis marker; a partner email in the
payload), runs it to the approval pause, and inspects the store at
three moments:

  pending        paused for approval, connection open (WAL present), as
                 after a crash
  completed      approved, sent and purged, connection still open
  closed         after the connection is closed (WAL checkpointed)

For each it records file sizes, stored blob bytes, and canary hits:
  raw       exact canary strings found in the bytes of the database,
            WAL, SHM and ledger files (an attacker reading files, no key)
  decrypted canaries found in the loaded checkpoint state and pending
            writes (an attacker with the key, or an insider)

A string scan can show that a value IS present; finding nothing doesn't
prove it's absent in a transformed form (compressed, split, encoded),
and it says nothing about memory, logs outside the store, or the OS.
"""
import json
import os
import shutil
import sqlite3
import tempfile

from agents.approval_flow import pending_review, submit_review

import harness
from configurations import CONFIGS, ExperimentStore, minimization, store_files

CLASSES = ["task_email", "doc_email", "api_key", "account", "analysis", "payload_email"]
STATE_FIELDS = ["task", "plan", "retrieved_documents", "retrieved_records", "web_results",
                "analysis", "final_output", "messages", "pending_action", "approval"]


def _file_bytes(directory):
    data, sizes = b"", {}
    for path in store_files(directory):
        with open(path, "rb") as f:
            blob = f.read()
        data += blob
        sizes[os.path.basename(path)] = len(blob)
    return data, sizes


def _blob_bytes(checkpoint_path):
    with sqlite3.connect(checkpoint_path) as conn:
        cp = conn.execute("SELECT COALESCE(SUM(LENGTH(checkpoint)), 0), COUNT(*) FROM checkpoints").fetchone()
        wr = conn.execute("SELECT COALESCE(SUM(LENGTH(value)), 0), COUNT(*) FROM writes").fetchone()
    return cp[0] + wr[0], cp[1] + wr[1]


def _raw_hits(data, c):
    return {cls: sum(1 for v in c["values"][cls] if v.encode("utf-8") in data) for cls in CLASSES}


def _decrypted(store, thread):
    tup = store.checkpointer.get_tuple({"configurable": {"thread_id": thread}})
    if tup is None:
        return None, []
    return tup.checkpoint["channel_values"], tup.pending_writes or []


def _decrypted_hits(values, writes, c):
    text = json.dumps(values, default=str) + json.dumps([w[2] for w in writes], default=str)
    hits = {cls: sum(1 for v in c["values"][cls] if v in text) for cls in CLASSES}
    fields = [f for f in STATE_FIELDS
              if any(v in json.dumps(values.get(f), default=str) for _, v in harness.all_canary_values(c))]
    if any(v in json.dumps([w[2] for w in writes], default=str) for _, v in harness.all_canary_values(c)):
        fields.append("interrupt_request")
    return hits, fields


def _record(row, phase, store, directory, thread, c):
    data, sizes = _file_bytes(directory)
    blob, rows = _blob_bytes(store.checkpoint_path)
    row[f"{phase}_file_bytes"] = sum(sizes.get(n, 0) for n in sizes if n.startswith("checkpoints"))
    row[f"{phase}_wal_bytes"] = sizes.get("checkpoints.sqlite-wal", 0)
    row[f"{phase}_blob_bytes"] = blob
    row[f"{phase}_rows"] = rows
    raw = _raw_hits(data, c)
    for cls in CLASSES:
        row[f"{phase}_raw_{cls}"] = raw[cls]
    row[f"{phase}_raw_total"] = sum(raw.values())
    if phase != "closed":
        values, writes = _decrypted(store, thread)
        if values is None:
            row[f"{phase}_dec_total"], row[f"{phase}_fields_retained"] = 0, ""
            row[f"{phase}_fields_count"] = 0
            for cls in CLASSES:
                row[f"{phase}_dec_{cls}"] = 0
        else:
            dec, fields = _decrypted_hits(values, writes, c)
            for cls in CLASSES:
                row[f"{phase}_dec_{cls}"] = dec[cls]
            row[f"{phase}_dec_total"] = sum(dec.values())
            row[f"{phase}_fields_retained"] = ";".join(fields)
            row[f"{phase}_fields_count"] = len(fields)


def run_trial(config, trial, seed):
    base = tempfile.mkdtemp(prefix=f"sp_conf_{config}_")
    row = {"config": config, "trial": trial, "seed": seed, "status": "complete", "error": "",
           "canaries_total": 0}
    store = None
    try:
        c = harness.canaries(seed)
        row["canaries_total"] = len(harness.all_canary_values(c))
        harness.install_mcp(c, os.path.join(base, "transmissions.jsonl"))
        directory = os.path.join(base, "store")
        store = ExperimentStore(config, directory)
        thread, logs = f"thread-{seed}", os.path.join(base, "logs")
        with minimization(CONFIGS[config]["minim"]):
            app, result = harness.run_to_pause(store, c, thread, logs)
            row["paused"] = "__interrupt__" in result
            _record(row, "pending", store, directory, thread, c)
            request = pending_review(app, thread)
            submit_review(app, thread, {"action_id": request["action_id"],
                                        "action_digest": request["action_digest"],
                                        "decision": "approve", "reviewer": "experiment"})
            _record(row, "completed", store, directory, thread, c)
        store.close()
        store = None
        _record_closed(row, directory, c)
    except Exception as e:
        row["status"] = "failed"
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        if store is not None:
            store.close()
        shutil.rmtree(base, ignore_errors=True)
    return row


def _record_closed(row, directory, c):
    data, sizes = _file_bytes(directory)
    row["closed_file_bytes"] = sum(v for n, v in sizes.items() if n.startswith("checkpoints"))
    row["closed_wal_bytes"] = sizes.get("checkpoints.sqlite-wal", 0)
    raw = _raw_hits(data, c)
    for cls in CLASSES:
        row[f"closed_raw_{cls}"] = raw[cls]
    row["closed_raw_total"] = sum(raw.values())
