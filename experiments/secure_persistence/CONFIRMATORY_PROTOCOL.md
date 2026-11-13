# Confirmatory evaluation protocol

| | |
|---|---|
| Status | **draft for review.** No confirmatory data has been collected, and none will be until you approve this protocol and amendment v1.2 is frozen |
| Authoritative specification | `preregistration.md` v1.1 (SHA-256 `8363417c5aadac06f6d87709e0d97f659ecd9a61a1fbd5c8b7112d049583c358`), unchanged |

This protocol says how the pre-registration will be carried out. v1.1 is amended by **v1.2**, `preregistration_v1.2.md`, a separate, timestamped file. v1.2 is frozen with its own hash before any confirmatory run, and v1.1 itself is never edited. Where this protocol and v1.2 differ, v1.2 prevails.

## 1. Disclosure: what is already known

An exploratory study has been run and audited:

- `REPORT.md`, `EXPLORATORY_AUDIT.md` and `CORRECTIONS.md`;
- frozen in `snapshots/exploratory_persistence_v1_20261109/`.

Its outcomes are known to the investigators. The confirmatory study is therefore a pre-registered replication under the v1.1 design, not a blind test. The rule that follows: **v1.1's hypotheses, predictions and analyses are not changed in response to exploratory outcomes**, except where section 10 states a reason that does not depend on the outcome. One known conflict (section 9) is disclosed instead of amended away.

## 2. Gates (in order; none may be skipped)

| Gate | Condition | Evidence |
|---|---|---|
| G0 | You approve the five documents (this protocol, the audit, the corrections, the PC1/PC2 plan, the ledger analysis) | your written approval |
| G1 | Amendment v1.2 is frozen | file hash recorded in this protocol's revision log |
| G2 | PC1 and PC2 implemented per `PC1_PC2_IMPLEMENTATION_PLAN.md`; tests U1–U5, T16, T17a–c, R1 and R2 pass | test output |
| G3 | The PC3 harness is built in a new directory, `experiments/secure_persistence_confirmatory/`. It is validated **only on validation seeds** (master seed 20261108, never the confirmatory seeds), with n = 2 per cell, and the full analysis pipeline runs end to end on that validation data | validation CSVs and the analysis output, kept separately |
| G4 | PC4 reproduction check (plan section 5): C1 matches `DevApprovalStore`; the existing suites pass; the Attack Lab replay is byte-identical; the frozen hashes are unchanged | check log |
| G5 | **The methodology is frozen.** A SHA-256 manifest is taken of the harness, the analysis script, this protocol, amendment v1.2 and the environment lock. From here on, any change means stopping and writing a new amendment | `METHOD_FREEZE.sha256` |
| G6 | The confirmatory run, with confirmatory seeds | raw CSVs |
| G7 | Analysis with the frozen script only. Any extra analysis is labelled exploratory | tables and figures |
| G8 | The report: results against every prediction, every deviation, every exclusion | `CONFIRMATORY_REPORT.md` |

The exploratory harness (`experiments/secure_persistence/`) and its results are not modified. The confirmatory harness may copy code from it, but copies, never edits in place.

## 3. Configurations (v1.1 section 6; the ledger is on in every configuration)

| ID | M1 encryption | M2 strict decoding | M3 minimization | M4 ledger | PC1 / PC2 |
|---|---|---|---|---|---|
| C0 Baseline | off | off | off | **on** | on |
| C1 Full | on | on | on | on | on |
| C2 Full − M1 | off | on | on | on | on |
| C3 Full − M2 | on | off | on | on | on |
| C4 Full − M3 | on | on | off | on | on |

Construction follows v1.1 section 6:

- **M1 off:** the strict inner serializer without the encrypted wrapper.
- **M2 off:** `allowed_msgpack_modules=True` inside the encrypted wrapper.
- **M3 off:** a test-only monkeypatch of `minimize_state`.

The exploratory configurations A and F (ledger off) are **not** part of the confirmatory study.

Held constant: `durability="exit"`, purge of completed threads, owner-only file permissions, master-key derivation, the single flow rule, and the frozen models, thresholds and feature configuration (v1.1 section 2; hashes checked before and after the run).

## 4. Isolation and data

**Storage:**

- Every run gets a fresh temporary directory under the system temp directory, with a per-run name.
- The experiment factory refuses `runtime/approvals` and any path outside the temp directory.
- No deployed configuration or environment variable is read: `PRIVAGENT_MASTER_KEY` and `GOOGLE_API_KEY` are removed from the worker environment.

**Data:**

- The LLM is FakeLLM / a scripted LLM.
- Synthetic MCP content comes from the existing fixed seed 42.
- Each run gets its own canaries.
- No real payload is used, and there is no network.

**MCP stand-ins (PC3):**

- *Source servers* reproduce the real manager's connect-all behaviour, needed for T12a. That is checked once against `MCPClientManager` in G3.
- *A digest-recording external stand-in* writes, for every call, one file with an atomic rename. Each file holds:
  - action ID (out of band);
  - full-payload SHA-256;
  - destination, tool, server;
  - `received` / `delivered` markers.

  This addresses exploratory correction C5. Any `delivered` without `received`, or any unparsable record, is a measurement defect and stops the study (section 8).

**Probe object:** the benign `SideEffectProbe`, which writes a marker file. No commands are run and there is no network.

## 5. Scenarios, sample sizes and seeds

**Scenarios and sample sizes** follow v1.1 sections 7 and 11 exactly. The per-run seed is `SHA-256("20261109|<config>|<scenario>|<rep>")[:8]`. Configuration order per repetition is shuffled with seed 20261110.

| Scenarios | Configurations | n per cell | Independent runs |
|---|---|---|---|
| T1–T7, T10, T11, T12a, T12b, T13, T14, T17 (14) | C0–C4 | 30 | 2,100 |
| T8-flip, T8-trunc, T8-meta (v1.2 AM4) | C0–C4 | 30 each | 450 |
| T8-struct, H5′ (v1.2 §4; seed namespace 20261112) | C0, C2 × 2 targets; C1 reference | 75 per primary cell; 30 + 30 reference | 360 |
| T18a–d | C1 | 30 each | 120 |
| T19, H6e master-key forgery (v1.2 §6) | C1 | 30 | 30 |
| T20a–h ledger recovery, H7a–h (v1.2 §7.2; namespace 20261113) | C1; T20f also C2 | 30 per cell | 450 |
| T15, D1–D5 | C0–C4 | 10 per condition | 250 |
| T16 | none (deterministic) | each case once | 10 cases |
| T9 timing | C0–C4 | 50 (first 5 discarded) | 250 |
| E6 key availability | C0–C4 | 30 × 2 | 300 |
| **Total** | | | **4,310 independent runs** |

**Unit of analysis.** Every CSV row is **one independent run**, identified by `run_uid`. Where several measurements come from one run (scan moments S1–S3, the D1–D5 conditions applied in sequence, criteria a–g), they are columns of that row, or rows carrying the same `run_uid` and flagged `derived=1`. No table reports derived rows as trials (exploratory correction C0).

**Hard kill** is `TerminateProcess` of the pausing process (v1.1 section 7). Scan moment S1 is taken **after** the hard kill, without a WAL checkpoint. The exploratory study scanned in-process, which differs.

**Bootstrap.** 10,000 resamples. Each interval gets its own generator, seeded with `SHA-256("20261111|<metric>|<config>")[:8]`, so intervals don't depend on the order of computation (amendment item A6).

## 6. Hypotheses and analysis (v1.1 sections 8 and 13, unchanged)

| ID | Contrast | Prediction | Test |
|---|---|---|---|
| H1 | Raw exposure of payload and task-PII canaries, T6 at S1 | C2 = 100%, C1 = 0% | one-sided Fisher, Holm across H1–H5; Newcombe interval for the difference |
| H2 | Document-text and record-value canaries in decrypted blobs, T6 at S1 | C4 = 100%, C1 = 0% | same |
| H3 | Gadget constructed, T7 under A4 | C0 = 100%, C2 = 0% | same |
| H4 | Gadget constructed, T7 under B | C3 = 100%, C1 = 0% | same |
| ~~H5~~ | **Retired** (v1.2 AM1): contradicted by exploratory evidence; not tested | none | none |
| H5a | Authenticated refusal (`InvalidTag` or plaintext refusal) of byte flips and truncations, T8-flip + T8-trunc | C1 = 100%, C2 = 0% (by construction) | one-sided Fisher, Holm across H1–H4 and H5a; point prediction reported (v1.2 AM15) |
| H5′ | Structural refusal of truncated MsgPack blobs without M1; independent of M2 (T8-struct) | 100% in each C0/C2 × target cell; C2 − C0 within ±0.10 | all-n rule; Wilson per cell; Newcombe interval with equivalence margin. Outside the family; never credited to M1 or M2 |
| H6a–d, H6e | T18a–d; T19 (master-key holder B2) in C1 | as in v1.1; H6e per v1.2 §6 | all-n rule; Wilson interval; not in the family |
| I1, I2 | Recovery correctness (criteria a–g) and zero duplicate or modified transmissions in the listed scenarios; I2 not claimed against A5 or B2 | 100% / 0 | zero violations; any violation stops the study |
| F1–F4 | T12a, T12b, T13, T14 | as in v1.1 | match or mismatch per cell, with Wilson intervals |
| E1–E8 | E1–E5 as v1.1; E6 key availability; E7 byte-flip end-to-end without M1; E8 authenticated against structural refusals | descriptive | median, IQR, bootstrap CI of the median difference from C0; counts |
| H7a–h | T20a–h (v1.2 §7.2) | v1.2 §7.2 | all-n rule; not in the family |

**Reporting rules:**

- Checkpoint recovery and execution outcome are reported separately (exploratory correction C2), as v1.1's criteria a–g already allow.
- The ledger state is reported per run, with `executing` and `failed` described as "outcome not recorded", never as "consistent" (correction C4).

## 7. Exclusions (v1.1 section 12, unchanged)

A run may be excluded only for an infrastructure fault before the treatment point that doesn't depend on the configuration:

- the pause is not reached (outside T12 and T13);
- the temporary directory can't be created;
- the worker crashes before the manipulation.

Further rules:

- Each excluded run is replaced by the next seed, at most 3 replacements per cell.
- A cell with more than 10% exclusions is invalid.
- T12 and T13 failures are outcomes, never exclusions.

## 8. Stopping rules

The confirmatory analysis stops, and the defect is reported with reproduction details, on any of:

1. **An I1 or I2 violation.**
2. **A measurement defect** in the external stand-in: a `delivered` without `received`, or an unparsable record. Such a run is not excluded, because it is not a fault before the treatment point; it stops the study.
3. **A frozen hash that changes during the run.**
4. **A change to the harness or the analysis after G5.**

T18d's predicted second send is outside I2 by definition (v1.1) and does not stop the study.

## 9. A known conflict between v1.1 and the exploratory observations

H5 predicts that in C2 (no encryption), 0% of byte flips **and truncations** are refused at the storage layer. In the exploratory study, without encryption:

- a 20-byte truncation was refused in 60/60 runs by the MsgPack decoder (`ValueError`);
- a byte flip was refused in 1/60 runs.

H5's C2 prediction is therefore likely to fail for truncation. The cause is that a truncated MsgPack blob is structurally invalid, not that anything detects tampering.

**Options:**

- **(a) Keep H5 as registered (recommended).** Test it exactly as written, and report whatever outcome results. Add, as a *labelled exploratory* measure, the share of refusals attributable to authentication (`InvalidTag`, or the plaintext refusal) against structural decoding errors. This keeps the pre-registration intact, at the cost of a likely partial failure of H5's prediction that has to be reported honestly.
- **(b) Amend H5** so that only authenticated refusals count. This is better construct validity, but the change would be motivated by an observed outcome. It would have to be disclosed as such, and it weakens the confirmatory status of H5.

**This choice is yours.** The protocol proceeds with (a) unless you choose (b) before G1.

**Resolved, 2026-11-09:** you chose to amend. v1.2 retires H5 (AM1) and keeps it verbatim with the status "contradicted by exploratory evidence". It is replaced in the family by H5a, authenticated refusal (AM2). The exploratory observation is investigated separately as H5′ on fresh seeds (AM3, v1.2 §3.2 and §4). The exploratory 60/60 is never counted as evidence.

## 10. Proposed amendment v1.2

**Superseded by `preregistration_v1.2.md`.** That file is authoritative. It contains these items as AM5–AM13, plus AM1–AM4 (H5 retired; H5a; H5′; T8 split), AM14 (reporting rules) and AM15 (point-prediction reporting). The table below is the earlier draft, kept for the record:

| Draft item | Became |
|---|---|
| A1 | AM5 |
| A2 | AM6 |
| A3 | AM7 |
| A4 | AM8 |
| A5 | AM9 |
| A6 | AM10 |
| A7 | AM12 |
| A8 | AM13 |

Each item states what changes, why, and whether the reason depends on exploratory outcomes. None changes the configurations, the models, the datasets, H1–H5, I1 or I2.

| Item | Change | Reason | Outcome-dependent? |
|---|---|---|---|
| A1 | Section 8a: replace "exactly-once execution (M4)" with "at most one execution claim per approved action ID (M4); after a failure at or after the claim, delivery is not recorded and requires reconciliation with the recipient". Add this to the "makes no claim of" list: exactly-once delivery, and recovery of ambiguous (`executing` / `failed`) actions | v1.1's own design cannot support exactly-once: the claim, the call and the finish are separate steps, and the recipient has no idempotency key (LEDGER_RECOVERY_ANALYSIS.md section 1). This follows from the code, not from any outcome | No (code analysis); the exploratory R5 observation agrees with it |
| A2 | T17 and attacker B: T17's attacker can rewrite stored state but does not recompute HMACs. In encrypted configurations, that means holding only the derived checkpoint subkey. Add: "An attacker holding the master key can derive the approval key and forge approvals; PC1 does not address this, and no claim is made against it" | K is derived from the master key (v1.1 section 4), so v1.1's "B in all" prediction for T17 cannot hold for a master-key holder (PC1 plan section 4) | No (design analysis) |
| A3 | Metric 2 and criterion (f): the digest-recording stand-in writes one atomically renamed file per call. A record inconsistency is a measurement defect that stops the study (section 8) | Prevents the exploratory log-line loss (correction C5) | Measurement procedure only; affects no prediction |
| A4 | Add H7a–h as confirmed-descriptive scenarios LR1–LR8 (LEDGER_RECOVERY_ANALYSIS.md section 4), in C1, plus C2 for LR6, n = 30, with the predictions in section 4.2 of that document. They are not in the H1–H5 family and are never credited to a mechanism's contribution. LR5's idempotent recipient is a design probe, reported as exploratory | Characterizes the ledger's failure modes, which A1 makes explicit, in the same way H6 characterizes context-integrity gaps | No: predictions are derived from the code before any LR run |
| A5 | Add exploratory measure E6: wrong-key and missing-key recovery (availability) in C0–C4, n = 30, reported separately from metric 5 and never counted as tamper detection | Keeps key failures out of the tamper-detection measure (correction C1) | No (definition) |
| A6 | Bootstrap: one generator per interval, seeded as `SHA-256("20261111\|<metric>\|<config>")[:8]`, instead of one shared generator | Removes the dependence on computation order found in the exploratory analysis (audit section 3) | No |
| A7 | Server identity: the approved action's `mcp_server` is `MCP_SERVER_IDENTITY[TOOL_TO_SERVER[tool]]`, with `{"external": "external_server"}` | Records how v1.1's literal `"external_server"` maps to the code's routing key. Clarification only | No |
| A8 | Units: every reported n counts independent runs, and derived rows are flagged (section 5) | Correction C0 | No |

**H5:** no amendment unless you choose option (b) in section 9.

## 11. Mapping from the exploratory harness to the confirmatory harness

| Exploratory element | Confirmatory treatment |
|---|---|
| Configurations A–F | replaced by C0–C4, all with the ledger on |
| `configurations.ExperimentStore` | copied; `NullLedger` removed; must pass the G4 equivalence check with `DevApprovalStore` |
| Synthetic MCP (`harness.SyntheticMCP`) | replaced by PC3 stand-ins: connect-all source servers, plus the digest-recording external stand-in with atomic per-call files |
| Worker and fault injection (`worker.py`) | reused pattern; the hard kill becomes `TerminateProcess` of the pausing process, as v1.1 specifies |
| Confidentiality scan, in-process | redone at S1 (after the hard kill), S2 and S3, with metadata inventory 3b and the `thread_id` positive control |
| Encryption manipulations | T8 only covers byte flip, truncation and metadata edit; key failures move to E6 |
| Deserialization probe | reused; the attackers become A2, A4 and B as defined in v1.1 |
| Ledger L1–L5 | replaced by T3, T4 and T5, plus LR1–LR8 |
| Performance (40 runs) | T9: 50 runs, 5 discarded |
| `analysis/analyze.py` | replaced by a new analysis script written before G5 and run only on validation data before G6 |

## 12. Risks to validity that remain after this protocol

- **Same-team analysis.** The investigators know the exploratory results. Mitigation: the method is frozen (G5) and analysed by a script fixed before data collection. An analysis by a second person is recommended but not required by v1.1.
- **Synthetic stand-ins.** Real MCP servers and the real recipient are not used. v1.1 limitations 7 and 10 apply.
- **Single machine, Windows, a single SQLite writer.** v1.1 limitation 8 applies. LR6 tests several processes on one host only.
- **Version dependence.** v1.1 limitation 9 applies. The environment must match v1.1 section 2: Python 3.14.3, langgraph 1.2.19, langgraph-checkpoint 4.3.1, langgraph-checkpoint-sqlite 3.1.3, cryptography 42.0.2, SQLite 3.50.4. These match the exploratory `environment.json`.

## Revision log

| Date | Change |
|---|---|
| 2026-11-09 | Draft for review (G0 pending) |
| 2026-11-09 12:42 IST | Aligned with `preregistration_v1.2.md`: H5 retired; H5a, H5′, T19 and T20 added; I2 scope; run counts 4,310. G1 pending your approval of v1.2 |
