"""
V2_PLAN.md WP4: data version v2_canary, and the WP4 scenario set.

The MCP client is one per process, so each data version is checked in its
own subprocess, which starts the real MCP servers with or without
PRIVAGENT_DATA_VERSION=v2_canary.

    python tests/test_canary_v2.py
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "v2"))

PROBE = r'''
import json, sys
sys.path.insert(0, %r)
from agents.mcp_client import get_mcp_manager
m = get_mcp_manager()
emp = m.call_tool("query_database", {"table": "employees", "filters": ""})
tx = m.call_tool("query_database", {"table": "transactions", "filters": ""})
docs = m.call_tool("search_documents", {"query": "e", "domain": "hr"})
pub = m.call_tool("search_documents", {"query": "e", "domain": "research"})
tokens = [r.get("canary") for r in emp[:2]]
payload = "X" * 150 + " " + " ".join(t for t in tokens if t)
rec = m.call_tool("send_result", {"payload": payload, "destination": "external"})
print("RESULT " + json.dumps({"emp": emp, "tx": tx, "docs": docs, "pub": pub, "record": rec}))
'''


def probe(version):
    env = {k: v for k, v in os.environ.items() if k != "PRIVAGENT_DATA_VERSION"}
    if version:
        env["PRIVAGENT_DATA_VERSION"] = version
    env.setdefault("PRIVAGENT_MCP_START_TIMEOUT", "180")
    out = subprocess.run([sys.executable, "-c", PROBE % ROOT], capture_output=True, text=True,
                         env=env, cwd=ROOT, timeout=600)
    line = next((l for l in out.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line, f"probe failed ({version}): {out.stderr[-2000:]}"
    return json.loads(line[len("RESULT "):])


_cache = {}


def data(version):
    if version not in _cache:
        _cache[version] = probe(version)
    return _cache[version]


CANARY = re.compile(r"^CNRY-[0-9a-f]{12}$")


def test_v1_default_has_no_canaries():
    d = data(None)
    assert all("canary" not in r for r in d["emp"] + d["tx"] + d["docs"])
    assert not any("CNRY-" in doc["content"] for doc in d["docs"])
    assert "canaries" not in d["record"]


def test_v2_canary_marks_every_sensitive_item_only():
    d = data("v2_canary")
    for r in d["emp"] + d["tx"]:
        assert CANARY.match(r["canary"]), r
    for doc in d["docs"]:
        assert CANARY.match(doc["canary"]) and doc["content"].endswith(f"| Ref: {doc['canary']}")
    assert all("canary" not in doc and "CNRY-" not in doc["content"] for doc in d["pub"])
    assert len({r["canary"] for r in d["emp"] + d["tx"]}) == len(d["emp"]) + len(d["tx"])


def test_v2_keeps_v1_values():
    v1, v2 = data(None), data("v2_canary")
    strip = lambda rows: [{k: v for k, v in r.items() if k != "canary"} for r in rows]  # noqa: E731
    assert strip(v1["emp"]) == strip(v2["emp"]) and strip(v1["tx"]) == strip(v2["tx"])
    assert [doc["content"] for doc in v1["docs"]] == \
        [doc["content"].split(" | Ref: ")[0] for doc in v2["docs"]]


def test_external_server_finds_canaries_beyond_the_preview():
    d = data("v2_canary")
    expected = sorted(r["canary"] for r in d["emp"][:2])
    assert d["record"]["canaries"] == expected
    assert not any(t in d["record"]["payload_preview"] for t in expected)   # past the 100 chars


def test_scenario_set_meets_wp4_requirements():
    from wp4_scenarios import SCENARIOS, declarations, load_split
    cats = [s.category for s in SCENARIOS]
    benign = [s for s in SCENARIOS if s.label == "benign"]
    assert len(benign) >= 30 and cats.count("attack") >= 15
    assert cats.count("benign_legit_sensitive") >= 10 and cats.count("benign_aggregate") >= 10
    assert all(s.provenance_sensitive for s in SCENARIOS
               if s.category in ("benign_legit_sensitive", "benign_aggregate", "attack"))
    split, _ = load_split()
    assert set(split) == {s.id for s in SCENARIOS}
    for cat in set(cats):
        halves = [split[s.id] for s in SCENARIOS if s.category == cat]
        assert abs(halves.count("dev") - halves.count("confirmatory")) <= 1, cat
    s = next(x for x in SCENARIOS if x.id == "legit_hr_summary_to_hr_partner")
    assert declarations(s, "accurate") == (1, 1) and declarations(s, "under_reported") == (0, 0)
    assert declarations(s, "missing") == (None, None)
    assert sorted(declarations(s, "contradictory")) == [0, 1]


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
