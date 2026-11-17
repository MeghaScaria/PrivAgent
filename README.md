# PrivAgent

PrivAgent is an inspectable research prototype for runtime governance of a multi-agent LLM pipeline.
Four LangGraph agents (orchestrator, retriever, analyst, writer) reach their tools through four FastMCP
stdio servers (document, database, web, external). A single interception point scores every proposed tool
call before it executes. It combines a learned trajectory classifier (gradient boosting), deterministic
policy rules (R1–R3), a configurable decision precedence, provenance-derived sensitivity, optional scoring
of agent-to-agent handoffs, an opt-in human-approval gate, and a hash-chained audit log.

The repository holds the code, data generators, experiments and evidence for two evaluation phases:

- **Phase 1 (exploratory):** offline evaluation on synthetic trajectories and scripted demonstrations.
  It is written up in `research_paper/final/`, which is frozen.
- **Phase 2 (pre-registered, confirmatory):** five hypotheses (H1–H5), frozen before any confirmatory run.
  Ground truth is canary tokens, and an independent agent recomputed the results. It is written up in the
  manuscript draft in `research_paper/v2/`.

The study uses synthetic data only. Its real-LLM pilot used one local 3B-parameter model
(`qwen2.5:3b` on Ollama). This is a research prototype, not a production security product. The
limitations are listed in Section VIII of the manuscript.

## Repository map

| Path | What it is |
|---|---|
| `agents/`, `mcp_servers/`, `governance/`, `main.py` | the pipeline, the MCP servers, and the governance layer |
| `data/generate_trajectories.py` | synthetic trajectory generator (template-based; no personal data) |
| `models/` | trained classifiers (Phase 1 deployed model, frozen) |
| `experiments/v2/` | Phase 2: pre-registration, harnesses, scenarios, task sets, results, analyses, reports |
| `experiments/v2/results/confirmatory/` | raw confirmatory result files (frozen) |
| `experiments/v2/results/confirmatory/analysis/` | outputs of the pre-registered analyses h1–h5 (frozen) |
| `experiments/v2/analysis/` | the pre-registered analysis code (frozen with the pre-registration) |
| `experiments/v2/exploratory/` | analyses that were not pre-registered, labelled EXPLORATORY |
| `research_paper/v2/` | manuscript (Markdown source, LaTeX, figures), supplement, claim–evidence ledger |
| `research_paper/final/` | the Phase 1 paper and its claim–evidence ledger (frozen) |
| `snapshots/`, `research_paper/evidence/` | frozen Phase 1 evidence snapshots and checksums |
| `tests/` | unit and integration tests |
| `dashboard/`, `docs/LIVE_SYSTEM.md` | the interactive Streamlit dashboard and how to run the live system |

## Pre-registration and freeze

- **Pre-registration:** `experiments/v2/PREREGISTRATION_v2.md`. It names the four pre-freeze commits
  that hold the harnesses, runners and analysis code (`adc18b0`, `29b979c`, `984caf9`, `843d157`). It also
  lists five analysis choices fixed in that code.
- **Freeze:** the file was frozen at 2026-11-15T13:25:37Z in commit `7727046`. Its SHA-256 is in
  `experiments/v2/PREREGISTRATION_HASHES.md`.
  - After the freeze, the only change is one dated editorial amendment, appended at the end.
  - The file's first bytes, up to the frozen length, still hash to the frozen value.
- **Verifying the freeze:**

  ```bash
  git show 7727046:experiments/v2/PREREGISTRATION_v2.md | sha256sum
  # expected: 846374a77d92b82e617be8ddd1ba8d60b2e898b9978d5d8351725f4076c705ac
  ```

- **Run log:** `experiments/v2/CONFIRMATORY_REPORT.md` records the order, times, exit codes and commits of
  the confirmatory steps. It also records that none failed or was rerun. A dated erratum at its end
  corrects one observation and three denominators.
- **Independent check:** `experiments/v2/INDEPENDENT_CHECK.md` is the independent recomputation. It
  was made from the raw result files and the pre-registration only, without reading the analysis code.

## Reproducing the results

Every number in the manuscript cites a row of the claim–evidence ledger,
`research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md`. Each row names the artifact that holds the number, the
commit that produced it, and how it was verified.

- **Number → ledger row:** Supplementary S11 maps each manuscript section to its rows. S11 replaces the
  draft's former Appendix B.
- **Phase 1 commands:** Appendix A of `research_paper/final/PrivAgent_Research_Paper_Final.md` maps each
  Phase 1 experiment to its script and output.

### Setup

```bash
pip install -r requirements.txt
```

The real-LLM pilot also needs Ollama with `qwen2.5:3b`. The harness checks the model's name and digest.

### Recompute the confirmatory analyses from the committed result files (no LLM calls)

The analysis scripts write into the frozen `analysis/` directory by default. Always pass `--out` to
write somewhere else:

```bash
python experiments/v2/analysis/h1.py --out /tmp/privagent/h1
python experiments/v2/analysis/h2.py --out /tmp/privagent/h2
python experiments/v2/analysis/h3.py --out /tmp/privagent/h3
python experiments/v2/analysis/h4.py --out /tmp/privagent/h4
python experiments/v2/analysis/h5.py --out /tmp/privagent/h5
```

Compare the outputs with `experiments/v2/results/confirmatory/analysis/h1.json` … `h5.json`. The
exploratory analyses (reviewer sweep, H4(b) without the send step) come from:

```bash
python experiments/v2/exploratory/exploratory_v2.py
```

The figures come from:

```bash
python research_paper/v2/figures/make_figures_v2.py
python research_paper/v2/figures/make_architecture_v2.py
```

### Re-run the experiments

These commands regenerate raw results. Each confirmatory mode writes into
`experiments/v2/results/confirmatory/`, so run them on a copy of the repository to keep the committed
files intact.

| Step (pre-registered order) | Command | Ledger rows |
|---|---|---|
| 1. Precedence ablation and multi-seed evaluation (offline, H1) | `python experiments/v2/precedence_ablation.py --confirmatory` and `python experiments/v2/multiseed_eval.py --confirmatory` | C1, C3, C5, C19, C20 |
| 2. Graph scenarios, confirmatory half (H1-live, H2, H3) | `python experiments/v2/wp4_confirmatory.py --half confirmatory` | C2, C4, C7–C11 |
| 3a. Real-LLM pilot, family B (H4, H5) | `LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:3b python experiments/v2/real_llm_pilot.py --confirmatory familyB` | C12–C17, C24 |
| 3b. Real-LLM pilot, benign tasks | `LLM_BACKEND=ollama OLLAMA_MODEL=qwen2.5:3b python experiments/v2/real_llm_pilot.py --confirmatory benign` | C18 |
| 4. Analyses | the h1–h5 commands above | all C rows |

- **Exact invocations:** check each script's docstring before running it. The run log in
  `CONFIRMATORY_REPORT.md` is the record of what was actually run.
- **Determinism:** the graph scenarios (step 2) are deterministic.
- **Pilot timing:** the two pilot parts took about 14 hours (run log in `CONFIRMATORY_REPORT.md`). LLM outputs may differ between machines
  and Ollama versions.

### Tests

Each test file runs as a module, for example:

```bash
python -m tests.test_canary_v2
```

### The manuscript

- **Markdown:** `research_paper/v2/build/manuscript_src.md` is the source.
  `python research_paper/v2/build/build_manuscript.py` renders `PrivAgent_v2_DRAFT.md`, and
  `python research_paper/v2/build/make_supplementary.py` renders `SUPPLEMENTARY.md`.
- **LaTeX:** `python research_paper/v2/build/make_latex.py` writes `research_paper/v2/latex/`. That
  directory holds the `.tex` files, the `.bib` file and the figures.
- **Template:** the IEEE Access class and font files are not part of this repository. Download the
  IEEE Access LaTeX template from IEEE and put it in `research_paper/v2/template/`.

## Licence

- **Code** (all source files, scripts, tests and build tools) is released under the MIT License; see
  `LICENSE`.
- **Data, results and text** are released under Creative Commons Attribution 4.0 International
  (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/. This covers the synthetic data, the
  experiment results and logs, the trained models, the figures, the reports, the ledgers, the
  pre-registration and the manuscript text.
- **Third-party material** keeps its own licence. The IEEE Access template is not included.

## Citation

See `CITATION.cff`. The manuscript is in preparation and has not been peer reviewed.
