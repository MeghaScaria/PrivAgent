"""Locating and loading the WP6 pilot traces for h4.py and h5.py."""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import load_jsonl  # noqa: E402

CONF = os.path.join(os.path.dirname(HERE), "results", "confirmatory")
PATTERNS = {"familyB": "pilot_ollama_qwen2.5-3b_familyB_*.jsonl",
            "benign": "pilot_ollama_qwen2.5-3b_benign_*.jsonl"}


def default_traces():
    """Exactly one confirmatory trace per part; anything else is an error
    (never a silent choice between reruns)."""
    paths = []
    for part, pattern in PATTERNS.items():
        found = sorted(glob.glob(os.path.join(CONF, pattern)))
        if len(found) != 1:
            sys.exit(f"Expected exactly one confirmatory {part} trace ({pattern}) in {CONF}, found {len(found)}.")
        paths += found
    return paths


def load(paths):
    rows = []
    for p in paths:
        for r in load_jsonl(p):
            r["_file"] = os.path.basename(p)
            rows.append(r)
    return rows
