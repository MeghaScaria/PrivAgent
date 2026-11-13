# Secure persistence evaluation: methodology and reproduction

This directory evaluates four persistence mechanisms of PrivAgent's
human-approval workflow, alone and together, with synthetic data in
isolated temporary directories. Results are in `results/` (raw, one row
per trial), `analysis/output/` (tables) and `analysis/figures/`; the
findings are in `REPORT.md`.

**Status of this study: exploratory.** The frozen pre-registration
(`preregistration.md`, v1.1) describes a different, confirmatory design:
five configurations with the execution ledger always on, gated on
preconditions PC1 (pre-send approved-action digest check) and PC2
(canonical digest encoding), neither of which is implemented. This study
adds two ledger-off configurations (A, F) and runs without PC1 and PC2,
so none of its results are confirmatory evidence under the
pre-registration. The pre-registration file is unchanged.

## Configurations

| ID | Encryption | Strict deserialization | State minimization | Execution ledger |
|---|---|---|---|---|
| A | off | off | off | off |
| B | on | on | on | on |
| C | off | on | on | on |
| D | on | off | on | on |
| E | on | on | off | on |
| F | on | on | on | off |

How each mechanism is switched (`configurations.py`, built only from the
production classes, which are not modified):

| Mechanism | On | Off |
|---|---|---|
| Encryption | `StrictEncryptedSerializer(AesGcmCipher(...))` | the inner serializer alone (plaintext blobs) |
| Strict deserialization | `JsonPlusSerializer(pickle_fallback=False, allowed_msgpack_modules=None)` | the library's permissive default (`allowed_msgpack_modules=True`) |
| State minimization | `minimize_state()` in `writer_compose` | test-only monkeypatch of `minimize_state` with a no-op |
| Execution ledger | `ExecutionLedger` (SQLite, unique action ID) | `NullLedger`: every claim succeeds, nothing is recorded |

Held constant in every configuration: owner-only file permissions (the
same `make_private` call), master-key derivation, exit-only checkpoint
durability, completed-thread purge, the single flow rule, the frozen
risk model and thresholds.

**Independence of the toggles.** All four can be toggled mechanically
without touching another's code. Their effects overlap in documented
ways:

- With encryption on, an injected blob is refused before it is ever
  deserialized, so strict deserialization only matters against an
  attacker who holds the key, or when encryption is off.
- The approval service derives its signing key from the same master key
  as the encryption key. A wrong or missing key therefore also breaks
  the approval digests, even in unencrypted configurations.
- Duplicate sends are also blocked, in some paths, by LangGraph (a resume
  on a finished thread is a no-op), by the resume helper (it refuses when
  nothing is pending) and by purge. Only paths that re-enter the execute
  step show the ledger's effect.
- The ledger's absence breaks no other component: `ApprovalService` only
  needs an object with `claim`, `finish` and `status`.

## Workload and test doubles

- **The workload** (`harness.py`) is the approval-graph pipeline, driven
  by a scripted LLM:
  - it retrieves five synthetic HR documents;
  - the analyst under-reports their sensitivity;
  - the flow rule sends the external transmission for review.
- **Canaries.** Each trial gets unique synthetic sensitive values: a
  requester email in the task; per document an employee email, an
  API-key-like token and an account number; an analysis marker; a
  partner email in the payload. That's 18 values per trial.
- **The synthetic MCP server** replaces the four real MCP subprocesses.
  It serves the documents and records every `send_result` attempt and
  delivery as an fsynced line in a per-trial file, so transmissions are
  counted exactly across processes. MCP protocol and tool latency are
  therefore not part of any measurement.
- **The probe class** (`gadget.py`) stands in for a malicious serialized
  object. Its only side effect is writing a marker file into a temporary
  directory. No commands, no network.

## Experiments

| # | Module | What it does | Trials |
|---|---|---|---|
| 1 | `recovery_experiments.py`, `worker.py` | Separate processes; the pausing process is hard-killed; crashes injected with `os._exit` at fixed points (R1-R5) | 30 per configuration and scenario (900) |
| 2 | `confidentiality_experiments.py` | Canary scan of raw store bytes and decrypted state, at the pause, after completion, after close | 30 per configuration |
| 3 | `encryption_experiments.py` | 7 manipulations of a paused checkpoint, then recovery and an approval attempt; AES-GCM timing | 30 per configuration (x7) |
| 4 | `deserialization_experiments.py`, `probe_worker.py` | Probe object injected into a paused checkpoint and recovered in a separate process; serializer-level cases | 30 per configuration and attacker; 30 per serializer case |
| 5 | `ledger_experiments.py` (+ R5 from 1) | First, repeated, concurrent (double-click), duplicate-resume and rejected approvals | 30 per configuration and scenario |
| 6 | `performance_experiments.py` | Sequential, shuffled order, 5 warm-ups, 40 measured runs per configuration; separate memory pass | 40 (+5) per configuration; 10 memory |

Rules followed:

- Identical workload and payload shape in every configuration.
- Setup (graph build, store open) is timed separately from the measured execution.
- Warm-ups are recorded and flagged.
- Configuration order is shuffled per repetition (performance) and per trial (recovery), with fixed seeds.
- Every trial, including failed ones, is written to CSV.
- Crash-recovery trials run 10 at a time. Their latencies are therefore indicative only; the latency results come from experiment 6, which runs alone.

## Reproduce

From this directory:

```bash
python run_experiments.py --quick
```
```bash
python run_experiments.py --workers 10
```
```bash
python analysis/analyze.py
```

The first is a harness check (n = 2, writes `results/validation/`). The
second is the full run (writes `results/`, about 2 hours on the
reference machine). The third writes the tables and figures.

Seeds: master 20261109 (trial seeds and recovery order), 20261110
(performance order), 20261111 (bootstrap). The environment of each run
is recorded in `results/environment.json`.

Safety: every store is created in a fresh temporary directory and deleted
after the trial. The experiment factory refuses the deployed
`runtime/approvals` path, no real credentials are present in any worker,
and the deployed configuration, frozen models, thresholds and
pre-registration are not touched. A snapshot of the implementation as it
was before this study is in `snapshots/pre_persistence_eval_20261109/`.
