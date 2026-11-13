# Exploratory study audit

| | |
|---|---|
| Audit date | 2026-11-09 |
| Subject | exploratory secure-persistence study v1 (`REPORT.md`, `results/`, `analysis/`) |
| Audited copy | the frozen snapshot `snapshots/exploratory_persistence_v1_20261109/` (SHA-256 manifest of 84 files; archive `da46f42d…89ff33`) |
| Method | `audit/recompute.py`, written for this audit, reads only the frozen raw CSVs and does not import `analysis/analyze.py` |
| Outputs | `audit/output/checks.csv` (71 checks), `audit/output/facts.json`, `audit/output/performance_recomputed.csv` |

The original report is not changed. Corrections are listed separately in [CORRECTIONS.md](CORRECTIONS.md).

**Who did this audit.** It was carried out by the same agent that designed and ran the study, so it is a re-derivation, not an independent review by a second party. It guards against computational and transcription errors and against claims that go further than the data. It cannot exclude design errors shared by the harness and the audit, for example a wrong delivery counter. Section 6 lists what it cannot check.

## 1. Summary

| Result | Count |
|---|---|
| Checks run | 71 |
| Numbers that match the raw data | 67 |
| Mismatches | 4 (all interpretive or wording; no number in the report is wrong) |

What the audit found:

- **Every number is right.** Every stated count, rate, Wilson interval, mean, median, SD, P95, overhead percentage, Fisher p-value and Mann–Whitney statistic reproduces from the raw CSVs. Bootstrap intervals reproduce with an independent generator to within 0.91 percentage points (Monte Carlo variation).
- **Some statements claim more than the data shows.** The audit found 9 places where the report's wording goes beyond the data, or conflates two different things. Four are marked as mismatches in `checks.csv`; five more are wording issues found while reading. All are listed in CORRECTIONS.md (C1–C9). The most important are:
  1. **"5,070 trials" is wrong as a description.** These are 5,070 *rows*. They represent 2,940 independent experimental runs, 660 repetitions of deterministic serializer computations, 30 performance warm-ups, and rows derived from the same runs (section 2).
  2. **Wrong or missing keys were reported together with tampering.** For encrypted configurations they appear under "every manipulation is rejected". A wrong or missing key is a key-availability failure, not detected tampering (C1).
  3. **The R5 "correct outcome" and "ledger consistency" overstate what the ledger knows.** In R5 the ledger never records that the delivery happened (C3, C4).
  4. **"Recovery success" in Figure 1 and B1 mixes two different properties:** checkpoint recovery and execution recovery (C2).

## 2. Trial counts and independence (point 5)

| CSV | Rows | Failed | What one row is | Independent experimental units |
|---|---|---|---|---|
| `recovery.csv` | 900 | 0 | one crash-recovery trial: own store, own seed, separate OS processes | 900 |
| `ledger.csv` | 900 | 0 | one ledger trial | 900 |
| `confidentiality.csv` | 180 | 0 | one trial, with 3 measurement phases of the same run | 180 |
| `encryption.csv` | 1,260 | 0 | one manipulation; **7 rows share one paused run** (manipulations applied to copies of the same store) | 180 |
| `encryption_latency.csv` | 180 | 0 | the mean of 200 timing repetitions; **the same 180 runs** as `encryption.csv` | 0 additional |
| `deserialization_store.csv` | 300 | 0 | one probe-injection trial | 300 |
| `deserialization_serde.csv` | 1,020 | 0 | 360 rows: 180 compatibility runs × 2 decoder modes on the same state; 660 rows: 22 deterministic cases × 30 repetitions | 180 runs + 660 deterministic repetitions |
| `performance.csv` | 270 | 0 | 240 measured runs + 30 warm-ups (excluded) | 240 |
| `performance_memory.csv` | 60 | 0 | one memory run | 60 |
| **Total** | **5,070** | **0** | | **2,940 independent runs** |

Consequences for how the results can be read:

- **Within-run comparisons.** The 7 manipulation outcomes in one encryption run are not independent samples: they share the canaries, the store and the pause. Comparisons between manipulations are within-run comparisons. The per-cell Wilson intervals, n = 30 per configuration and manipulation, are still correct, because every cell holds 30 distinct runs.
- **Deterministic serializer cases.** For the serializer-level cases (type round-trips, probe class, unknown class), 30 repetitions of a deterministic computation give no sampling information. "30/30" there means "deterministic and reproduced", not a rate with a confidence interval.
- **Compatibility rows.** The two decoder modes are applied to the same state, so the 180 + 180 rows are 180 paired runs.
- **R5 is counted twice.** The R5 row of the Experiment 5 table reuses the same 180 Experiment 1 trials. It is not an independent replication.
- **Timing is not independent across trials.** Crash-recovery trials ran 10 at a time, so their timings share machine load. Their outcomes (counts, states) are independent.
- **Performance runs are paired.** Runs within one repetition use the same canary seed (`perf-<rep>`) across configurations. The analysis treats them as independent groups, which is conservative for the medians and makes no difference to their values.
- **Seeds.** Seeds are unique per independent unit: 900 / 900 / 180 / 180 / 300.

## 3. Results that reproduce exactly

Each line below reproduces from the raw data. Check IDs refer to `audit/output/checks.csv`.

| Section | What was recomputed | Checks |
|---|---|---|
| B1 recovery | All 30 per-scenario cells; pooled correct-outcome and duplicate rates with Wilson CIs. A, F: 120/150, [72.9, 85.6]; dup 30/150, [14.4, 27.1]. B–E: 150/150, [97.5, 100]. Pending recovered 900/900; R2 sends 0/180; R5 ledger `executing` 120/120; second-resume outcomes 180/180 + 180/180; latency ranges | 1.0–1.9 |
| B1 classification | The derived `correct_outcome` column was re-derived from primitive columns (paused, pending recovered, payload matches, delivered = expected, no rejected send): agrees in 900/900 | 1.0 |
| B2 confidentiality | All canary counts. The count is identical (min = max) in all 30 trials of every configuration. Blob means and SDs to the byte; file bytes 86,336 in every trial; 0 rows after purge | 3.1–3.6 |
| B3 encryption | All 42 manipulation cells (outcome counts and number of trials with a send); error types; AES-GCM median and P95 ranges | 4.1–4.5 |
| B4 deserialization | All 10 store-level cells; 360/360 compatibility round-trips; probe-class and tuple behaviour | 5.1–5.4 |
| B5 ledger | All 36 cells. `at_most_once` agrees with delivered ≤ 1 in 900/900. A L3 duplicates 25/30 | 2.0–2.2 |
| Fisher tests | 0/30 vs 30/30, two-sided: p = 2 / C(60,30) = 1.69 × 10⁻¹⁷ (reported "< 10⁻¹⁶"). One-sided p = 8.46 × 10⁻¹⁸. Holm-adjusted across the 4 reported contrasts: largest 6.8 × 10⁻¹⁷ | 6.1 |
| B6 performance | 40 measured runs per configuration. Mean, median, SD (ddof = 1), P95 and overhead equal the generated table to 1e-6 for all 42 metric × configuration cells; all B6 values in the report match at 1 decimal place. Mann–Whitney U = 1600, p = 1.4 × 10⁻¹⁴. Memory medians 0.315 / 0.317 MB | 7.0–7.8 |
| Bootstrap CIs | Independent `scipy.stats.bootstrap` (percentile, 10,000 resamples, different seed): maximum deviation from the reported median and ratio CIs is 0.91 percentage points | 7.2 |

Method notes on the statistics, not errors:

- **P95** uses NumPy's default linear interpolation. With n = 40, the nearest-rank P95 differs slightly; both are in `performance_recomputed.csv`.
- **Bootstrap seeding.** `analyze.py` draws all bootstrap resamples from one module-level generator. Each interval therefore depends on the order of the calls before it. The intervals are reproducible only by re-running the whole script unchanged. The confirmatory analysis should seed each interval independently.
- **Reference ratio.** The bootstrap ratio CI reported for A against itself, [0.963, 1.038], resamples A twice independently. It is not meaningful and should not be shown.
- **Test choices differ from the pre-registration.** The Fisher tests in the report are two-sided and unadjusted. The pre-registration specifies one-sided tests with Holm adjustment for H1–H5. The conclusions are unchanged at these p-values, but the exploratory tests are not the pre-registered ones.
- **Wilson intervals** were cross-checked against `scipy.stats.binomtest(...).proportion_ci(method="wilson")` for every interval computed (assertion in the script; no failure).

## 4. Points examined in detail

### 4.1 Ciphertext tampering against wrong or missing keys (point 1)

**What the data shows:**

- In encrypted configurations, both key failures end in `InvalidTag`, in 30/30 trials per configuration (`facts.json` → `enc_errors`). That is the same exception as a flipped ciphertext or tag byte.
- In unencrypted configurations, a wrong or missing key leaves the checkpoint readable. The send is then refused (0 sends), because the approval-signing key is derived from the same master key.

**Why this is a separate category:**

- **Tampering** means the attacker changed stored data. Detecting it is the integrity property P1.
- **A wrong or missing key** means the operator's process cannot decrypt genuine data. It is an availability and key-management failure, and the stored data may be entirely intact.

**Why it matters:** the system cannot tell the two apart. Both raise `InvalidTag`, so an operator who loses or rotates a key will see what looks like tampering. Counting key failures as tampering cases also inflates the number of "detected manipulations" from 4 to 6 per configuration. Only `flip_ciphertext`, `flip_tag`, `truncate` and `plaintext_inject` are tampering.

**In unencrypted configurations,** "send refused after a wrong key" is a side effect of the shared master key, not a property of encryption. It would disappear if the approval key were provisioned separately.

Correction C1.

### 4.2 The lost transmission-log line in the concurrent double-click (point 2)

**The anomaly.** In `ledger.csv`, configuration A, scenario `L3_double_click`, trial 11 (seed `20261109-L-A-L3_double_click-11`) recorded 1 `attempt` line but 2 `delivered` lines. It is the only row among the 1,800 ledger and recovery rows where attempts ≠ deliveries (check 2.3).

**Cause (hypothesis, not verified).**

- In L3 the two "clicks" are two threads in one process. Each appends to the same JSONL file through its own `open(path, "a")`.
- On Windows, the C runtime implements append by seeking to the end and then writing, which is not atomic across threads. Two concurrent writes at the same offset can overwrite each other, so one line is lost.
- The per-trial log file was deleted with the trial directory, so the mechanism cannot be confirmed after the fact.

**Effect on the results:**

- **Duplicate classification is unaffected.** All 30 F trials and 25 A trials show 2 deliveries. The 5 A trials with 1 delivery all recorded a `no_pending` error from the second thread, so they really had one send.
  - A trial with two real sends whose two delivery lines both collided would appear as delivered = 1 *without* that error. No such trial exists.
  - So 25/30 (A) and 30/30 (F) duplicate trials are exact counts.
- **Per-trial delivery and attempt counts in L3 without a ledger are lower bounds.** The reported `attempted_sends = 54` for A in L3 is one too low; 55 is the consistent value.
- **Configurations with a ledger are not affected.** In B–E, only one thread ever reaches the send, so there are no concurrent writes.
- **Cross-process recovery counts are not affected.** R1–R5 write the log from sequential processes, and attempts = deliveries in all 900 trials.

**Remedy for the confirmatory study:** serialize the stand-in's log writes (a lock, or one file per call with an atomic rename), and fail the trial when attempts ≠ deliveries.

Correction C5.

### 4.3 The ledger's stuck `executing` state (point 3)

**The data.** In R5, a crash after the send but before `finish()`, the ledger entry remains `executing` in 120/120 trials (B–E). The retried approval was accepted by the approval service in 120/120. The ledger claim then failed, so there was no second send.

**What `executing` means.** "Claimed, outcome not recorded." That one state covers three different realities:

1. claimed, crashed before the call (not delivered);
2. crashed during the call (unknown);
3. crashed after delivery (delivered).

The exploratory study only produced case 3. The ledger contains no information that tells the three apart, and `executing` entries never time out or get reconciled.

**What the report gets right and wrong:**

- **Right:** "at most once".
- **Wrong:** "ledger consistency: 60/60". The analysis defined `executing` as the consistent state for R5. That is a definition, not a measurement that the ledger matches the deliveries: the ledger records a completed delivery in 120/240 checked trials, which is R1 only.
- **Missing:** the user-visible outcome. After the retry, the run finished with outcome `duplicate_prevented` and was not halted, because `_execute` halts only on outcomes other than `duplicate_prevented`. A stuck action looks the same to the reviewer as a correctly prevented duplicate of a confirmed send.

Corrections C3 and C4. The full analysis is in [LEDGER_RECOVERY_ANALYSIS.md](LEDGER_RECOVERY_ANALYSIS.md).

### 4.4 Checkpoint recovery against execution recovery (point 4)

The report's "recovery success" (Figure 1, table B1) combines two properties:

| Property | Definition | A | B, C, D, E (each) | F |
|---|---|---|---|---|
| Checkpoint recovery | the pending request is restored intact in a new process | 150/150 | 150/150 | 150/150 |
| Delivery count correct (approve scenarios R1, R3, R4, R5) | exactly one delivery | 90/120 | 120/120 | 90/120 |
| Execution recovery confirmed | exactly one delivery **and** completion recorded | n/a (no ledger) | 90/120 (R1, R3, R4); R5: 0/30, outcome unrecorded | n/a |

**Checkpoint recovery** is shown for all 900 trials and is a property of the LangGraph SQLite checkpointer. None of the four mechanisms changes it.

**Execution recovery** is shown only where the run reached its end with a recorded outcome. Two qualifications apply:

- In R4 and R5, the approval decision was not persisted. Every trial needed a second human approval (60/60 per configuration; check 1.10), so recovery depended on a reviewer acting again.
- In R5, "correct outcome" means "not sent twice". It does not mean the system knows the action was delivered.

Correction C2.

## 5. Other observations from the audit

- **Byte flips without encryption.** In 59/60 trials, a flipped byte was loaded undetected and the approved action was still delivered. The comparison was on decoded channel values; whether the delivered payload itself was altered was not recorded. The approval digest would refuse a changed payload, as `plaintext_inject` shows (0/60 sends). So these 59 deliveries most likely carried an unchanged payload, with the alteration elsewhere in state. That is an inference, not a measurement.
- **`flip_tag` without encryption.** "Bytes outside the compared channel values" is an inference from "loaded, channel values unchanged". The changed byte's location was not identified.
- **AES-GCM latency.** It was measured as one mean per run over 200 repetitions, then summarized by median and P95 over 30 run-means. The reported spread is therefore the spread of run means, not of individual operations (C9).
- **Size comparison.** The −9.5% "A to C" size difference compares configurations that also differ in M2 and M4. E to B isolates M3 and gives the same −9.5% (C6).
- **Encryption overhead in bytes.** The "+57 bytes per checkpoint" is per paused thread, summed over the checkpoint blob and all write blobs (C7).
- **Per-call latency.** It is the median of per-run *mean* call latencies, not of individual calls (C8).
- **Stored blob size.** It differs between Experiments 2 and 6 (A: 9,327 against 9,260 bytes) because the canary seeds differ in length. Both are correct for their own runs.

## 6. What this audit cannot verify

- **Shared counters.** The audit re-derives results from the same CSVs the harness wrote. Errors in what the harness measured would be shared, for example the delivery counter or the canary scanner. The scanner's positive control is configuration A, where it finds 18/18.
- **Lost per-trial artifacts.** Stores, transmission logs and audit logs were deleted after each trial, so per-trial evidence beyond the CSV row cannot be re-examined.
- **Environment.** The software environment is recorded (`environment.json`), but the run cannot be bit-for-bit reproduced: timing, and thread scheduling in L3.
