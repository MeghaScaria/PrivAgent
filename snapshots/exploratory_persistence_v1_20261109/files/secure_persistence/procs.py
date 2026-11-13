"""Running worker processes and collecting their JSON event lines."""
import json
import os
import queue
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 180


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ("PRIVAGENT_MASTER_KEY", "GOOGLE_API_KEY")}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class Proc:
    def __init__(self, script, *args, extra_env=None):
        env = _env()
        env.update(extra_env or {})
        self.p = subprocess.Popen([sys.executable, os.path.join(HERE, script), *args],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, cwd=HERE, env=env)
        self.q = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.p.stdout:
            line = line.strip()
            if line.startswith("{"):
                try:
                    self.q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        self.q.put(None)

    def next_event(self, timeout=TIMEOUT):
        return self.q.get(timeout=timeout)

    def finish(self, timeout=TIMEOUT):
        events = []
        while True:
            e = self.q.get(timeout=timeout)
            if e is None:
                break
            events.append(e)
        self.p.wait(timeout=timeout)
        return events, self.p.returncode

    def kill(self):
        self.p.kill()
        self.p.wait(timeout=TIMEOUT)
        return self.p.returncode


def run(script, *args, extra_env=None):
    proc = Proc(script, *args, extra_env=extra_env)
    return proc.finish()
