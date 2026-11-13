"""
Recovers a paused thread from a store whose checkpoint may hold a probe
object, in its own process, and reports what happened. The probe's only
side effect is a marker file in PRIVAGENT_PROBE_DIR.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: E402

from agents.approval_flow import pending_review  # noqa: E402
from configurations import CONFIGS, ExperimentStore  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, choices=sorted(CONFIGS))
    p.add_argument("--dir", required=True)
    p.add_argument("--thread", required=True)
    args = p.parse_args()
    store = ExperimentStore(args.config, args.dir)
    out = {"event": "probe_load", "loaded": False, "error_type": "", "final_output_type": ""}
    try:
        tup = store.checkpointer.get_tuple({"configurable": {"thread_id": args.thread}})
        out["loaded"] = tup is not None
        if tup is not None:
            out["final_output_type"] = type(tup.checkpoint["channel_values"].get("final_output")).__name__
            pending_review(harness.build_app(store, "probe", os.path.join(args.dir, "logs")), args.thread)
    except Exception as e:
        out["error_type"] = type(e).__name__
    finally:
        store.close()
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
