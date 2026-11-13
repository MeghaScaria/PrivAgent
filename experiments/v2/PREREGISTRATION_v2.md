# PrivAgent v2: pre-registration (DRAFT; finalise, then hash before any confirmatory run)

**Status:** DRAFT, 13 Nov 2026.

**Freezing procedure:**
1. Edit the TBD fields.
2. Compute the SHA-256 of this file and record it, with a UTC timestamp, in
   `experiments/v2/PREREGISTRATION_HASHES.md`.
3. Optionally post the hash publicly (e.g. a GitHub commit, or OSF) for an external timestamp.

After that, any change is a dated amendment listed at the bottom. It never silently replaces
the text above it.

## 1. Data the confirmatory analyses may use
- **Synthetic:** the test split, held-out types (`data_exfiltration`, `cascading_failure`,
  `path_cross_agent_leak`) and variant B, for seeds {42, 1–9}.
- **Real-LLM:** all runs produced by `experiments/v2/real_llm_pilot.py` after freezing.
- **Development (not confirmatory):** train and val splits, variant C, and any real-LLM runs
  made before freezing. Those runs are discarded from confirmatory analysis.

## 2. Hypotheses and decision rules

**H1: Escalation-only precedence (WP1)**
- **Claim:** under `max_severity`, no sensitive external send that the ML model rates BLOCKED
  executes. The benign approval volume rises by at most **TBD (proposed: 5 percentage
  points)** relative to `first_fire_v1`.
- **Test:** count the downgrade events (expected 0), and the difference in benign-run
  approval rate with a 95% bootstrap CI over runs and seeds.
- **Supported** if there are 0 downgrades and the CI's upper bound is ≤ the margin.

**H2: Scored handoffs (WP2)**
- **Claim:** with `handoff_mode="score"`, R3 and the cross-agent features become active live,
  and live run-level catch of path-dependent scenarios improves over `shadow`.
- **Test:** run-level catch on the live replay scenarios, compared by McNemar's test on paired
  runs.
- **Supported** if p < 0.05 and the effect is in the predicted direction.
- **Flow features:** re-run the original pre-specified rule unchanged. A candidate is adopted
  only if the mean LOTO AUPRC gain minus 2·SE > 0, it is not worse on variant C, and false
  alarms stay within 2 percentage points.

**H3: Enforced provenance (WP4)**
- **Claim:** in the under-reported and missing conditions, `enforce` reduces canary-confirmed
  attack sends relative to `shadow`.
- **Cost:** the benign block-or-escalate rate under `enforce` is reported with a Wilson CI.
  No success threshold is set for it; it is a measured cost.
- **Supported** if attack sends are lower under `enforce` (exact paired test, p < 0.05).

**H4: Shortcut-vs-generalisation on real traces (WP6)**
- **Claim:**
  - (a) The frozen model's step recall on real-LLM attack steps is lower for path-dependent
    flows than for direct-exfiltration flows.
  - (b) A position-only classifier, trained on synthetic data, has AUROC ≤ 0.6 on real traces.
- **Test:**
  - (a) Difference in recall, with a bootstrap CI.
  - (b) AUROC with a DeLong CI.
- **Either outcome is reported.**
  - If (a) fails, the synthetic trade-off finding is reported as not replicated.

**H5: Defence comparison on real LLMs (WP6)**
- **Primary metric:** canary-based attack success rate (ASR), over the six configurations
  per model.
- **Secondary metrics:** benign utility, utility under attack, approval volume, latency.
- **Hypothesis:** v2 has lower ASR than v1 and than ML-only.
- **No claim of beating the rules-only PEP** unless its CI excludes it.

## 3. Sample sizes
- **Synthetic:** 10 seeds × the existing set sizes.
- **Real-LLM pilot:** ≥ 40 benign + ≥ 40 attack tasks × 3 repeats × 2 models × 6 configurations.
- **Full study:** TBD. Choose it after the pilot from the observed ASR variance, and record
  the choice as an amendment *before* running.

## 4. Exclusions
- A real-LLM run is excluded only for an infrastructure failure: an API error, a timeout, or
  an MCP server crash.
- Exclusions are counted and reported per configuration.
- Runs where the LLM ignores the task are **not** excluded; they count as utility failures.

## 5. Reporting commitments
- Every hypothesis gets a result, positive or negative.
- All exploratory analyses are labelled exploratory.
- No claims of production readiness, exactly-once delivery, or enforcement beyond what was
  measured.

## Amendments
(none)
