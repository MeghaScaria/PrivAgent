"""
A harmless stand-in for a malicious serialized object. Building it has
exactly one side effect: it writes a marker file into the directory named
by PRIVAGENT_PROBE_DIR (and does nothing if that isn't set). No commands,
no network.
"""
import os
import uuid
from dataclasses import dataclass


@dataclass
class SideEffectProbe:
    label: str = "probe"

    def __post_init__(self):
        directory = os.environ.get("PRIVAGENT_PROBE_DIR")
        if directory and os.path.isdir(directory):
            path = os.path.join(directory, f"constructed-{os.getpid()}-{uuid.uuid4().hex}.marker")
            with open(path, "w") as f:
                f.write(self.label)
