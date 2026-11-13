# Ledger recovery: analysis and test design

| | |
|---|---|
| Status | analysis and test design; none of the tests below has been run |
| Sources | `governance/approval.py` (`ExecutionLedger`), `agents/approval_flow.py` (`_execute`), `agents/tools.py`, `agents/mcp_client.py`, `mcp_servers/external_server/server.py`; exploratory R5 and L3 data |

The determinations in section 3 are derived from reading the code, unless they are marked *observed*. Each one names the test that would confirm or refute it.

**Registration.** These tests are registered in `preregistration_v1.2.md` §7.2:

| Here | In v1.2 |
|---|---|
| LR1 | T20a |
| LR2a | T20b |
| LR2b | T20c |
| LR3 | T20d |
| LR2c | T20e |
| LR6 | T20f |
| LR7 | T20g |
| LR8 | T20h |

LR4 is reported within T20a and T20d. LR5 stays an exploratory design probe. The terms "execution attempt", "confirmed external delivery" and "ambiguous crash recovery" are defined in v1.2 §5.

**No claim of exactly-once delivery is made.** The ledger provides at most one *claimed attempt* per action ID, within one SQLite ledger that has not been rolled back.

## 1. How execution works today

`_execute` (`agents/approval_flow.py`) does these steps, in order, for an authorized action:

1. `ledger.claim(action_id, …)`. This INSERTs a row with status `executing` and commits, in its own connection. If the row already exists, it returns False, which leads to outcome `duplicate_prevented` with no call.
2. `tools.execute_send(...)`, which calls `MCPClientManager.call_tool("send_result", {payload, destination})` with `timeout=30`.
3. On an exception: `ledger.finish(action_id, "failed")`, then re-raise.
4. On success: `ledger.finish(action_id, "executed")`.

Properties that matter for recovery:

| # | Property | Consequence |
|---|---|---|
| P-a | Claim, call and finish are three separate steps; only the claim and the finish are durable writes | a crash between them leaves `executing` |
| P-b | The ledger has three statuses: `executing`, `executed` and `failed`. Nothing ever revisits `executing`; there is no timeout, no sweep and no reconciliation API | a stuck entry stays stuck |
| P-c | A later claim on the same action ID fails, whatever the existing status is | after any crash past step 1, the action can never be sent again under that action ID, whether or not it was delivered |
| P-d | `duplicate_prevented` does not halt the run (`task_halted` is set only for other non-executed outcomes) | after a retry, an unresolved action looks like a correctly prevented duplicate |
| P-e | The real recipient (`external_server.send_result`) takes only `payload` and `destination`. It has no action ID or idempotency key, and its log lives in process memory, holding only the payload length and first 100 characters | the recipient cannot deduplicate, and cannot be asked "did action X arrive?". Its log is lost when the server restarts |
| P-f | `call_tool` waits up to 30 s (`future.result(timeout=30)`). On timeout it raises, but the coroutine may still complete | `failed` can mean delivered: the send may finish after the timeout |
| P-g | An exception raised *after* the recipient processed the call (a response parsing error, `isError`, a dropped connection) also leads to `failed` | `failed` is also ambiguous |
| P-h | `finish()` can itself fail (for example `database is locked` after 10 s) after a successful send | `executing` remains, although the call returned |
| P-i | The ledger file sits in the same store directory as the checkpoints | restoring an older copy of the directory (attacker A5, or a backup) rolls the ledger back, and a fresh approval sends again (pre-registration section 4a) |

## 2. What the exploratory data already shows

- **R5, crash after the send but before `finish()`.** *Observed* in 120/120 trials (B–E):
  - the ledger stays `executing`;
  - exactly 1 delivery;
  - the retry was approved by the reviewer and refused by the ledger;
  - the run completed with outcome `duplicate_prevented`.

  This confirms P-a, P-c and P-d for one crash point.
- **L3, double-click in one process.** *Observed:* with a ledger, 0/120 duplicates; without one, 25/30 (A) and 30/30 (F). Only two threads in one process were tested, so separate processes are untested.
- **Not observed.** A crash between claim and call, a crash during the call, a timeout, an exception after delivery, a `finish()` failure, and concurrency across processes.

## 3. Outcome classification

"Safely recoverable" means the system can reach a correct, known state without human judgement and without risking a duplicate or a silent loss.

| # | Failure point | Ledger after the failure | Delivered? | Can the system tell? | Retry under the same action ID | Classification | Confirming test |
|---|---|---|---|---|---|---|---|
| F1 | Crash before approval is recorded (R3) | no row | no | yes | re-approval leads to 1 send | **Safely recoverable** (needs re-approval). *Observed* 30/30 per configuration | none needed |
| F2 | Crash after approval, before claim (R4) | no row | no | yes | re-approval leads to 1 send | **Safely recoverable** (needs re-approval; the approval is not persisted under `durability="exit"`). *Observed* 30/30 | none needed |
| F3 | Crash after claim, before the call | `executing` | **no** | **no**: identical to F5 | refused (`duplicate_prevented`) | **Manual intervention.** The action is silently lost, and the run reports a prevented duplicate | LR1 |
| F4 | Crash during the call (client dies, recipient may or may not have processed it) | `executing` | unknown | no | refused | **Manual intervention**; needs reconciliation with the recipient | LR2a, LR2b |
| F5 | Crash after delivery, before `finish()` (R5) | `executing` | yes | no: identical to F3 | refused | **Manual intervention.** No duplicate (*observed*), but the outcome is unrecorded | LR3 |
| F6 | Call times out (30 s) but completes later | `failed` | possibly | no | refused | **Manual intervention**; `failed` is ambiguous | LR2c |
| F7 | Tool raises after the recipient processed the call (pre-registration T4) | `failed` | yes | no | refused | **Manual intervention.** No duplicate, but the record says failed | LR7 |
| F8 | Tool raises before the recipient processed it (recipient unreachable, pre-registration T13) | `failed` | no | no (in general) | refused | **Manual intervention** (pre-registration: "the approved action is lost") | LR7 |
| F9 | `finish()` fails after a successful call | `executing` | yes | no | refused | **Manual intervention** | LR8 |
| F10 | Crash after `finish()`, before the run completes | `executed` | yes | yes | refused (correct) | **Safely recoverable.** The record is accurate, and the retry is a true duplicate | LR3 (variant) |
| F11 | Concurrent approvals across processes, local disk | one `executing`/`executed` row | 1 (prediction) | yes | the losers get `duplicate_prevented`, `NoPendingApproval` or `OperationalError` | **Safe for duplicate prevention** (prediction); the losing runs may end in an error | LR6 |
| F12 | Ledger rolled back (snapshot restore, A5) | an older state | possibly 2 | no | allowed: a second send | **Not protected** (pre-registration section 4a, T18d) | out of scope here |

**Summary:**

- Only F1, F2 and F10 are safely recoverable, plus duplicate prevention in F11 (predicted).
- Every state in which the ledger reads `executing` (F3, F4, F5, F9) or `failed` (F6, F7, F8) is **ambiguous about delivery** and needs a human decision.
- The current recipient cannot help settle that decision (P-e). The resolution path is reconciliation with the recipient, and today that has to happen out of band.
- The design always fails towards **non-delivery rather than duplication**: at most once. It never guarantees delivery.

## 4. Test designs

### 4.1 Common conditions

Every test uses the following set-up:

- **Isolation.** Each trial gets its own temporary directory, and the experiment factory refuses the deployed path. Data is synthetic only; there is no network and no real MCP.
- **Store.** Configuration C1/B: encryption, strict deserialization, minimization and the ledger all on. LR6 also runs in C2.
- **Recipient stand-in.** It records `received` (before processing) and `delivered` (after processing) lines for every call, each with the action ID passed out of band by the harness. Writes go to one file per call with an atomic rename, so concurrent writers cannot overwrite each other (lesson from exploratory C5). A trial is invalid if a `delivered` line has no `received` line.
- **Fault injection** through monkeypatches in a separate worker process, with exit codes per fault point and a hard kill (`os._exit`), the same as the exploratory `worker.py`.
- **Measured per trial:**
  - ledger rows: status, `claimed_at`, `finished_at`;
  - recipient `received` / `delivered` counts;
  - the recovered run's outcome, `task_halted` and halt reason;
  - the review queue's view of the run;
  - the outcome of a retry under the same action ID.
- **Sample size.** n = 30 per test and configuration. The outcomes are predicted to be deterministic, and 0/30 bounds a rate below 11.4%.

### 4.2 Tests

| ID | Fault | Injection | Predicted result (from code) |
|---|---|---|---|
| LR1 | Crash after claim, before the call | wrap `ledger.claim`: after it returns True, `os._exit(73)` | ledger `executing`; received 0; delivered 0. The retry is refused (`duplicate_prevented`), the run is not halted, and nothing is ever delivered. The ledger state is identical to LR3 |
| LR2a | Crash during the call, recipient processed | stand-in writes `delivered`, then the worker exits before `call_tool` returns | ledger `executing`; delivered 1; retry refused |
| LR2b | Crash during the call, recipient not processed | stand-in writes `received`, then the worker exits before processing | ledger `executing`; delivered 0; retry refused. Same ledger state as LR2a |
| LR2c | Timeout | stand-in sleeps past a reduced client timeout (set by the harness), then records `delivered` | ledger `failed`; delivered 1 after the timeout; retry refused |
| LR3 | Crash after delivery, before `finish()` (replicates exploratory R5 with the new recorder) | wrap `execute_send`: after return, `os._exit(72)` | ledger `executing`; delivered 1; retry refused, run completes as `duplicate_prevented`. **Variant LR3b:** crash right after `finish()` gives ledger `executed`, delivered 1, retry refused |
| LR4 | Recovery of a stuck `executing` action, current behaviour | after LR1 or LR3: (i) retry 3 times under the same action ID; (ii) restart the task (new run and action ID) and approve; (iii) inspect what the review queue and the audit log show | (i) 0 further sends, `duplicate_prevented` each time, no alert. (ii) a new action ID is claimed and delivered, so after LR3 the recipient has **2 deliveries of the same content**: the ledger cannot see duplicates across action IDs. (iii) nothing marks the action as needing attention |
| LR5 | Reconciliation with the recipient | two stand-ins: **R-plain** behaves like the real server (no action ID, in-memory log); **R-idem** accepts an `idempotency_key` = action ID, deduplicates, and answers `query(action_id)` with `delivered`, `unknown` or `not_received`. The LR1, LR2a, LR2b and LR3 states are each resolved by an experimental reconciler under `experiments/` that maps `delivered` to marking `executed`, `not_received` to marking `failed_not_sent` and requiring a new approval, and `unknown` to manual handling | R-plain: no state can be resolved (0/120). R-idem: all four resolved correctly, with no duplicate and no auto-resend. **LR5 is a design probe.** R-idem needs a new tool signature (pre-registration R2.10: a new schema version), so it is not a property of the current system |
| LR6 | Concurrent approval across separate processes | 2, 4 and 8 worker processes open the same store, wait on a file barrier and submit the same approval. Variants: (a) local disk; (b) one process holds a write lock longer than the 10 s busy timeout | (a) exactly 1 claim and 1 delivery; the others get `duplicate_prevented`, `NoPendingApproval` or a checkpoint write conflict; record every process's exit state and the final checkpoint. (b) the blocked process raises `OperationalError` in `claim` and sends nothing; the run errors. Multiple hosts and network file systems are not tested and not claimed |
| LR7 | Tool raises after or before the recipient processed it (pre-registration T4 / T13) | stand-in records `delivered`, then raises; separately, it raises before recording | ledger `failed` in both cases; delivered 1 or 0; retry refused in both. `failed` does not tell them apart |
| LR8 | `finish()` fails | wrap `ledger.finish` to raise `OperationalError` once | ledger `executing`; delivered 1; the run errors |

Reported per test:

- the counts;
- the ledger state;
- whether the state was **distinguishable** from the other states with the same ledger value, using only system-side information;
- **classification:** safely recoverable, or manual intervention.

## 5. Mitigation options (not implemented, not part of PC1/PC2)

These are listed so you can decide whether any belongs in a later design phase. None makes delivery exactly-once without the recipient's cooperation.

1. **Surface ambiguous states.**
   - Halt the run and flag it when the claim fails and the existing status is not `executed`. Today `duplicate_prevented` hides F3–F9 (P-d).
   - Show `executing` entries older than a threshold in the review queue as "outcome unknown: reconcile".

   This is low-risk, but it does change production behaviour.
2. **Record intent.** Write a `sending` status, with a timestamp, immediately before the call. This narrows F3 against F4/F5 (a crash before the intent record is a definite non-send). It does not remove the ambiguity between the intent record and `finish()`.
3. **Recipient idempotency key.** Pass the action ID to the recipient, which deduplicates and can be queried. That is the only option here that turns an ambiguous state into a known one. It changes the tool's signature (new approved-action schema version) and requires the external system to support it. With it, the property becomes: *at most one effect at a cooperating recipient per action ID, and resolvable outcomes*. It is still not exactly-once across recipients that do not cooperate.
4. **An operator reconciliation procedure.** It would cover:
   - listing ambiguous entries;
   - checking with the recipient out of band;
   - marking `executed` or `failed_not_sent` with the operator's identity;
   - for a non-delivery, requiring a fresh approval under a new action ID.

   Never automatically re-send an ambiguous action.
5. **Rollback (F12).** A ledger reference outside the store's trust domain, as described in pre-registration section 4a. Out of scope.

## 6. Precise claim supported today

> Within one non-rolled-back SQLite ledger on a local disk, each approved action ID is claimed for execution at most once. After a crash or error at or after the claim, the action is never sent again under that ID. Whether it was delivered is not recorded in the states `executing` and `failed`, and must be resolved with the recipient, which the current external server cannot answer.
