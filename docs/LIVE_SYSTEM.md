# PrivAgent

A working multi-agent AI research assistant where LangGraph agents
collaborate through real MCP servers, with every tool call governed
live by trained risk models. Open the dashboard, ask a question, and
watch the agents retrieve information while the governance layer
scores and decides on each action in real time.

This is the live-system counterpart to the PrivAgent research paper
(trajectory-aware runtime governance for MCP-based multi-agent
systems) -- the risk models here are the same ones trained and
evaluated in that work.

---

## What's actually running

- **4 real MCP servers** (`mcp_servers/`) using stdio transport --
  document search, structured database queries, web search, and an
  external transmission endpoint. Each was tested directly through the
  MCP protocol (tool listing + tool calls), not just "does it start."
- **4 LangGraph agents** (`agents/orchestrator.py`, `retriever.py`,
  `analyst.py`, `writer.py`) that plan, retrieve, synthesise, and write
  the final answer, calling Gemini for reasoning.
- **A governance layer** (`governance/`) that intercepts every proposed
  tool call before it reaches an MCP server: a trained gradient-boosted
  risk model scores it, a deterministic policy engine can override that
  score with hard rules, and every decision is written to an audit log.
- **A Streamlit dashboard** (`dashboard/`) with three pages: a live
  research assistant, a trajectory viewer for any past run, and an
  attack laboratory that replays known attack patterns against the real
  pipeline with no API key required.

Everything above has been run and tested in a sandbox before being
handed to you -- including actually connecting to all four MCP servers
over the real protocol, running the full LangGraph pipeline end to end,
and clicking through all three dashboard pages via Streamlit's own
`AppTest` framework to confirm nothing throws.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Tested clean in a fresh virtual environment with these exact versions.

### 2. Train the risk models

```bash
python models/train_models.py
```

This generates the synthetic training data and trains both risk
models (takes a few minutes). Attack templates are embedded at random
positions inside benign runs, with random gaps between stages, so the
model can't learn *when* attacks happen. Data is split 60/20/20 by run
(never by row), thresholds are tuned on the validation runs only, and
both models are also scored on two held-out sets: three attack types
never seen in training, and tool-swapped variants of the training
attacks. You'll see output like:

```
Training trajectory_level model (trajectory_invariant)...
  Thresholds (tuned on val): {'autonomous_max': 0.22, 'restricted_max': 0.5, 'approval_max': 0.85}
  test: {'precision': 0.88, 'recall': 0.94, 'f1': 0.91, 'fpr': 0.008, ...}
  holdout_types: {'precision': 0.86, 'recall': 0.54, 'f1': 0.66, ...}
  holdout_variants: {'precision': 0.86, 'recall': 0.35, 'f1': 0.49, ...}
Models saved to models/
```

The held-out numbers are the meaningful ones. Full results are in
`models/training_metrics.json`.

Features are computed by one shared module (`governance/features.py`)
in both training and live scoring, and the feature list each model was
trained on is saved in `models/feature_config.json`;
`tests/test_feature_consistency.py` checks that live scores match the
training rows exactly.

### Experiments

```bash
python experiments/position_ablation.py
python experiments/attack_lab_replay.py
```

The first compares feature sets and checks for positional shortcuts;
the second replays the Attack Lab against the real MCP servers, with
and without the policy engine. Results go to `experiments/results/`.

**Models are already trained and included in this zip** -- you only
need to rerun this if you delete `models/*.pkl` or want fresh ones.

### 3. Add your Gemini API key

```bash
cp .env.example .env
```

Edit `.env` and add a free key from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)
(free tier: 15 requests/minute, no cost).

You only need this for the **Research Assistant** page. The **Attack
Laboratory** page works with no key at all, since it doesn't call an
LLM.

### 4. Run it

```bash
python main.py
```

This opens the dashboard at `http://localhost:8501`. The four MCP
servers start automatically on first page load (takes 1-2 seconds).

---

## The three dashboard pages

### Research Assistant
Ask a question in plain English. The orchestrator classifies it and
builds a retrieval plan, the retriever executes that plan through
governed MCP calls, the analyst synthesises what came back, and the
writer produces the final answer -- optionally transmitting it
externally if the task asked for that, which is exactly the point
where governance is most likely to intervene. You'll see every agent's
activity and every governance decision live as the run progresses.

### Trajectory Viewer
Every governed action from every run (Research Assistant or Attack
Lab), read from the on-disk audit log. Pick a run ID and see its full
decision trail: which tool, what risk score, which of the four
autonomy levels it landed on, and why.

### Attack Laboratory
Replays nine attack patterns -- the same ones the risk models were
trained and evaluated on -- as real governed tool calls against the
real MCP servers, live, step by step. No API key needed.

**One honest note:** one of the nine scenarios,
`path_cross_agent_leak`, was deliberately **held out entirely from
training** in the original research (used only to test generalisation
to attack types the model has never seen). The paper itself reports
imperfect, not perfect, generalisation on held-out attacks. The
dashboard labels this scenario accordingly -- it is not guaranteed to
be blocked, and that's the honest, faithful behaviour of the actual
trained model, not a bug. The other eight scenarios use attack
families the model was trained on or evaluated against directly, and
should be caught reliably.

---

## Architecture notes

### Why the MCP servers use stdio, not HTTP

MCP supports multiple transports. This project uses **stdio**: the
client (`agents/mcp_client.py`) spawns each server as a subprocess and
talks to it over stdin/stdout. That's simpler and faster for a
single-machine deployment than running an HTTP/SSE transport, but it
does mean the four "servers" are subprocesses of the main app, not
independently addressable network services.

**This is also why `docker-compose.yml` defines one service, not
five.** A docker-compose file with five separate MCP containers would
only make sense if the servers spoke HTTP/SSE to each other over the
network -- with stdio transport, splitting them into separate
containers isn't possible without rewriting the transport layer. One
service starts everything, exactly as `python main.py` does locally.

### Why the MCP client runs in a background thread

MCP client sessions are bound to the asyncio event loop they were
created in. Streamlit's execution model is synchronous. `mcp_client.py`
resolves this by running one persistent background thread with its own
event loop, hosting all four server connections, with a synchronous
`call_tool()` that dispatches into that loop and blocks for the
result. This was tested directly: connecting, then making five
sequential calls across all four servers in a single Python process,
confirming the connections stay stable across repeated use.

### A real bug that was caught and fixed during testing

FastMCP (the library the servers are built on) serialises a returned
Python list as **one content block per item**, not one JSON array --
and an empty list becomes **zero blocks**. The first version of the
MCP client only read the first content block, silently dropping every
result past the first. This was caught by actually inspecting the raw
MCP protocol response (not just checking "did the call succeed"), and
`mcp_client.py` now reconstructs the original list correctly by
tool name.

### Governance: two layers, not one

Every proposed action passes through both:
1. **The trained risk model** (`governance/risk_engine.py`) -- a
   gradient-boosted classifier scoring the action in context.
2. **A deterministic policy engine** (`governance/policy_engine.py`) --
   hard rules that fire regardless of what the ML model says (e.g.
   "never allow external transmission after 2+ sensitive reads in this
   task"). If a policy rule fires, it overrides the ML decision.

Both layers write to the same audit log
(`governance/audit_logger.py`), and the dashboard shows you which
layer made each decision.

---

## Project structure

```
privagent_live/
    mcp_servers/              4 MCP servers (document, database, web, external)
    agents/
        state.py               shared LangGraph state
        mcp_client.py           persistent MCP client (background event loop)
        tools.py                governed tool wrappers
        llm.py                  Gemini client wrapper
        orchestrator.py         plans the retrieval
        retriever.py             executes the plan via governed tools
        analyst.py                synthesises retrieved content
        writer.py                  final answer + optional external send
        graph.py                    LangGraph wiring
    governance/
        risk_engine.py          trained risk models -> risk score
        policy_engine.py         deterministic hard rules
        trajectory_monitor.py     the interceptor tying it together
        audit_logger.py            append-only decision log
        attack_scenarios.py         the 9 replayable attack patterns
    dashboard/
        app.py                    entry point + sidebar nav
        theme.py                   dark, dual-tone visual system
        components.py               shared UI fragments
        page_research.py             Page 1
        page_trajectory.py           Page 2
        page_attack_lab.py            Page 3
    data/generate_trajectories.py   synthetic training data generator
    models/train_models.py            trains + saves the risk models
    models/*.pkl, thresholds.json       already-trained models (included)
    main.py                    single entry point
    docker-compose.yml, Dockerfile
    requirements.txt, .env.example
```

---

## Troubleshooting

**"GOOGLE_API_KEY is not set"** -- you haven't copied `.env.example` to
`.env` and added a key, or you're on the Attack Lab page (which doesn't
need one -- this warning only appears on the Research Assistant page).

**MCP servers fail to start** -- run `python mcp_servers/document_server/server.py`
directly and check for a Python error; all four use the same `mcp<2`
package pinned in `requirements.txt`.

**Models missing** -- run `python models/train_models.py`. `main.py`
checks for this and tells you if they're missing before it tries to
start the dashboard.
# -PrivAgent_project
