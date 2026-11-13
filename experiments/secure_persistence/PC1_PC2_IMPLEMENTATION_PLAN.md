# PC1 and PC2: implementation plan

| | |
|---|---|
| Status | plan only; no code has been changed |
| Authoritative specification | `preregistration.md` v1.1 (SHA-256 `8363417c5aadac06…c358`), sections 3, 4 and 7 (T16, T17), unchanged |

Implementing this plan changes production code: `governance/approval.py` and `agents/approval_flow.py`. That needs your approval first, because it changes the opt-in approval workflow of the deployed application. The default pipeline, the risk model, the thresholds and the policy rules are not touched.

## 1. Exact requirements from the pre-registration

### PC2: canonical encoding v1 (section 4)

| # | Requirement (v1.1 wording, condensed) | Current code (`governance/approval.py`) | Gap |
|---|---|---|---|
| R2.1 | `K = HMAC-SHA256(master_key, "approval-service")` | `derive_key(master, "approval-service")` in the store factory | none, but it must be verified to be the same derivation |
| R2.2 | Every digest = `HMAC-SHA256(K, label ‖ 0x00 ‖ message)`, with a distinct ASCII label per use | `hmac(K, _canonical(value))`; no label, no separator | missing |
| R2.3 | Payload must be a Python `str`; anything else rejected | `_canonical(payload)` accepts any type (`default=str`) | missing |
| R2.4 | Payload bytes = UTF-8 of the exact string, with no normalization, trimming, line-ending change or case folding | payload is JSON-quoted with `ensure_ascii=True` before hashing | wrong input bytes (but still injective) |
| R2.5 | `payload_digest = HMAC(K, "privagent/payload/v1" ‖ 0x00 ‖ payload_bytes)`, lowercase hex | different construction | missing |
| R2.6 | CJ = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, UTF-8; values only `str` or objects of `str`; other types rejected, never converted; no `default=` | `json.dumps(sort_keys=True, default=str)`: default separators, ASCII escaping, converts anything | missing |
| R2.7 | Approved action: the eight fields `schema`, `action_id`, `run_id`, `agent_role`, `mcp_server`, `tool`, `arguments{destination, payload_digest}`, `decision_event_id`, all strings | seven flat fields; no `schema`, no `mcp_server`, `destination` and `payload_digest` not nested in `arguments` | missing |
| R2.8 | `action_digest = HMAC(K, "privagent/approved-action/v1" ‖ 0x00 ‖ CJ(approved_action))` | HMAC of the non-canonical JSON of the flat dict | missing |
| R2.9 | `approval_token = HMAC(K, "privagent/approval-token/v1" ‖ 0x00 ‖ CJ({action_digest, action_id, decision: "approve", reviewer}))` | `_digest({"approved", "digest", "by"})`; no decision field, no label | missing |
| R2.10 | `arguments` lists every argument passed to the tool; a tool with other arguments needs a new schema version | `send_result(payload, destination)` matches | none |
| R2.11 | Payloads share an approval only if their UTF-8 bytes are identical (NFC/NFD, homoglyph, zero-width, trailing space, CRLF/LF); likewise any change in destination, tool, server, run or action ID (T16) | not tested | test missing |

### PC1: pre-send verification (sections 3 and 4)

| # | Requirement | Current code (`agents/approval_flow.py::_execute`, `ApprovalService.authorize`) | Gap |
|---|---|---|---|
| R1.1 | Runs immediately before the MCP call, inside the execute step | `authorize()` runs at the top of `_execute` | position is right, content is wrong |
| R1.2 | Step 1: rebuild `approved_action` from the exact `payload`, `destination`, `tool` and `mcp_server` about to be used | the payload digest is recomputed; destination, tool and server are not | **missing.** A `pending["destination"]` changed in the checkpoint is sent to unnoticed, because the token is checked against the *stored* `pending["action_digest"]`, not a recomputed one |
| R1.3 | Step 2: compare the recomputed `action_digest` with the one bound in the token, in constant time | the token is recomputed from the stored digest | missing |
| R1.4 | Step 3: verify the token | done, with the old format | format |
| R1.5 | Step 4: claim the ledger entry; step 5: make the call | claim, then `tools.execute_send(..., state["final_output"], pending["destination"])` | the call re-reads state after verification. The verified values must be passed straight to the call |
| R1.6 | Any failure in steps 1–3: no claim, no send, reason recorded | `authorize` failure: refused, no claim | must cover the new checks, with distinct reasons |
| R1.7 | T17: a stored destination, tool or server changed before resume is refused by PC1 before any send or claim | not tested | test missing |

## 2. Design

### 2.1 New module `governance/approval_binding.py`

This module holds only pure functions, no I/O. Keeping them in one small module makes the encoding independently testable and reviewable.

```python
SCHEMA_ACTION = "privagent-approved-action/1"
LABEL_PAYLOAD = b"privagent/payload/v1"
LABEL_ACTION  = b"privagent/approved-action/v1"
LABEL_TOKEN   = b"privagent/approval-token/v1"

class BindingError(ValueError): ...           # any rejected input

def canonical_json(obj) -> bytes              # R2.6: str or {str: str | {str: str}} only; raises BindingError
def labeled_hmac(key, label, message) -> str  # R2.2: HMAC-SHA256(key, label + b"\x00" + message).hexdigest()
def payload_digest(key, payload) -> str       # R2.3–R2.5: payload must be str; UTF-8 bytes, no transformation
def approved_action(*, action_id, run_id, agent_role, mcp_server, tool,
                    destination, payload_digest, decision_event_id) -> dict   # R2.7; validates every field is str
def action_digest(key, action) -> str         # R2.8
def approval_token(key, action_digest, action_id, reviewer) -> str            # R2.9 (decision fixed to "approve")
def verify(expected_hex, actual_hex) -> bool  # hmac.compare_digest on str
```

Validation rules:

- **`action_id`** must match `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, a lowercase uuid4.
- **Type coercion.** Every other field must be a non-empty `str`. Nothing is coerced; `default=` is never used.
- **`decision_event_id`.** `TrajectoryMonitor` creates decisions with `event_id=None` by default. The implementation must confirm that every decision reaching `gate()` carries a string event ID. If not, `gate()` refuses with `BindingError("decision_event_id")` and the run halts. It must not insert a placeholder, because that would let distinct decisions share an ID.

### 2.2 MCP server identity

The pre-registration names the server `"external_server"`, while `agents/mcp_client.TOOL_TO_SERVER` maps `send_result` to the key `"external"`.

**Plan:** add a constant map in `approval_binding`, `MCP_SERVER_IDENTITY = {"external": "external_server"}`. That is the server's directory name under `mcp_servers/`, which is stable. The server identity in the approved action is then always `MCP_SERVER_IDENTITY[TOOL_TO_SERVER[tool]]`, resolved from code, never from state.

This follows the pre-registration literally, so no amendment is needed. Any tool whose server is not in the map is refused.

### 2.3 Changes to `ApprovalService` (`governance/approval.py`)

- **`gate()`** builds `approved_action(...)` via the binding module, with:
  - `mcp_server` from section 2.2;
  - `tool = "send_result"`;
  - `destination` from the request;
  - `payload_digest(K, payload)`.

  The pending dict stores `binding_version = 1`, the full `approved_action` and `action_digest`. Top-level `destination`, `tool` and `payload_digest` stay as display copies, so the dashboard keeps working. Verification never reads the display copies.
- **`review_request()`:** `payload_matches_gated_action` uses the new `payload_digest`, with a constant-time compare.
- **`resolve()`:** same checks as today. For an approval it adds `action_digest` (the value approved) and `token = approval_token(K, action_digest, action_id, reviewer)`. The reviewer must be a non-empty `str`, which is already checked.
- **New `verify_pre_send(pending, approval, payload, destination, tool)`** replaces `authorize()` as the gate in `_execute`. It implements R1.2–R1.4 in the pre-registered order and returns `(ok, reason, verified_call)`:
  1. Refuse if `pending.get("binding_version") != 1`: `legacy_binding_version`.
  2. Refuse if `payload` is not a `str`: `payload_not_str`.
  3. Rebuild the action from the stored identity fields (`action_id`, `run_id`, `agent_role`, `decision_event_id` from `pending["approved_action"]`) and the values about to be used: `tool`, `MCP_SERVER_IDENTITY[TOOL_TO_SERVER[tool]]`, `destination`, `payload_digest(K, payload)`. Any `BindingError` is refused as `binding_invalid:<field>`.
  4. `recomputed = action_digest(K, rebuilt)`.
  5. **Allowed without review** (`final_decision ∈ ALLOWED_DECISIONS`): require `verify(pending["action_digest"], recomputed)`, else `pre_send_digest_mismatch`. There is no token in this path.
  6. **Human approval:**
     - require an approval for this `action_id` with `approved` true;
     - require `verify(approval["action_digest"], recomputed)`, else `pre_send_digest_mismatch`;
     - then `verify(approval["token"], approval_token(K, recomputed, action_id, approval["reviewer"]))`, else `invalid_approval_token`.

     Because the token is checked over the *recomputed* digest, editing `pending["action_digest"]` or `approval["action_digest"]` in the checkpoint cannot make a changed call pass.
  7. Return `verified_call = {"tool": tool, "arguments": {"payload": payload, "destination": destination}}`.

  The existing `authorize()` is kept, unchanged, for one release, so that callers outside `_execute` don't break. `_execute` stops using it.

### 2.4 Changes to `agents/approval_flow.py::_execute`

```text
payload     = state["final_output"]
destination = pending["approved_action"]["arguments"]["destination"]   # the stored destination: what PC1 must check
tool        = "send_result"                                            # fixed for this schema
ok, reason, call = service.verify_pre_send(pending, approval, payload, destination, tool)
if not ok:            -> outcome "refused", no claim, no send, record reason        (R1.6)
elif not ledger.claim -> "duplicate_prevented"                                       (unchanged)
else:                 -> tools.execute_send(monitor, decision, call["arguments"]["payload"],
                                            call["arguments"]["destination"])     (R1.5: verified values only)
```

`destination` deliberately comes from stored state. A tampered stored destination therefore reaches the rebuild in step 3 and changes the recomputed digest. That is exactly the T17 case. The call then uses only the verified values in `call`, so nothing re-reads state between verification and the call.

### 2.5 Compatibility and migration

- **Pending actions created before PC2.** These include any paused run in the deployed `runtime/approvals` store. They lack `binding_version` and are refused with `legacy_binding_version`. That is fail-closed: such a run must be re-gated by starting the task again. It cannot be approved under the old format.
  - The dashboard review queue (`dashboard/review_queue.py`) should show the refusal reason. That is a display-only change.
  - Before deployment, check the deployed store for paused runs. Do not delete or alter them.
- **Unchanged.** The response format the reviewer sends stays `{action_id, action_digest, decision, reviewer[, comment]}`. The dashboard and the existing tests submit `request["action_digest"]`, which keeps working.
- **Tests** that compare digests with hard-coded values (`"0" * 64` in `test_human_approval.py`) are unaffected: they test mismatch, not format.

## 3. Tests to add (before any confirmatory run)

All tests go in a new `tests/test_approval_binding.py` plus additions to `tests/test_human_approval.py`, using synthetic data only. Nothing under `experiments/` is changed.

| ID | Test | Pass criterion |
|---|---|---|
| U1 | Known-answer vectors: a fixed key, payload and action give fixed hex for `payload_digest`, `action_digest` and `approval_token`, computed independently by hand-written HMAC in the test | exact match |
| U2 | Domain separation: the same message under the three labels gives three different digests; a payload digest submitted as an action digest is refused | all distinct; refused |
| U3 | CJ rejects int, float, bool, None, list, bytes, nested objects deeper than one level, and NaN | `BindingError` for each |
| U4 | CJ equals the RFC 8785 output for string-only objects, including non-ASCII, quotes, backslashes and control characters | byte-equal to fixed expected bytes |
| U5 | Payload must be `str` (bytes and dict refused); no normalization (T16 cases below) | as stated |
| T16 | Each case gets a different `payload_digest` or `action_digest`, and approving one never authorizes the other end to end: NFC vs NFD "é"; Latin "a" vs Cyrillic "а"; inserted U+200B; trailing space; CRLF vs LF; changed destination, tool, server, `run_id` or `action_id` | 10/10 distinct; 10/10 refused at `verify_pre_send` |
| T17a | A paused run's stored `approved_action.arguments.destination` is changed in the checkpoint (attacker A4 in configurations without encryption; in encrypted configurations through a re-encrypted blob, see section 4) | refused `pre_send_digest_mismatch`; ledger has no row; stand-in has 0 sends |
| T17b | As T17a for `tool` and for the server-identity field | as T17a |
| T17c | Stored `pending["action_digest"]` and `approval["action_digest"]` both changed to match the tampered destination, without the key | refused `invalid_approval_token`; no claim; 0 sends |
| R1 | The existing approval, restart and dashboard suites pass unchanged | all pass |
| R2 | A legacy pending dict (no `binding_version`) is refused as `legacy_binding_version`, with no claim | as stated |

## 4. A limitation of PC1 that the pre-registration must state (input to amendment v1.2)

The pre-registration's attacker B "holds the checkpoint key (leaked `master.key` or `PRIVAGENT_MASTER_KEY`)". The approval key K is derived from that same master key.

**Consequence:** an attacker holding the master key can compute valid payload digests, action digests and approval tokens for any action, so PC1 cannot detect an approval forged by a master-key holder. T17's prediction "refused by PC1 … B in all" holds only for an attacker who *edits* stored fields without re-signing them.

**Two options:**

1. **Narrow T17's attacker.** T17 tests an attacker who can rewrite stored state but does not recompute HMACs. In encrypted configurations this is an attacker holding only the derived checkpoint subkey (`derive_key(master, "checkpoint-aes-gcm")`), not the master key. State explicitly that a master-key holder can forge approvals and is out of PC1's scope.
2. **Separate the keys.** Provision the approval key K independently of the checkpoint master key. That is a design change beyond PC1/PC2 and is not proposed here.

**Recommendation:** option 1, recorded in amendment v1.2 (see CONFIRMATORY_PROTOCOL.md).

**Adopted in `preregistration_v1.2.md`:**

- **AM6** splits attacker B into **B1** (checkpoint subkey only; PC1 applies) and **B2** (master key; PC1 and I2 not claimed).
- **T19 / H6e** characterizes B2 forging an approval.
- T17 uses A4 in C0 and C2, and B1 in C1, C3 and C4.

## 5. Gate 3 / PC4 reproduction check (from v1.1 section 3)

All of the following must pass, in order, before any confirmatory run:

1. PC1 and PC2 are implemented, and the U and T tests above pass.
2. **C1 reproduction.** C1 is built through the experiment factory and matches `DevApprovalStore`: the same serializer, cipher, key derivation, ledger, `purge_completed` and flow rule. This is checked by comparing the constructed objects' configuration, and by running one paused-and-approved run through each and comparing the action digests for identical inputs and keys.
3. The existing suites pass: `test_human_approval`, `test_restart_recovery`, `test_dashboard_changes`, `test_handoff_instrumentation`, `test_sensitivity_authority`, `test_feature_consistency`.
4. The Attack Lab replay is byte-identical to `models/baselines/trajectory_invariant_v1/results/attack_lab_replay.md`.
5. The frozen hashes are unchanged: models, thresholds, feature configuration, `preregistration.md` and the exploratory snapshot manifest.

## 6. Order of work, after your approval

1. Write `approval_binding.py` and tests U1–U5. No behaviour change yet.
2. Switch `gate`, `resolve` and `verify_pre_send` over to it, and switch `_execute` to `verify_pre_send`. Then run T16, T17, R1 and R2.
3. Show the refusal reason in the dashboard review queue.
4. Check the deployed store for paused runs (read-only) and report what is found.
5. Run gate 3.

Steps 1–3 change production code and need explicit approval. Nothing is committed without your approval.
