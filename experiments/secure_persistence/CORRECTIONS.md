# Corrections to the exploratory report

This document lists corrections to `REPORT.md` of the exploratory secure-persistence study v1, dated 2026-11-09. The frozen copy is in `snapshots/exploratory_persistence_v1_20261109/`.

**The original `REPORT.md` is not edited.** This file is the record of what should be read differently. Each item names:

- the original wording and where it appears;
- what is wrong;
- the corrected statement;
- the evidence, as a check ID in `audit/output/checks.csv` or a key in `audit/output/facts.json`.

**No number in the report was found to be wrong.** All corrections are about scope, definitions, units or wording that claims more than the data supports.

Severity, from most to least serious:

- **Interpretation:** changes what a reader would conclude.
- **Definition:** a metric means something narrower than its name says.
- **Wording:** imprecise, but the conclusion is unaffected.

---

### C0. "Total trials: 5,070" (header table): Interpretation

- **Original:** "Total trials | 5,070 rows in 9 CSV files; 0 failed".
- **Problem:** the 5,070 rows are not 5,070 independent trials. Seven encryption rows share one paused run. The latency rows summarize the same runs. The two decoder modes in the compatibility case share one state. 660 serializer rows repeat deterministic computations. 30 rows are warm-ups.
- **Corrected:** "5,070 result rows from 2,940 independent experimental runs, plus 660 repetitions of deterministic serializer computations and 30 performance warm-ups (excluded); 0 failed."
- **Evidence:** check 0.3; `facts.json` → `units`; EXPLORATORY_AUDIT.md section 2.

### C1. Key failures listed as rejected manipulations (B3, D3): Interpretation

- **Original:**
  - B3: "Every manipulation is rejected in 30/30 trials … in each of B, D, E and F."
  - D3: "all six manipulations were rejected at load in 30/30 trials each."
- **Problem:**
  - Two of the six, `wrong_key` and `missing_key`, are not tampering. The stored data was genuine, and the process lacked the right key.
  - They fail with the same `InvalidTag` as a tampered blob, so the system cannot tell an attack from an operational key problem.
  - Presenting six detected manipulations inflates the tamper-detection evidence.
- **Corrected:** "With encryption, all four tampering manipulations (`flip_ciphertext`, `flip_tag`, `truncate`, `plaintext_inject`) were refused at load in 30/30 trials per configuration. Separately, a wrong or missing key made genuine checkpoints unreadable in 30/30 trials (`InvalidTag`), with no send. That is a fail-closed availability failure, and the error is indistinguishable from tampering. In unencrypted configurations, a wrong or missing key left the checkpoint readable. The send was refused only because the approval-signing key is derived from the same master key; this is a coupling of the two mechanisms, not a property of encryption."
- **Evidence:** checks 4.1, 4.3; `facts.json` → `enc_errors`.

### C2. "Recovery success" combines checkpoint and execution recovery (B1, D1, Figure 1): Interpretation

- **Original:**
  - Figure 1: "Recovery success: correct outcome after a crash".
  - D1: "Correct outcomes were 100% [97.5, 100] in B–E".
- **Problem:** "correct outcome" means four things together: the request was restored, the payload matches, the number of deliveries is as expected, and no rejected action was sent. It does not mean the run's execution was recovered with a known result:
  - In R5 (B–E), the action's completion was never recorded.
  - In R4 and R5 (all configurations), recovery needed a second human approval, because the first was not persisted.
- **Corrected:** report two separate measures.
  - **Checkpoint recovery** (pending request restored intact in a new process): 150/150 in every configuration, 900/900 overall.
  - **Execution outcome after recovery, approve scenarios:**
    - B–E: exactly one delivery in 120/120 each. Completion recorded in 90/120 (R1, R3, R4). Unrecorded in 30/120 (R5, ledger `executing`).
    - A and F: exactly one delivery in 90/120; the 30 R5 trials delivered twice.
    - R4 and R5 required re-approval in 60/60 trials per configuration.

  Figure 1 should be titled "Crash scenarios with the expected number of deliveries (R1–R5)".
- **Evidence:** checks 1.0, 1.4, 1.10; `facts.json` → `execution_recovery`.

### C3. R5 counted as "correct" with the ledger (B1, D1, D5): Interpretation

- **Original:** R5 shown as 30/30 correct for B–E, and D1 calls the R5 behaviour with a ledger correct.
- **Problem:**
  - "Correct" here means only "not delivered twice".
  - The ledger entry stays `executing`, and the retried run finishes as `duplicate_prevented` without being halted.
  - To the operator, that looks identical to a correctly prevented duplicate of a confirmed delivery.
  - Had the crash happened *before* the send (not tested), the same state would hide an action that was never delivered.
- **Corrected:** "In R5, the ledger prevented a second delivery in 120/120 trials (B–E). The action's outcome remained unrecorded (`executing`), and the system reported the retry as a prevented duplicate. Whether the action was delivered cannot be determined from the ledger; it requires reconciliation with the recipient, which the current recipient does not support."
- **Evidence:** check 1.6; `approval_flow._execute` (a `duplicate_prevented` outcome does not halt the run); LEDGER_RECOVERY_ANALYSIS.md.

### C4. "The ledger matched the deliveries in 60/60" (B5): Definition

- **Original:** "Ledger state. The ledger matched the deliveries in 60/60 checked trials for each of B–E, CI [94.0, 100]."
- **Problem:** the check defined `executing` with 1 delivery as consistent for R5. The ledger records a delivery in 120/240 checked trials (R1 only). For R5, the measurement shows that the ledger state is as predicted for that crash point, not that it matches the delivery.
- **Corrected:** "The ledger state was as predicted for the crash point in 60/60 trials per configuration (B–E): `executed` after R1, and `executing` after R5. In R5 the ledger does not record the delivery that took place."
- **Evidence:** check 2.4.

### C5. Lost log line in the concurrent double-click (B5, D5): Wording / measurement

- **Original:**
  - D5 limitation: "1 trial logged 1 attempt but 2 deliveries … Duplicate counts without a ledger in L3 are therefore a lower bound."
  - The Experiment 5 output table lists A L3 `attempted_sends = 54`, `successful_sends = 55`.
- **Problem:** the report's conclusion is too weak in one place and imprecise in another.
  - **Exact, not a lower bound:** the *number of duplicate trials* is exact. The 5 A trials with one delivery all show a `no_pending` error from the second thread, and no trial shows one delivery without it.
  - **A lower bound:** what is uncertain is the per-trial *line counts*.
  - The table's 54 attempts are one too low.
- **Corrected:** "In L3 without a ledger, duplicate delivery occurred in 25/30 (A) and 30/30 (F) trials; these counts are exact. One A trial lost one log line to a concurrent append, so A's attempt total (54) is a lower bound; the consistent value is 55. Configurations with a ledger and the cross-process recovery experiment are not affected."
- **Evidence:** check 2.3; `facts.json` → `log_anomalies`; EXPLORATORY_AUDIT.md section 4.2.

### C6. Minimization size effect compared against the wrong reference (D2): Wording

- **Original:** "Minimization reduced stored blob bytes by about 9% (A to C: −9.5%)."
- **Problem:** A and C also differ in strict deserialization and the ledger. The leave-one-out contrast for minimization is E to B.
- **Corrected:** "Minimization reduced stored blob bytes by 9.5% (E 9,389 → B 8,496 bytes, means, n = 30)."
- **Evidence:** check 3.4.

### C7. "Encryption added about 57 bytes per checkpoint" (D2): Wording / unit

- **Original:** "Encryption added about 57 bytes per checkpoint (C to B)."
- **Problem:** `pending_blob_bytes` sums the checkpoint blob and every write blob stored for the thread at the pause. The expected AES-GCM cost is 28 bytes per blob (12-byte nonce + 16-byte tag).
- **Corrected:** "Encryption added 57 bytes per paused thread in total, summed over all stored blobs (C 8,439 → B 8,496 bytes)."
- **Evidence:** check 3.5.

### C8. "Per call" latency (B6, D6, Figure 4): Wording

- **Original:** "Checkpoint write per call", "Checkpoint read per call"; "raised per-call checkpoint read latency from 0.12 to 0.18 ms".
- **Problem:** each run contributes one value, the mean of that run's calls. The reported medians, SDs and P95s are over 40 run-means, not over individual calls.
- **Corrected:** "Mean checkpoint read latency per run: median over 40 runs 0.12 ms (A) and 0.18 ms (B)." Figure 4's axis label should read "ms per call, run mean (median, IQR over runs)".
- **Evidence:** check 7.4; `performance_experiments.one_run` (`write_mean_ms`, `read_mean_ms`).

### C9. AES-GCM sample description (B3): Wording

- **Original:** "AES-GCM cost per checkpoint blob (180 trials × 200 repetitions …)", with medians and P95s.
- **Problem:** each of the 180 rows is the mean of 200 repetitions. The median and P95 per configuration are over 30 run-means, so the P95 describes variation between runs, not single operations.
- **Corrected:** "AES-GCM time per operation, averaged over 200 repetitions in each of 30 runs per configuration; median and P95 across those 30 run means."
- **Evidence:** check 4.6.

---

## Smaller precision notes (no correction required)

- **"+12.3 ms in every configuration with the ledger" (D6).** +12.3 ms is B's mean difference. The range across B–E is +12.3 to +13.5 ms (means) and +11.8 to +12.5 ms (medians). Check 7.5.
- **"Checkpoint reads were 2.3 ms (unencrypted)" (B1).** The range is 2.28–2.36 ms. Check 1.9.
- **"Flipping the last byte changed bytes outside the compared channel values" (D3).** This is an inference from "channel values unchanged". The changed byte's location was not identified.
- **Fisher tests.** The reported tests are two-sided and unadjusted. Holm-adjusted across the four reported contrasts, the largest p is 6.8 × 10⁻¹⁷. The pre-registration's tests (one-sided, Holm across H1–H5) were not run, because this study does not implement the pre-registered design.
- **The bootstrap ratio CI for A against itself** in the performance table resamples A twice. It has no meaning and should be ignored.
