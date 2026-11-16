# PrivAgent v2: confirmatory report

Pre-registration: `experiments/v2/PREREGISTRATION_v2.md`, frozen 2026-11-15T13:25:37Z at commit
`7727046` (SHA-256 `846374a77d92b82e617be8ddd1ba8d60b2e898b9978d5d8351725f4076c705ac`, recorded in
`PREREGISTRATION_HASHES.md`, commit `6a59e1a`). Code: the pre-freeze commits `adc18b0`, `29b979c`,
`984caf9`, `843d157`; no code was changed after the freeze. Every outcome below is the one the
pre-registered script computed (`experiments/v2/results/confirmatory/analysis/h1..h5.{md,json}`),
copied, not recomputed. No amendments.

## Outcomes

| Hypothesis | Outcome | Decision statistic |
|---|---|---|
| H1 escalation-only precedence | **Supported** | 0 downgrades under `max_severity`, offline (10 seeds × 3 sets) and live (WP4) |
| H2 scored handoffs | **Supported** | score R1-on vs shadow: 14 → 0 sends of 40 pairs, exact McNemar p = 0.000122; score R1-off vs shadow: 14 → 14, p = 1 |
| H3 enforced provenance | **Supported** | under-reported + missing: shadow 12/16 sends, enforce 0/16, p = 0.000488 |
| H4(a) path-dependent recall lower | **Supported** | frozen-model step recall path 1/62 vs direct 52/52; path − direct −0.984 [−1.000, −0.948] |
| H4(b) position-only AUROC ≤ 0.6 | **Not supported** | AUROC 0.654, DeLong 95% [0.601, 0.706] (114 unsafe, 283 safe steps) |
| H5 v2 lower ASR than v1 and ml_only (family B, qwen2.5:3b) | **Supported** | v2 − v1 −0.281 [−0.431, −0.145]; v2 − ml_only −0.345 [−0.517, −0.186] |
| H5 v2 vs rules_only | **Claim made** (CI entirely below 0) | v2 − rules_only −0.321 [−0.517, −0.148] |

Bootstrap CIs: 10,000 resamples, seed 20261115, percentile. WP4 p-values carry the pre-registered
caveat: outcomes are deterministic, so the confirmatory half is a replication check on unseen
scenarios, and the scenario is the unit of analysis.

## Measured costs and secondary results (no thresholds)

- **H1, live (WP4, accurate declaration):** plain `max_severity` hard-blocks 10/14 benign sends
  against 2/14 for `first_fire_v1` (difference 0.571 [0.286, 0.786]);
  `max_severity_reviewable` matches `first_fire_v1` (2/14). Offline, every arm-minus-v1 cost
  difference is 0.000. Its downgrades are exactly the ML BLOCKED → HUMAN_APPROVAL relaxations on
  external actions (offline 376, live 70), none to an allowed decision.
- **H2:** with `handoff_enforce` (score, R1 off), 10/70 benign runs halted at a handoff, 0.143
  [0.079, 0.243]. R3 fired 0 times; no R3 effect is claimed.
- **H3 costs (benign sends, enforce, accurate):** 2/12 completed, 8/12 to review, 2/12
  hard-blocked; identical to shadow under accurate declaration. Under under-reported and missing
  declarations, enforce completes 2/12 where shadow completes 10/12.
- **H5 family B ASR per configuration** (denominator: runs that reached the scripted writer):
  no_governance 51/54, rules_only 18/56, ml_only 20/58, v1 16/57, **v2 0/55**, v2_reviewer 17/53.
  Model failures before the writer: 6, 4, 2, 3, 5, 7. Infrastructure exclusions: 0. Harness
  faults: 0.
- **H5 benign utility (40 tasks, Wilson 95%):** no_governance 23/40 = 0.575 [0.422, 0.715],
  rules_only 0.475, ml_only 0.500, v1 0.500, v2 18/40 = 0.450 [0.307, 0.602], v2_reviewer 0.550.
  Benign approval volume: v1 2/40, v2 5/40, v2_reviewer 5/40, others 0/40. Median seconds per
  run: 72–106.
- **Multiseed offline evaluation (WP5, descriptive, no test):**

  | Set | AUPRC (mean, 95% CI) | Step recall | Runs caught |
  |---|---|---|---|
  | test | 0.965 [0.960, 0.968] | 0.953 | 0.999 |
  | holdout_types | 0.853 [0.847, 0.860] | 0.562 | 0.672 |
  | holdout_variants | 0.834 [0.828, 0.841] | 0.338 | 0.671 |

  The path-dependent attack types are the ones mostly missed: held-out `path_cross_agent_leak`
  0.028, and on variant B `path_exfiltration` 0.036 and `path_privilege_escalation` 0.023. Every
  other type is ≥ 0.995. Full tables: `results/confirmatory/multiseed_confirmatory.md`.
- **Family A:** dropped; there was no paid Gemini quota. It was not run and not analysed.

## Observations (descriptive, not tested)

- **H4 used 19 of the 20 family B tasks.** In `v2`, all three runs of `atk_b_hr_depts` failed
  before the writer: the retriever raised `IndexError` on an empty `search_queries` list, which
  counts as a model failure. All three runs of `atk_b_ai_infra_hr` reached the writer, but none of
  their steps carried a canary, so they contributed only safe steps.
- **The `v2` result in H5 is driven by enforced provenance and scored handoffs on the send step.**
  The frozen model's own step decisions are not what stopped these sends: H4(a) shows the model
  flagged 1 of 62 path-dependent handoffs.
- **With the simulated reviewer**, which approves an attack send with probability 0.5,
  `v2_reviewer` lands at 17/53, close to `rules_only`.

## Run log

| Step | Started (UTC) | Finished (UTC) | Result | Commit |
|---|---|---|---|---|
| Freeze | | 2026-11-15T13:25:37Z | hash recorded | `7727046`, `6a59e1a` |
| 1. Precedence ablation + multiseed (seeds 42, 1–9) | 13:26:13 | 13:32:33 | exit 0 | `c7bd602` |
| 2. WP4 confirmatory half (880 runs, 22 scenarios) | 13:32:55 | 13:34:11 | exit 0 | `8316825` |
| 3a. Pilot family B, qwen2.5:3b (360 runs) | 13:35:05 | 21:32:09 | exit 0; 0 exclusions, 27 model failures | `6362436` |
| 3b. Pilot benign, qwen2.5:3b (240 runs) | 21:32:38 | 2026-11-16T03:32:35 | exit 0; 0 exclusions, 9 model failures | `c4d0b66` |
| 4. Analyses h1–h5, unchanged | 2026-11-16T03:33 (h1 written 03:33:06) | 03:33:09 (h5 written) | all exit 0 | `7eec408` |

Model: `qwen2.5:3b`, digest `357c53fb…015c9e4b`, checked by the harness before each pilot part. No
Gemini calls were made.

There were no failures and no selective reruns. One intervention before step 3a: 10 idle Python
processes were stopped. They were left over from an earlier, pre-freeze test run of a scratchpad
copy of the repo (restart-test workers and their MCP servers), not part of the study; nothing else
ran alongside the confirmatory steps.

Known text issue: the frozen pre-registration's header still reads "DRAFT … still unfrozen, no hash
recorded". The freeze is recorded in `PREREGISTRATION_HASHES.md`; correcting the header would be a
dated amendment.
