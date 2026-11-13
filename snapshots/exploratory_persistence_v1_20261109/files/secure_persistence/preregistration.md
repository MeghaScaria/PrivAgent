# Pre-registration: Secure Persistence Ablation Study

Version 1.1 · 2026-11-09 · Status: **frozen on approval**. Design document:
"Secure Persistence Ablation Study: Experimental Design" (claude.ai doc).

Changes from v1.0 (no confirmatory data had been collected):

- Added section 4a, which separates ciphertext authentication from checkpoint-context integrity and freshness.
- Added attacker capability A5 (restoring a full earlier snapshot of the store).
- Moved cross-thread swap and rollback out of T8 into a new scenario, T18 (four variants).
- Replaced H6 with H6a–H6d.
- Added metric 5b and explicit scope exclusions.

Configurations, the fixed ledger and every other part of v1.0 are unchanged.

This file fixes the hypotheses, attacker capabilities, configurations,
scenarios, metrics, seeds, sample sizes, exclusion criteria and analysis
before any confirmatory run. Its SHA-256 is recorded in the design
document when frozen. Changes after freezing require a new version, with
the reason stated, made before any confirmatory data is collected. Every
deviation from this file is reported with the results.

## 1. Purpose

Measure the individual contribution of three persistence mechanisms to the
security of paused human-approval runs, with a fourth held fixed:

| ID | Mechanism | Role in this study |
|---|---|---|
| M1 | AES-GCM checkpoint encryption | Ablation variable |
| M2 | Strict MsgPack deserialization (`allowed_msgpack_modules=None`, no pickle) | Ablation variable |
| M3 | Sensitive-state minimization (`minimize_state()` in `writer_compose`) | Ablation variable |
| M4 | Execution ledger (at-most-once send) | **Fixed: on in every configuration** |

## 2. Fixed conditions

- **Frozen artefacts unchanged** (SHA-256, first 16 hex), verified before and after the study:
  - `models/trajectory_level_model.pkl` e31d0b0717dc9bd1
  - `models/action_level_model.pkl` eadc63aee402c61a
  - `models/thresholds.json` e0deff4dac6c6a3d
  - `models/feature_config.json` 4ac02f5ff82754bd
  - `models/baselines/trajectory_invariant_v1/` (copies, same hashes)
- **Deployed behaviour unchanged.** The default pipeline (`build_graph` without approvals), the risk model, the thresholds, the policy rules and shadow-mode sensitivity all stay as they are. The Attack Lab replay must match `models/baselines/trajectory_invariant_v1/results/attack_lab_replay.md` byte for byte before and after.
- **Payload binding: option A (payload-bound).** The approved payload is stored verbatim (encrypted under M1) and never rebuilt from references.
- **Held constant in every configuration:** exit-only durability (`durability="exit"`), completed-thread purge, owner-only file access, master-key derivation, the M4 ledger, the single flow rule (`sensitive_crossed_agent_boundary_to_external`), and preconditions PC1–PC2 (section 3).
- **Environment** (recorded with the results): Python 3.14.3; langgraph 1.2.19; langgraph-checkpoint 4.3.1; langgraph-checkpoint-sqlite 3.1.3; cryptography 42.0.2; SQLite 3.50.4 (`secure_delete` default 0); Windows 11; CPU model and power plan recorded at run time.

## 3. Preconditions for confirmatory runs

None of these is implemented yet. Each must be implemented, reviewed and
verified (gate 3: reproduction check) before any confirmatory run. PC1 and
PC2 change the opt-in approval workflow only; the default pipeline and the
frozen model are unaffected. Once implemented, they are part of every
configuration.

| ID | Precondition | Why | Current state |
|---|---|---|---|
| PC1 | Pre-send verification: immediately before the MCP call, recompute the payload digest from the exact payload argument and the action digest from the exact call parameters (section 4), and compare them in constant time with the action digest bound in the verified approval token. On mismatch: refuse, claim no ledger entry, send nothing | Review point 2 | **Missing.** `authorize()` re-checks the payload digest and the token, but not the destination, tool or server actually used. A stored `destination` changed after review would be sent to |
| PC2 | Canonical encoding v1 (section 4) for the payload digest, the action digest and the approval token, with domain separation and MCP server identity | Review point 1 | **Partial.** The current code uses `json.dumps(sort_keys=True, default=str)` with default separators and ASCII escaping, no domain labels, and no server identity |
| PC3 | Test-only factory, MCP stand-ins and experiment worker under `experiments/secure_persistence/` | Toggling M1–M3 and the failure scenarios | Not built |
| PC4 | Reproduction check: C1 matches `DevApprovalStore` (with PC1–PC2), the existing approval and restart suites pass against it, and the Attack Lab replay and frozen hashes are unchanged | Integrity of the comparison | Not run |

## 4. Approved-action binding and canonicalization (v1)

**Keys.** `K = HMAC-SHA256(master_key, "approval-service")`, as today. Every
digest below is `HMAC-SHA256(K, label || 0x00 || message)`, with a distinct
ASCII label per use, so a digest of one kind can never be accepted as
another.

**Payload bytes.** The payload must be a Python `str` (anything else is
rejected). Its bytes are the UTF-8 encoding of that string exactly as it is
passed to the MCP call. There is no Unicode normalization, no trimming, no
line-ending conversion and no case folding.

`payload_digest = HMAC(K, "privagent/payload/v1" || 0x00 || payload_bytes)`, lowercase hex.

**Canonical JSON (CJ).** `json.dumps(obj, sort_keys=True,
separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, then UTF-8
encoded. Every value must be a `str` or an object of `str` values: no
numbers, booleans, nulls or lists, and no `default=` conversion. A value of
any other type is rejected, not converted. For string-only objects this
coincides with RFC 8785 (JCS).

**Approved action** (all fields required, all strings):

```
{
  "schema": "privagent-approved-action/1",
  "action_id": "<uuid4, lowercase, hyphenated>",
  "run_id": "<run id>",
  "agent_role": "writer",
  "mcp_server": "external_server",
  "tool": "send_result",
  "arguments": {"destination": "<destination>", "payload_digest": "<payload_digest>"},
  "decision_event_id": "<governance decision event id>"
}
```

`arguments` lists every argument passed to the MCP tool. `send_result` takes
exactly `payload` (bound through `payload_digest`) and `destination`. A tool
with other arguments needs a new schema version.

`action_digest = HMAC(K, "privagent/approved-action/v1" || 0x00 || CJ(approved_action))`

`approval_token = HMAC(K, "privagent/approval-token/v1" || 0x00 || CJ({"action_digest", "action_id", "decision": "approve", "reviewer"}))`

**What may share an approval.** Two payloads share an approval only if their
UTF-8 bytes are identical. Visually identical but different payloads get
different digests and need separate approval, including:

- NFC versus NFD forms,
- homoglyphs,
- zero-width characters,
- trailing whitespace,
- CRLF versus LF line endings.

The same holds for any difference in destination, tool, server, run or
action ID. Scenario T16 tests this.

**Pre-send verification (PC1)**, in this order, inside the execute step:

1. Rebuild `approved_action` from the exact `payload`, `destination`, `tool` and `mcp_server` about to be used.
2. Compare `action_digest` with the one bound in the token.
3. Verify the token.
4. Claim the ledger entry.
5. Make the call.

Any failure in steps 1–3 ends with no claim and no send, with the reason recorded.

## 4a. Checkpoint integrity: what AES-GCM does and doesn't provide

Three properties are kept separate. This study claims only the first.

| Property | Meaning | Provided today? |
|---|---|---|
| P1 Ciphertext authentication | A blob was produced by a holder of the checkpoint key and hasn't been altered since | **Yes, by M1** (AES-GCM tag). Tested by H5 |
| P2 Checkpoint-context integrity | A blob belongs to the thread, namespace, checkpoint, task and channel of the row it's read from | **No.** The associated data is the constant `privagent-checkpoint-v1`, so a genuine blob decrypts under any row. Characterized by T18a–b |
| P3 Freshness (rollback resistance) | The state read is the latest state written, not an older valid one | **No.** AES-GCM can't provide it, with or without context binding. Characterized by T18c–d |

**AES-GCM alone provides no rollback protection, and this study claims none.**

**Binding context with AEAD associated data** (investigated; not implemented; not part of this study):

- **Interfaces.** LangGraph's serializer and cipher interfaces receive no context: `dumps_typed(obj)` and `encrypt(plaintext)`. Only the saver knows `thread_id`, `checkpoint_ns`, `checkpoint_id`, `task_id`, `idx` and `channel`, in `put`, `put_writes`, `get_tuple` and `list`. Binding therefore needs a saver subclass that, for every blob:
  1. passes `AAD = CJ({"schema": "privagent-checkpoint/2", "kind": "checkpoint" | "write", "thread_id", "checkpoint_ns", "checkpoint_id", "parent_checkpoint_id" (checkpoints), "task_id", "idx", "channel" (writes)})`;
  2. on read, rebuilds the same associated data from the row's own columns, so a blob moved to another row fails authentication.
- **The plaintext metadata column** (`source`, `step`, `parents`) would also need to be authenticated: included in the associated data, or given a separate MAC.
- **A partial check exists today.** The checkpoint ID is also stored inside the encrypted checkpoint (`checkpoint["id"]`), so a moved checkpoint blob could be detected after decryption by comparing that field with the row. The thread ID isn't in the plaintext, and write blobs carry no IDs, so this check is incomplete without the saver change.
- **What binding would and wouldn't achieve.** It would detect substitution between threads and splicing between rows (P2). It wouldn't detect a rollback to an older consistent copy (P3), and it wouldn't detect a deleted row.

**Rollback against a restored snapshot (attacker A5).** If an attacker restores an earlier, internally consistent copy of the store directory (database, WAL, SHM and `ledger.sqlite`), nothing inside the store can tell it's old. Every blob is genuine and every binding matches. The consequences:

- A completed or rejected run reappears as paused.
- The ledger is rolled back too, so a fresh approval would send a second time. **The exactly-once guarantee depends on the ledger not being rolled back.**

Detecting this needs a reference the attacker can't write: a per-thread high-water mark, or the ledger itself, kept in a separate trust domain (an append-only remote service, or an OS- or TPM-protected monotonic counter) and checked before recovery and before every send. Binding an expiry time into the approved action would only limit how long a replay window stays open; it isn't detection. None of these is implemented, and none is claimed.

## 5. Attacker capabilities

| ID | Capability | M1 | M2 | M2 credited? |
|---|---|---|---|---|
| A1 | Reads the store's files; no key | Hides blob contents; plaintext columns stay readable | — | No (no deserialization) |
| A2 | Writes the files; no key; injects a foreign or plaintext blob | Rejects (unencrypted refused; wrong key fails the tag) | Not reached | **No** |
| A3 | Writes the files; no key; replays or swaps genuine blobs between rows of the live database | Accepts (constant associated data, so no P2) | Decodes only our own types | **No** (a context-integrity problem, T18a–c) |
| A4 | Writes the files; M1 off (C0, C2) | — | Blocks non-allowlisted types | **Yes** |
| B | Holds the checkpoint key (leaked `master.key` or `PRIVAGENT_MASTER_KEY`, insider) | Accepts anything they encrypt | Blocks non-allowlisted types | **Yes** |
| C | Shapes data our own process serializes (LLM or MCP text) | Encrypts normally | Not exercised: the state holds only plain values | No |
| A5 | Restores a full earlier copy of the store directory, including `ledger.sqlite` (backup restore, filesystem snapshot); no key | Accepts: every blob is genuine (no P3) | Not involved | No (a freshness problem, T18d) |

Out of scope: reading process memory, malware running as the same user,
administrators, and the safety of the library's built-in type allowlist.

## 6. Configurations

| ID | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| C0 Baseline | off | off | off | on |
| C1 Full | on | on | on | on |
| C2 Full − M1 | off | on | on | on |
| C3 Full − M2 | on | off | on | on |
| C4 Full − M3 | on | on | off | on |

How each is built: M1 off = strict `JsonPlusSerializer` without the
encrypted wrapper. M2 off = `allowed_msgpack_modules=True` inside the
encrypted wrapper. M3 off = a test-only monkeypatch of `minimize_state`.

## 7. Scenarios and expected outcomes

Hard kill = `TerminateProcess` / `SIGKILL` of the pausing process, so the
WAL is not checkpointed.

| ID | Scenario | Expected outcome |
|---|---|---|
| T1 | Pause, hard kill, new process recovers and approves | Same action and payload; exactly one send with the approved digest |
| T2 | Pause, hard kill, new process recovers and rejects | Same action; no send |
| T3 | Approve; process dies right after the send, before the ledger update; a new process approves again | Second send blocked by the ledger |
| T4 | Approve; the tool raises after sending; retry in the same process | Second send blocked by the ledger |
| T5 | Duplicate resume after completion (helper and raw `Command(resume)`) | No second send |
| T6 | Pause, hard kill, scan all artifacts (section 9) | Per hypotheses H1–H2 |
| T7 | Inject a gadget blob into a paused thread, then resume (A2, A4, B) | Per H3–H4; no send whenever the gadget is blocked |
| T8 | Tamper in place with a paused thread's stored data, then resume: byte flip, truncation, metadata edit | Byte flip and truncation per H5; a metadata edit isn't detected at the storage layer (the column isn't authenticated) |
| T9 | Timed runs | Descriptive |
| T10 | Source document edited between approval and resume (stand-in server: same IDs, new content) | Approved payload sent unchanged; the change is not detected (option A) |
| T11 | Source document deleted before resume | As T10 |
| T12a | Source servers unreachable at recovery; **exact approved payload preserved locally** (the normal option A state) | Review recovered intact (same action ID and payload digest). The send fails closed, because MCP connects all servers at once: no send, ledger `failed`, no retry. Reported as **"payload intact, availability failure"** |
| T12b | Source servers unreachable at recovery; **only a reference preserved** (the harness replaces the stored payload with a stub reference; attackers A4/B or the harness only) | **Fail closed:** no send, no ledger claim, refusal reason recorded. Reported as **"reference only, fail closed"** |
| T13 | External server unreachable at execution | No send; ledger `failed`; not retried; the approved action is lost |
| T14 | References unresolvable (fresh process; a stub altered under A4/B) | Send unaffected; closing provenance unknown |
| T15 | Run completes and is purged, then every artifact is scanned under deletion conditions D1–D5 | Exploratory (E2) |
| T16 | Canonicalization cases: NFC/NFD, homoglyph, zero-width, trailing space, CRLF/LF, and changed destination, tool, server, run or action ID | Every variant gets a different digest; approving one never authorizes another |
| T17 | A stored pending-action field (destination, tool, server) is changed before resume (A4 in C0/C2; B in all) | Refused by PC1 before any send or ledger claim |
| T18a | **Cross-thread substitution, checkpoint only** (A3): two runs X and Y are paused; X's `checkpoints` blob is replaced with Y's; X's `writes` row (the review request) is left alone. Recover and approve X's presented request | Storage layer: not detected (P2 absent). End to end: the approval carries X's action ID, but the restored state holds Y's, so it's rejected as `action_id_mismatch`. No send |
| T18b | **Cross-thread substitution, consistent** (A3): X's `checkpoints` and `writes` rows both replaced with Y's. Recover X and approve what's presented; afterwards resume Y | Not detected at either layer. X's reviewer is shown and approves Y's action, which is sent once under X's thread. Resuming Y then hits the ledger and doesn't send again. Reported as "wrong-thread execution, at most once per action" |
| T18c | **Same-thread rollback in the live database** (A3): X is approved, sent and purged; then X's earlier paused rows (copied beforehand) are re-inserted, with the ledger untouched. Recover and approve again | Not detected at the storage layer (P3 absent). The ledger claim fails, so there's no second send |
| T18d | **Full-snapshot rollback** (A5): copy the whole store directory while X is paused; approve and send X; restore the copy, ledger included; recover and approve again | Not detected anywhere. A second send is expected, because the ledger was rolled back. This is predicted, excluded from I2 and from the security claims (section 8a), and does not stop the study |

**T15 deletion conditions**, each applied after a completed, purged run.
The settings are applied on the harness's connection; nothing in deployed
code changes.

| ID | Condition |
|---|---|
| D1 | Logical deletion only: `delete_thread`, `secure_delete` = 0, no WAL checkpoint |
| D2 | `PRAGMA secure_delete = 1` set before the deletion, no WAL checkpoint |
| D3 | D1, then `PRAGMA wal_checkpoint(TRUNCATE)` |
| D4 | D2, then `PRAGMA wal_checkpoint(TRUNCATE)` |
| D5 | D4, then `VACUUM`, then `PRAGMA wal_checkpoint(TRUNCATE)` |

No result is reported as guaranteed or forensic erasure. Out of scope:
filesystem journaling and slack space, SSD wear-levelling and remapping,
the OS page cache, backups and sync clients, temporary files SQLite
creates during `VACUUM` (also scanned where found), and process memory.

## 8. Hypotheses

**Confirmatory contrasts** (family for multiplicity: H1–H5).

| ID | Hypothesis | Measure, scenario, moment | Prediction |
|---|---|---|---|
| H1 | M1 prevents raw exposure of checkpoint content | Payload and task-PII canaries in raw artifact bytes; T6 at S1 | C2 = 100%, C1 = 0% |
| H2 | M3 prevents exposure of retrieved content to a key holder | Document-text and record-value canaries in decrypted blobs; T6 at S1 | C4 = 100%, C1 = 0% |
| H3 | M2 blocks gadget construction when M1 is absent (A4) | Gadget constructed; T7 | C0 = 100%, C2 = 0% |
| H4 | M2 blocks gadget construction against a key holder (B) | Gadget constructed; T7 | C3 = 100%, C1 = 0% |
| H5 | M1 detects in-place tampering at load | Byte flip and truncation refused at the storage layer; T8 | C1 = 100%, C2 = 0% |

**Confirmatory descriptive** (characterizing known gaps, run in C1 only; each
reported with a Wilson interval and confirmed if the predicted outcome
occurs in every run):

| ID | Scenario | Prediction |
|---|---|---|
| H6a | T18a | 0% storage-layer detection, 100% end-to-end refusal, 0 sends |
| H6b | T18b | 0% detection at either layer; exactly one send per action ID across X and Y |
| H6c | T18c | 0% storage-layer detection; 0 additional sends (the ledger holds) |
| H6d | T18d | 0% detection; exactly one additional send per run |

T18 is run in C1 only. In C0 and C2 an attacker can forge blobs outright, so
substitution adds nothing to measure. C3 and C4 don't change context
binding, so they would behave exactly like C1. The five configurations are
unchanged.

**Invariants** (must hold in every configuration; any violation is a defect
and stops the study):

- **I1.** Recovery correctness = 100% for T1, T2, T10, T11 and T14 (criteria a–g, section 9).
- **I2.** Duplicate or modified transmissions = 0 for T1, T3, T4, T5, T10, T11, T16 and T17. I2 is claimed against attackers A1–A4, B and C, and only while the ledger hasn't been rolled back. T18d's predicted second send is outside I2 by definition.

**Failure-path predictions** (compared with the prediction, reported per
cell):

- **F1:** T12a.
- **F2:** T12b.
- **F3:** T13.
- **F4:** T14.

**Exploratory** (descriptive only; no claims of contribution):

| ID | Measure |
|---|---|
| E1 | Plaintext metadata inventory (3b) at S1, S2, S3 |
| E2 | T15 leftovers by deletion condition D1–D5 |
| E3 | Storage size (6) |
| E4 | Recovery and write latency (7, 8) |
| E5 | Runtime overhead (9) |

## 8a. Scope of the security claims

The study's claims cover:

- ciphertext authentication (P1, under M1);
- resistance to malicious deserialization (M2, against attackers A4 and B);
- reduced checkpoint content (M3);
- exactly-once execution (M4), against attackers A1–A4, B and C, while the ledger isn't rolled back.

It explicitly **makes no claim** of:

- checkpoint-context integrity (P2);
- freshness or rollback resistance (P3), against A3 within a live database or against A5 snapshot restores;
- integrity of the plaintext metadata column;
- erasure.

T18 is in the confirmatory protocol only to characterize these gaps (H6a–H6d). Its results aren't counted as evidence for or against any mechanism's contribution.

## 9. Metrics

- **1 Recovery correctness.** A run counts as correct only if all of these hold:
  - (a) it resumes in a new process;
  - (b) the action ID equals the original;
  - (c) the payload digest equals the approved digest;
  - (d) the outcome matches the decision;
  - (e) the send count is exactly as expected for the scenario;
  - (f) the full-payload digest, destination, tool and server at the receiving stand-in equal the approved action;
  - (g) no other send occurs for that run.

  Each criterion is also reported separately.
- **2 Duplicate or modified transmissions.** Count of sends beyond one per approved action, or of sends whose recorded digest differs from the approved one. Counted at the digest-recording external stand-in in every process.
- **3a Checkpoint-content exposure.** Share of canaries found, per class (payload, task PII, document text, record values, analysis text), in (i) raw bytes and (ii) decrypted blobs.
- **3b Plaintext metadata exposure.** An inventory of readable values outside blobs, by class:
  - identifiers (thread, checkpoint, task, action IDs);
  - workflow position (`task_path`, `channel`, `step`);
  - timing (time-ordered checkpoint IDs, ledger timestamps);
  - caller-supplied values (a deliberate canary in `thread_id` as a positive control);
  - leftovers after purge.
- **4 Malicious deserialization.** Share of gadget blobs not constructed and leading to no send. Credited to M2 only for A4 and B.
- **5 Tampering detection (in place).** Share of in-place modifications (byte flip, truncation, metadata edit; T8) refused at the storage layer, reported separately from those refused by the approval layer. Measures P1.
- **5b Context and freshness detection.** For T18a–d: the share detected at the storage layer, the share refused end to end, and the number of sends per action ID (counted at the digest-recording stand-in). Measures the absence of P2 and P3; never credited to any mechanism.
- **6 Storage size.** Summed blob bytes; file bytes of all artifacts after `wal_checkpoint(TRUNCATE)`.
- **7 Recovery latency.** From opening the store to `pending_review()` returning (ms); resume-to-send latency separately (it includes MCP start-up).
- **8 Write latency.** Per `put` / `put_writes` at the pause (ms).
- **9 Runtime overhead.** End-to-end time to pause and to completion relative to C0 (ms and %).

**Artifacts scanned for 3a, 3b and T15:** every file in the store directory
matching `checkpoints.sqlite*` and `ledger.sqlite*` (database, `-wal`,
`-shm`, `-journal`), plus a listing of unexpected files in the directory and
in the system temp directory created during the run. `master.key` is
reported by presence and access only, never scanned as exposure.

**Scan moments:**

| ID | When |
|---|---|
| S1 | After the pausing process is hard-killed (abnormal termination; WAL not checkpointed) |
| S2 | After recovery completes and the recovering process exits normally |
| S3 | After each T15 deletion condition |

## 10. Seeds

- Master seed **20261109**. The seed for each run = the first 8 bytes of `SHA-256("20261109|<config>|<scenario>|<rep>")`. It drives canary strings, thread IDs (random hex that never contains a canary, except the 3b positive control), and gadget and tamper offsets.
- Configuration order per repetition: a seeded shuffle with seed **20261110**.
- Bootstrap resampling seed: **20261111**.
- Synthetic MCP data: the existing fixed seed 42 in `mcp_servers/` (unchanged), so document and record content is identical across runs; canaries are per run.
- The LLM is FakeLLM with scripted outputs. No real API key is present in any worker's environment.

## 11. Sample sizes

| Scenarios | n per configuration | Basis |
|---|---|---|
| T1–T8, T10–T14, T17 | 30 | Predicted rates are 0% or 100%; 0 of 30 has a Wilson 95% upper bound of about 11% |
| T18a–d (C1 only) | 30 each | Same basis |
| T15 (per deletion condition D1–D5) | 10 | Exploratory |
| T16 | Each canonicalization case once (deterministic) | All must pass |
| T9 (timing) | 50; the first 5 are discarded as warm-up | Median and IQR |

## 12. Exclusion criteria

- A run is excluded **only** for an infrastructure fault before the treatment point that doesn't depend on the configuration:
  - the pausing process fails before reaching the pause (in scenarios other than T12 and T13);
  - the temporary directory can't be created;
  - the worker crashes before the scenario's manipulation.
- Failures in T12 and T13 are **outcomes**, never exclusions. No run is excluded because of its outcome.
- Every exclusion is logged with its seed and reason. An excluded run is replaced with the next seed, at most 3 replacements per cell. A cell with more than 10% exclusions is reported as invalid and not analysed.

## 13. Analysis

- **Every cell:** proportion with a Wilson 95% interval.
- **H1–H5:** one-sided Fisher exact test in the predicted direction for each contrast, Holm-adjusted across the five. A hypothesis is confirmed if the adjusted p < 0.05 and the direction matches. The difference in proportions is reported with a Newcombe hybrid-score 95% interval.
- **H6a–H6d:** each confirmed if its predicted outcome occurs in all n runs in C1; the Wilson interval is reported. Not part of the H1–H5 multiplicity family. A mismatch is reported as a finding about the gap, never as a mechanism's contribution.
- **I1, I2:** pass only with zero violations in every cell. A violation is reported as a defect with its reproduction details, and confirmatory analysis stops.
- **F1–F4:** observed result versus prediction per cell (match or mismatch), with Wilson intervals. T12a and T12b are always reported separately.
- **E1–E5:** descriptive. Timing: median, IQR, and a bootstrap 95% interval (10,000 resamples) of the median difference from C0. No other tests.
- **No additional confirmatory tests.** Any further analysis is labelled exploratory.

## 14. Unresolved limitations

1. **PC1 and PC2 are required but not implemented.** They change the opt-in approval workflow, not the default pipeline. Until they exist and pass gate 3, no confirmatory run can start.
2. **No context integrity and no freshness (section 4a).** The associated data is constant, so genuine blobs can be moved between threads or rows (T18a–c). An older snapshot of the whole store, ledger included, is indistinguishable from the current one (T18d), and it allows a second send after a fresh approval. Binding the context needs a saver subclass; rollback detection needs a reference outside the store's trust domain. Neither is implemented or claimed.
3. **All-or-nothing MCP connections.** An unreachable source server blocks the external send (T12a), turning an intact, recoverable payload into an availability failure.
4. **No erasure guarantee.** Even D5 leaves the filesystem, SSD, OS caches, backups and memory out of scope.
5. **Plaintext metadata.** It exists in every configuration (thread and checkpoint IDs, `task_path`, timing) and isn't addressed by M1–M3.
6. **In-memory provenance.** The provenance registry and monitor are lost on restart, so closing provenance after recovery is unknown in every configuration.
7. **Real-server exactness.** The real external server keeps only the length and first 100 characters of a payload, so full-payload checks rely on the harness stand-in.
8. **Single machine and single writer.** SQLite only; no claims about multi-worker deployments.
9. **Version dependence.** C3's behaviour depends on the installed langgraph-checkpoint's permissive default, which is pinned for the study.
10. **Synthetic data.** Fixed-seed MCP content and scripted LLM outputs. Results describe the mechanisms, not real-world data distributions.
