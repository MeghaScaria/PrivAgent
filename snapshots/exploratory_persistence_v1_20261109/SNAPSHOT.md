# Frozen copy: exploratory secure-persistence study v1 (2026-11-09)

This is an immutable copy of the exploratory study as it stood after its full run and report.

Treat this directory as read-only:

- Do not edit, regenerate or re-run anything in it.
- Corrections to the exploratory results are recorded separately in `experiments/secure_persistence/CORRECTIONS.md`.

## Contents

| Path | What it is |
|---|---|
| `files/secure_persistence/` | full copy of `experiments/secure_persistence/` (`__pycache__` excluded) |
| `files/pre_persistence_eval_MANIFEST.sha256` | the original SHA-256 manifest of the implementation before the study |
| `files/pre_persistence_eval_SNAPSHOT.md` | that snapshot's description |
| `MANIFEST.sha256` | SHA-256 of every file under `files/` (84 files) |
| `exploratory_v1.tar.gz` | archive of `files/` |

The study copy under `files/secure_persistence/` contains:

- **Code:** the six experiment modules, `configurations.py`, `harness.py`, `worker.py`, `probe_worker.py`, `procs.py`, `gadget.py`, `run_experiments.py`, `analysis/analyze.py`.
- **Raw data:** `results/*.csv` (9 files), `results/environment.json`, `results/run_log.txt`; validation run in `results/validation/`.
- **Analysis:** generated tables in `analysis/output/`; figures `analysis/figures/fig1`–`fig6`.
- **Documents:** `REPORT.md` and `README.md` as delivered; `preregistration.md` v1.1, unchanged.

## Integrity

The archive's SHA-256:

```
da46f42d925f5ba160a1017345b5e71acc418959d7f2ee03e5a1a4695589ff33  exploratory_v1.tar.gz
```

To verify the copy, from this directory:

```bash
tr -d '\r' < MANIFEST.sha256 > /tmp/m && (cd files && sha256sum -c /tmp/m)
```

## Notes

**Read-only attribute.** Every file under `files/` has the read-only attribute set. That attribute is a guard against accidents, not access control.

**The trial-count edit.** One edit was made to `REPORT.md` before it was delivered and before this freeze: the trial count was corrected from 4,890 to 5,070. The frozen copy is the delivered version.
