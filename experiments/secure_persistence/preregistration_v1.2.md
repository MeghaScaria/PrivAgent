# Pre-registration amendment v1.2: Secure Persistence Ablation Study

| | |
|---|---|
| Version | 1.2 (amendment) |
| Prepared | 2026-11-09T07:12Z (12:42 IST) |
| Status | **proposed; frozen on approval**. The approval and the freeze time are recorded in section 13 |
| Parent | `preregistration.md` v1.1, SHA-256 `8363417c5aadac06f6d87709e0d97f659ecd9a61a1fbd5c8b7112d049583c358` |
| Confirmatory data collected before this amendment | **none** |

**v1.1 is not edited.** It stays the authoritative text for everything this amendment does not change. Where the two conflict, v1.2 prevails. Every change is listed in section 1 with:

- the v1.1 text it replaces;
- the reason;
- whether the change was **motivated by exploratory observations**.

## 0. Amendment history

| Version | Date | Status | Summary |
|---|---|---|---|
| 1.0 | 2026-11-09 | superseded before any data | initial design |
| 1.1 | 2026-11-09 | frozen; hash above; unchanged | added section 4a (P1–P3), A5, T18a–d, H6a–d, metric 5b, scope exclusions |
| 1.2 | 2026-11-09 | proposed | this document: H5 retired and replaced; terminology; attacker model; units of analysis; reporting rules; ledger-recovery scenarios |

### Disclosure of exploratory knowledge

Between v1.1 and v1.2, an **exploratory** study was run with a different design:

- six configurations A–F, two of them without the ledger;
- no PC1 or PC2;
- the investigators' own harness.

That study, its audit and its corrections are frozen. The record is:

- the snapshot `snapshots/exploratory_persistence_v1_20261109/`;
- archive SHA-256 `da46f42d925f5ba160a1017345b5e71acc418959d7f2ee03e5a1a4695589ff33`;
- manifest of 84 files;
- the documents `EXPLORATORY_AUDIT.md` and `CORRECTIONS.md`.

The investigators know its results. Consequences:

- Where v1.2 changes a hypothesis because of those results, it says so (section 1, column "Motivated by exploratory observations").
- **No exploratory result is used as confirmatory evidence**, and none is pooled with confirmatory data.

## 1. Complete list of changes

"Motivated" means the change was prompted by an exploratory observation. Those changes carry a higher risk of being fitted to known data. Each such hypothesis is therefore tested only on fresh data (section 4).

| # | v1.1 location | v1.1 text (condensed) | v1.2 change | Reason | Motivated by exploratory observations? |
|---|---|---|---|---|---|
| AM1 | §8 H5; §13 | H5: "M1 detects in-place tampering at load. Byte flip and truncation refused at the storage layer; T8. C1 = 100%, C2 = 0%" | **Retired** before any confirmatory data, and kept verbatim in section 2 with status "contradicted by exploratory evidence". Not tested and not reported as confirmed | Its C2 prediction for truncation is contradicted (section 2) | **Yes** |
| AM2 | §8 family H1–H5 | H5 in the confirmatory family | Replaced in the family by **H5a**: authenticated refusal of in-place byte flips and truncations (section 3.1). The family stays at five contrasts | H5a measures what v1.1 §4a says H5 was meant to test (P1, ciphertext authentication), separately from structural decoding failures | **Yes** (the measure was redefined after the conflict was seen; the C1 prediction is unchanged from v1.1) |
| AM3 | new | none | New hypothesis **H5′** (section 3.2): structural MsgPack decoding refuses truncated checkpoint blobs without encryption, and strict deserialization (M2) makes no difference. Confirmed-descriptive; **outside** the H1–H5a family; tested on a new seed namespace (section 4) | You asked to investigate the exploratory observation properly instead of reusing it | **Yes** |
| AM4 | §7 T8; §11 | T8: "byte flip, truncation, metadata edit", n = 30 per configuration | T8 is split into three sub-scenarios, **T8-flip, T8-trunc and T8-meta**, each with n = 30 *independent* runs per configuration. No run is manipulated more than once, and no copies of one paused run are shared between sub-scenarios | The exploratory design applied several manipulations to copies of one run, which made them dependent (correction C0) | No (it implements the independence requirement) |
| AM5 | §4a; §7 T1; §8 H6b, H6d; §8a | "The exactly-once guarantee depends on the ledger not being rolled back"; §8a claims "exactly-once execution (M4)" | Terminology replaced throughout by the defined terms of section 5. §8a's M4 claim becomes **"at most one execution attempt per approved action ID"**. Added to "makes no claim of": exactly-once delivery, confirmed delivery after a failure at or after the claim, and recovery of ambiguous actions. The counts in T1 ("exactly one send") and H6b/H6d are kept, as *measured counts at the recipient stand-in*, not as guarantees | v1.1's design cannot support exactly-once: the claim, the call and the completion record are separate steps, and the recipient has no idempotency key | No (code analysis); the exploratory R5 observation agrees |
| AM6 | §5 attacker B; §7 T17; §8 I2; §8a | B "holds the checkpoint key (leaked `master.key` …)"; T17 refused by PC1 for "B in all"; I2 claimed against B | B is split into **B1** (checkpoint subkey only) and **B2** (master key), section 6. T17 uses A4 (C0, C2) and B1 (C1, C3, C4). **I2 is not claimed against B2.** New descriptive scenario **T19 / H6e** characterizes B2 forging an approval | The approval key K is derived from the master key (§4), so a master-key holder can forge digests and tokens. v1.1's T17 prediction cannot hold for that attacker | No (design analysis) |
| AM7 | §9 metric 2; criterion (f) | digest-recording stand-in | Every call is recorded as one atomically renamed file with `received` and `delivered` markers. A record inconsistency is a **measurement defect**: it stops the study, and it is never an exclusion | An exploratory log line was lost to concurrent appends (correction C5) | Yes (the procedure was prompted by it); no prediction is affected |
| AM8 | §8; §13 | none | New confirmed-descriptive scenarios **T20a–h** (H7a–h): the ledger-recovery failure points, section 7.2 | Characterizes the M4 limits made explicit by AM5 | No: the predictions are derived from code |
| AM9 | §8 exploratory | E1–E5 | Added **E6**, key-availability failure (wrong or missing key), which is never counted as tamper detection; **E7**, byte-flip end-to-end outcome without M1; and **E8**, the authenticated-against-structural breakdown of refusals in T8 | Keeps key failures out of the tamper measure (correction C1). Records what H5 used to conflate | Yes, for E7 and E8 (descriptive only) |
| AM10 | §10 | bootstrap seed 20261111 | One generator per interval, seeded with `SHA-256("20261111\|<metric>\|<config>")[:8]` | Removes the dependence on computation order found in the exploratory analysis | No |
| AM11 | §10 | master seed 20261109 | Seed namespaces are fixed per family (section 4.1). Before the run, a check confirms that no confirmatory seed equals any exploratory or validation seed | Freshness of data (your item 3) | No |
| AM12 | §4 approved action | `"mcp_server": "external_server"` | Clarification: `mcp_server = MCP_SERVER_IDENTITY[TOOL_TO_SERVER[tool]]`, with `{"external": "external_server"}`, resolved from code, never from state | The code's routing key is `"external"`; this records how the literal value is produced | No |
| AM13 | §9; §13 | none | Unit-of-analysis rules (section 8): every reported n counts independent runs | Correction C0 | No |
| AM14 | §13 | none | Mandatory reporting rules (section 9), which close the nine exploratory reporting issues C1–C9 (plus C0) | Your item 7 | No |
| AM15 | §13 | "A hypothesis is confirmed if the adjusted p < 0.05 and the direction matches. The difference in proportions is reported …" | Added: **"Each hypothesis's point prediction is also reported as met or not met. If the test confirms the direction but the point prediction fails, the result is reported as 'direction confirmed, prediction not met', never as plain 'confirmed'."** | Under v1.1's rule, H5 could have been "confirmed" by the Fisher test while its stated prediction was contradicted (section 2) | Yes |

Unchanged:

- configurations C0–C4 (ledger on in all);
- the frozen models, thresholds, feature configuration and datasets (MCP seed 42);
- H1–H4, H6a–d, I1, F1–F4, E1–E5;
- the exclusion criteria (§12);
- the sample sizes, except where stated;
- the Holm and Newcombe procedures;
- PC1–PC4 as preconditions.

## 2. Retired hypothesis H5 (kept for the record)

**Original text (v1.1 §8, verbatim):**

> | H5 | M1 detects in-place tampering at load | Byte flip and truncation refused at the storage layer; T8 | C1 = 100%, C2 = 0% |

**Status:** retired before any confirmatory data. **Contradicted by exploratory evidence.** H5 is not tested, and it must never be reported as a confirmed or confirmatory hypothesis.

**Evidence.** The exploratory study (not under the v1.1 design) used configurations without encryption: A (M2 off) and C (M2 on). The manipulations were applied to copies of one paused run per trial.

| Manipulation | Refused at load without encryption | Refusal | Evidence |
|---|---|---|---|
| Truncation by 20 bytes | **60/60** | MsgPack decoder `ValueError` | `encryption.csv`, rows `truncate`, configurations A and C |
| Single byte flip | 1/60 | | same file |

**Why it is contradicted.** The prediction "C2 = 0%" fails for truncation. The refusal comes from structural decoding, not from M1. H5's construct ("M1 detects …") would therefore attribute to M1 a refusal that also occurs without it.

**Why it is retired rather than tested.** Under v1.1 §13, H5 would very probably have passed its own test: pooled flips and truncations in C1 at 100%, against about 50% in C2, gives a small one-sided Fisher p. Its stated prediction would have failed all the same. Reporting that as "confirmed" would mislead. AM15 closes this gap for all hypotheses.

## 3. Replacement hypotheses

### 3.1 H5a: authenticated refusal (in the confirmatory family)

| | |
|---|---|
| Statement | M1 refuses in-place byte flips and truncations of stored checkpoint data by **authentication**, before any decoding |
| Scenario | T8-flip and T8-trunc (AM4): 30 independent runs each, per configuration |
| Outcome per run | *authenticated refusal*: recovery fails with the cipher's authentication error (`InvalidTag`) or with the explicit refusal of a plaintext blob, raised before the serializer decodes anything. Other refusals (decoder errors) are **not** counted, and are reported in E8 |
| Contrast | C1 against C2, pooled over T8-flip and T8-trunc (60 runs each); also reported per sub-scenario |
| Prediction | C1 = 100%; C2 = 0% |
| Test | one-sided Fisher in the predicted direction, Holm across H1–H4 and H5a; Newcombe hybrid-score 95% interval for the difference; point prediction reported per AM15 |
| Motivation | the measure was redefined after the exploratory conflict. The C1 prediction is the one v1.1 already made |

**Limitation.** The C2 = 0% prediction holds **by construction**: C2 has no authentication. The informative part of H5a is that C1 refuses every flip and truncation. H5a does not show that M1 detects context substitution or rollback (P2 and P3; T18).

### 3.2 H5′: structural refusal of truncation without encryption (confirmed-descriptive)

| | |
|---|---|
| Statement | Without M1, a stored MsgPack-typed checkpoint blob truncated at any offset is refused at load by structural decoding, with no state loaded, no ledger claim and no send. The refusal does not depend on M2 (strict or permissive decoding) |
| Status | **motivated by exploratory observations**. Outside the H1–H5a family. Never credited to M1 or M2 |
| Configurations | C0 (M1 off, M2 off) and C2 (M1 off, M2 on). C1 is included as a reference cell (expected refusal by authentication, reported only) |
| Scenario | **T8-struct** (section 4) |
| Prediction | structural refusal in **100%** of runs in each of the 4 primary cells (C0 and C2 × 2 targets); difference C2 − C0 = 0 |
| Confirmation rule (pre-specified) | **H5′-R (refusal)** is confirmed if structural refusal occurs in all 75 runs of every primary cell; the Wilson 95% interval is reported per cell (75/75 gives a lower bound of 0.951). **H5′-I (independence of M2)** is supported if, for each target, the Newcombe 95% interval for the difference in refusal rate C2 − C0 lies entirely within **±0.10** (the equivalence margin, fixed here). Both are reported separately. Any run in which truncated state loads without error is reported in full (offset, blob type, decoded value) as a counter-example, and H5′-R is not confirmed |
| What a confirmation would support | "In configurations without encryption, truncation of MsgPack-typed checkpoint blobs was refused by the decoder, with or without strict deserialization." Nothing more |

**What H5′ does not show, stated in advance:**

1. **Truncation detection is not tamper detection.** An attacker who can write the store can write a well-formed altered blob instead. The exploratory `plaintext_inject` loaded in 60/60 runs without encryption. Structural validation gives **no** protection against deliberate tampering.
2. **Appended bytes are not covered.** A design-time check (2026-11-09, on a synthetic dict, not study data) found that trailing bytes after a complete MsgPack object are silently ignored by the decoder in both modes.
3. **Blobs typed `bytes` or `null` are not covered.** They are not decoded as MsgPack, so their truncation is not structurally detectable.
4. **Version dependence.** The result depends on the pinned `ormsgpack` 1.13.0 and langgraph-checkpoint 4.3.1.
5. **Why refusal is expected.** MsgPack encodings of a single object are self-delimiting, so every proper prefix is an incomplete encoding. That makes H5′-R close to a format property. The empirical content of H5′ lies in the end-to-end behaviour: whether the system fails closed, with no fresh run started, no claim and no send, and that it does so identically with M2 on and off.

## 4. H5′ confirmatory test design (T8-struct)

### 4.1 Fresh data

- **Seed namespace.** Master `20261112`. The run seed is `SHA-256("20261112|H5prime|<config>|<target>|<rep>")[:8]` (16 hex characters).
- **No overlap.** Before the run, the harness checks that no H5′ seed equals any exploratory seed (the strings in the frozen CSVs), any validation seed (namespace `20261108`) or any other confirmatory seed (namespaces `20261109` for the v1.1 scenarios and `20261113` for T19 and T20). The run aborts on any overlap.
- **Fresh state.** Every run creates a new store in a new temporary directory, its own canaries (derived from the run seed) and a new paused run. No store, blob or result from the exploratory study, from G3 validation, or from another scenario is reused.
- **The exploratory 60/60 is motivation only.** It is never counted, pooled or cited as evidence for H5′.
- **The fixed synthetic corpus is not fresh.** The synthetic document and record content is fixed by v1.1 (MCP seed 42) and is the same as in the exploratory study. Freshness here means new runs, stores, canaries and truncation offsets, not a new corpus. This is listed as a limitation.

### 4.2 Procedure (one run)

1. Create a fresh store for the configuration. Start the scripted workflow until the approval pause, then **hard-kill** the pausing process (`TerminateProcess`).
2. **Select the target**, by cell:
   - **K (checkpoint):** the `checkpoints.checkpoint` blob of the paused thread's latest checkpoint;
   - **W (write):** the largest `writes.value` blob of the paused thread whose `type` is `msgpack`.

   If the target's `type` column is not `msgpack`, the run is an infrastructure fault before treatment: excluded and replaced under v1.1 §12.
3. **Truncate:** choose the truncation length L from the run seed, uniformly in [1, len − 1], where len is the blob length. Reps 0 and 1 of each cell are fixed at L = 1 and L = len − 1 (edge cases); reps 2–74 are random. Write the prefix back to the same row, leaving the `type` column unchanged. No other byte is changed.
4. **Recover** in a new process: open the store, call `pending_review`, then submit an approval with the originally presented action ID and digest.
5. **Record:**
   - the exception type and module of origin (cipher, decoder or other);
   - whether `pending_review` returned a request;
   - whether any state loaded;
   - whether LangGraph started a new run;
   - the ledger rows (count, status);
   - the recipient stand-in's `received` / `delivered` counts;
   - L, len and the target.

**Outcome definitions:**

- **Structural refusal:** recovery raised a decoding error from the serializer, no state was returned for the thread, the ledger has 0 rows, and the stand-in has 0 `received` records.
- **Silent acceptance:** state loaded without an error.
- **Other:** any other combination, reported individually.

### 4.3 Cells and sample size

| Cell | Configuration | Target | n |
|---|---|---|---|
| 1 | C0 | K | 75 |
| 2 | C0 | W | 75 |
| 3 | C2 | K | 75 |
| 4 | C2 | W | 75 |
| ref | C1 | K and W | 30 + 30 (reference, reported only) |

**Total:** 360 independent runs.

**Why n = 75:** 75/75 gives a Wilson 95% lower bound of 0.951, and with both arms at 75/75 the Newcombe interval for the difference is about ±0.05, inside the ±0.10 margin.

**Run order:** cells interleaved, with the order shuffled per rep using seed `SHA-256("20261112|order|<rep>")`.

### 4.4 Analysis (fixed now; script frozen at G5)

- Per cell: the proportion of structural refusal, with a Wilson 95% interval.
- **H5′-R:** confirmed only if all four primary cells are 75/75.
- **H5′-I:** for each target, the Newcombe hybrid-score 95% interval for C2 − C0. Supported if within ±0.10 for both targets.
- **Descriptive:**
  - the exception types;
  - the distribution of L among any non-refusals;
  - reference cells: share of authenticated refusals in C1.
- **No other tests on T8-struct.** Anything further is labelled exploratory.

### 4.5 Exclusions and stopping

- v1.1 §12 applies.
- An excluded run is replaced by the next seed in the same namespace (rep index continued past 74).
- A measurement defect (AM7) stops the study.

## 5. Terminology (replaces "exactly-once" throughout)

These terms are used in all study documents and reports from v1.2 on. "Exactly-once" is not used for any property of this system.

| Term | Definition | Where it is measured |
|---|---|---|
| **Execution attempt** | a successful ledger claim for an approved action ID, followed by a call to the external tool | ledger row created; stand-in `received` |
| **At most one execution attempt per action ID** | the M4 property: a second claim for the same action ID fails, so no second call is made under that ID | count of `received` records per action ID ≤ 1 |
| **Confirmed external delivery** | the recipient stand-in recorded `delivered` for the action ID, **and** the ledger records `executed`. Only both together are confirmed, from the system's own point of view | stand-in plus ledger |
| **Delivery observed at the recipient only** | `delivered` at the stand-in, but the ledger not `executed`. In a real deployment the system cannot see this | stand-in only; reported, never counted as confirmed |
| **Ambiguous crash recovery** | after a failure at or after the claim, the ledger reads `executing` or `failed`; delivery may or may not have happened, and the system cannot tell which | ledger status, compared with the stand-in |
| **Duplicate transmission** | more than one `delivered` record for the content of one approved action, under one or several action IDs. Duplicates across action IDs are invisible to the ledger | stand-in, by payload digest and run |

**Replacement statements:**

- **§4a**, "The exactly-once guarantee depends on the ledger not being rolled back" becomes: "**The at-most-one-attempt property depends on the ledger not being rolled back.**"
- **§8a**, "exactly-once execution (M4), against attackers A1–A4, B and C, while the ledger isn't rolled back" becomes: "**at most one execution attempt per approved action ID (M4), against attackers A1–A4, B1 and C, while the ledger isn't rolled back**."
- **§8a "makes no claim of"** gains:
  - exactly-once delivery;
  - confirmed delivery after a failure at or after the claim;
  - automatic recovery of ambiguous actions;
  - duplicate prevention across action IDs;
  - any property against B2.
- **T1** "exactly one send with the approved digest", and **H6b/H6d**, are measured counts at the recipient stand-in. Reports must call them "observed sends", not guarantees.

## 6. Revised attacker model (replaces attacker B of v1.1 §5)

Two kinds of threat are kept apart:

- **checkpoint tampering by someone without key material** (A2–A5);
- **an attacker who holds key material** (B1, B2).

Operator key loss is neither of these. It is an availability failure (E6).

| ID | Capability | M1 | M2 | PC1 | M2 credited? | I2 claimed? |
|---|---|---|---|---|---|---|
| A1–A5 | as in v1.1 | as v1.1 | as v1.1 | as v1.1 | as v1.1 | A1–A4: yes. A5: no |
| **B1** | holds the **checkpoint encryption subkey** only (`derive_key(master, "checkpoint-aes-gcm")`); can decrypt and produce validly encrypted blobs; **cannot** compute approval digests or tokens | accepts what B1 encrypts | blocks non-allowlisted types | detects a changed destination, tool, server or payload, because B1 cannot re-sign (T17) | **yes** (H4) | **yes** |
| **B2** | holds the **master key** (`master.key` or `PRIVAGENT_MASTER_KEY`); derives the checkpoint key **and** the approval key K | accepts anything | blocks non-allowlisted types | **does not detect**: B2 can recompute the payload digest, the action digest and the approval token for any action | **yes**, for gadget construction only (H4 applies to B2 too, because gadget injection needs only the checkpoint key) | **no** |
| C | as in v1.1 | | | | | yes |

**B1 is an analytical construct.** In the current deployment the only stored secret is the master key, so a realistic key leak gives B2. B1 isolates what PC1 and M2 do against an attacker who can encrypt but cannot sign. Reports must say so.

**T17 attackers:** A4 in C0 and C2; B1 in C1, C3 and C4.

**New scenario T19 (H6e, confirmed-descriptive, C1 only, n = 30).** B2 rewrites a paused run's stored destination, recomputes the action digest and approval token with K, re-encrypts, and writes the blob back. The harness then resumes the run using the forged approval.

- **Prediction:** not detected by M1, M2 or PC1; one send to the modified destination per run.
- This **characterizes** the B2 gap. It is outside I2 by definition, never credited to any mechanism, and does not stop the study.
- **Safety:** the modified destination is a synthetic label (`"attacker-sink"`) at the stand-in, with no network.

## 7. Other added scenarios

### 7.1 E6, E7, E8 (exploratory, descriptive)

| ID | Scenario | Configurations | n | Reported as |
|---|---|---|---|---|
| E6 | Wrong key; missing key file | C0–C4 | 30 each | availability outcome: recovered, refused (error type), sends. **Never counted as tamper detection** |
| E7 | T8-flip without M1: altered state loaded, and whether the delivered payload digest equals the approved digest | C0, C2 | from T8-flip runs | counts only |
| E8 | T8 refusals split into authenticated and structural | C0–C4 | from T8 runs | counts only |

### 7.2 T20a–h / H7a–h: ledger recovery (confirmed-descriptive, C1; T20f also in C2)

**Seed namespace:** `20261113`. **n = 30 per cell.** Confirmed if the prediction holds in all runs; the Wilson interval is reported. Outside the H1–H5a family, and never credited to a mechanism's contribution.

| ID | Failure point | Prediction |
|---|---|---|
| H7a / T20a | crash after the claim, before the call | ledger `executing`; 0 `received`; the retry is refused (`duplicate_prevented`); the run is not halted |
| H7b / T20b | crash during the call, after the recipient recorded `delivered` | ledger `executing`; 1 `delivered`; the retry is refused |
| H7c / T20c | crash during the call, before the recipient processed it | ledger `executing`; 0 `delivered`; the retry is refused |
| H7d / T20d | crash after delivery, before completion is recorded | ledger `executing`; 1 `delivered`; the retry is refused. Variant: crash after completion is recorded gives `executed` |
| H7e / T20e | the client times out, then the recipient completes | ledger `failed`; 1 `delivered`; the retry is refused |
| H7f / T20f | concurrent approvals from 2, 4 and 8 processes on one local store | ≤ 1 `received` per action ID; every losing process ends without a send |
| H7g / T20g | the tool raises after delivery; separately, before it | ledger `failed` in both; 1 or 0 `delivered`; the retry is refused |
| H7h / T20h | the completion record fails after a successful call | ledger `executing`; 1 `delivered` |

**Main measure for every T20 scenario:** whether the ledger state lets the system tell delivered from not delivered. The prediction is **no**, for every `executing` and `failed` state. Reported per cell.

**Design probe (exploratory only, not a hypothesis).** The LR5 idempotent-recipient stand-in.

## 8. Units of analysis and independence

1. **Every reported n counts independent runs.** A run has its own temporary directory, store, seed and canaries, and is manipulated at most once.
2. **Derived observations** (several scan moments S1–S3 of one run, the D1–D5 conditions applied in sequence, criteria a–g, and timing repetitions inside one run) carry the run's `run_uid` and are flagged `derived = 1`. They are never counted as runs.
3. **Deterministic computations** (T16 cases) are reported as "deterministic, reproduced k times", without confidence intervals.
4. **Paired runs.** Runs sharing a canary seed across configurations (T9 timing) are reported as paired. Medians of paired differences are reported alongside the group medians.
5. **Report headers.** Every report states: independent runs, derived observations and deterministic repetitions, separately. Total row counts are never presented as a sample size.

## 9. Mandatory reporting rules

The confirmatory report must satisfy each rule. Each rule closes a documented exploratory issue. A reviewer checklist with one line per rule is part of the report.

| Rule | Closes | The report must |
|---|---|---|
| R0 | C0 | state independent runs, derived rows and deterministic repetitions separately (section 8) |
| R1 | C1 | report key failures only under E6, never as tamper detection, and state that `InvalidTag` cannot tell tampering from key loss |
| R2 | C2 | report checkpoint recovery (request restored) and execution outcome (confirmed delivery / ambiguous / none) as separate measures, in separate tables and figures. No figure may be titled "recovery success" for a combined measure |
| R3 | C3 | describe a retried ambiguous action as "second attempt prevented; delivery not recorded", never as "correct" or "recovered" |
| R4 | C4 | report the ledger state per run against the stand-in, and never call `executing` or `failed` "consistent with delivery" |
| R5 | C5 | report any recorder anomaly (there should be none, under AM7) as a defect |
| R6 | C6 | report size effects as leave-one-out contrasts only (C4 → C1 for M3, C2 → C1 for M1) |
| R7 | C7 | state size units explicitly ("per paused thread, summed over all blobs" or "per blob") |
| R8 | C8 | state latency units explicitly ("per call", or "per run, mean of calls") with the matching n |
| R9 | C9 | state, for microbenchmarks, what the summarized values are (single operations or run means) |
| R10 | AM5 | use only the terms of section 5; "exactly-once" must not appear except to say it is not claimed |
| R11 | AM15 | for every hypothesis, report both the test result and whether the point prediction was met |
| R12 | AM1 | list H5 as "retired, contradicted by exploratory evidence", and never among confirmed hypotheses |
| R13 | general | not describe the system as production-ready; not claim novelty for combining established mechanisms; not present passing tests as a general security guarantee; not claim that encryption protects against a key holder; not treat a canary scan with 0 hits as proof of confidentiality |

## 10. Summary of hypotheses after v1.2

| Family or role | Members | Test |
|---|---|---|
| Confirmatory family (Holm, 5 contrasts) | H1, H2, H3, H4, **H5a** | one-sided Fisher; Newcombe interval; point prediction reported (AM15) |
| Confirmed-descriptive (all-n rule, Wilson) | H6a–d (T18), **H6e (T19)**, **H5′ (T8-struct; with a ±0.10 equivalence margin for H5′-I)**, **H7a–h (T20)** | as specified per hypothesis |
| Invariants (stop on violation) | I1, I2 (I2 not claimed against A5 or B2) | zero violations |
| Failure-path predictions | F1–F4 | match or mismatch |
| Exploratory | E1–E8; the LR5 probe | descriptive |
| Retired | **H5** | not tested |

## 11. Updated run counts (independent runs)

| Scenarios | Runs |
|---|---|
| T1–T7, T10–T14, T17 (14 scenarios) × 5 configurations × 30 | 2,100 |
| T8-flip, T8-trunc, T8-meta × 5 × 30 | 450 |
| T8-struct (H5′): 4 × 75 + reference 60 | 360 |
| T18a–d (C1) | 120 |
| T19 (C1) | 30 |
| T20 in C1: a, b, c, e, h (5 × 30) + d with its variant (2 × 30) + f at 2, 4, 8 processes (3 × 30) + g in two variants (2 × 30) = 360; plus T20f in C2 (90) | 450 |
| T15, D1–D5 × 5 × 10 | 250 |
| T9 timing, 50 × 5 (warm-ups included, flagged) | 250 |
| E6 (2 × 5 × 30) | 300 |
| T16 | 10 deterministic cases |
| **Total** | **4,310 independent runs** (plus replacements for exclusions) |

## 12. Remaining methodological limitations

1. **Same-team design and analysis.** The investigators have seen the exploratory results. H5a, H5′, E7, E8 and AM15 were written with that knowledge. The mitigations are fresh seeds, a frozen method (G5) and the analysis script frozen before data. They reduce the risk of fitting the design to known data, but do not remove it. An analysis by a second person is recommended.
2. **The corpus is fixed.** The synthetic documents and records (MCP seed 42) are identical to the exploratory study. Results describe the mechanisms on this corpus.
3. **H5′ is close to a format property.** Its refusal prediction follows largely from MsgPack framing. Its value lies in the end-to-end, fail-closed behaviour and the M2-independence check. It says nothing about deliberate tampering, appended bytes or non-MsgPack blobs.
4. **H5a's C2 arm is 0% by construction.**
5. **B1 is not a realistic leak in the current deployment** (section 6). B2 is realistic, and against it neither PC1 nor I2 holds (T19).
6. **Ledger outcomes after a failure at or after the claim cannot be resolved** by the system (T20). Recovery of ambiguous actions needs recipient cooperation, which the real external server does not offer. No exactly-once property is claimed.
7. **Rollback and context integrity (P2, P3)** are still absent (v1.1 §4a; T18).
8. v1.1 limitations 3–10 still apply: all-or-nothing MCP connections, no erasure, plaintext metadata, in-memory provenance, real-server exactness, a single machine and writer, version dependence, synthetic data.
9. **Stand-ins.** Recipient and MCP behaviour are emulated. Results about the real external server rest on code reading (it has no idempotency key and keeps its log in memory), not on measurement.

## 13. Freeze record

This file cannot contain its own hash. On approval:

- its SHA-256 is recorded in `PREREGISTRATION_HASHES.md`, together with v1.1's hash and the exploratory snapshot hash;
- the approval time is written there.

After that, any change requires v1.3, made before any confirmatory data is collected.
