# Deliberate deviations from V2_PLAN.md

Each entry records where the implementation knowingly differs from the plan, why, and how to
undo it. These are decisions, approved by the project owner, not defects.

## D1. WP3.3: restricted lineage also comes from internal RESTRICTED tool calls

- **Plan:** RESTRICTED + `cross_agent` (a scored handoff) is allowed, and the produced ref is marked
  `restricted_lineage=True`. Any later external send carrying restricted lineage → HUMAN_APPROVAL.
- **Implemented:**
  - Refs produced by a scored RESTRICTED handoff are marked through `mark_restricted_lineage()`
    (wired for WP2).
  - In addition, the tool-result refs of **internal** RESTRICTED tool calls are marked
    automatically (`TrajectoryMonitor.register_tool_result`).
  - The later-send check follows provenance origins, so lineage propagates through handoffs and
    derived objects (`TrajectoryMonitor.restricted_lineage`).
- **Reason:** in the live pipeline every tool action is `internal` or `external`, and `cross_agent`
  actions do not exist until WP2. Under the plan's wording, the lineage rule could therefore never
  fire live. Data read under a RESTRICTED decision and later sent outside is exactly what the rule
  is meant to catch.
- **Effect:**
  - v2 only; v1 is unaffected, because `restricted_semantics` is off unless
    `governance_version="v2"`.
  - The development count is in `experiments/v2/results/restricted_semantics_dev.md`: 0 of 1,059
    benign validation runs escalated (offline upper bound).
  - Covered by `tests/test_hygiene_v2.py::test_restricted_internal_runs_and_lineage_escalates_later_send`.
- **To revert:** drop the `mark_restricted_lineage(refs)` call in `register_tool_result`.
- **Approved:** 14 Nov 2026.

## D2. WP3.4: `server_identity()` helper in `agents/mcp_client.py`

- **Plan:** the binding digest covers the MCP server identity (`TOOL_TO_SERVER[tool]`). The plan does
  not list `agents/mcp_client.py` among the files to change.
- **Implemented:** a read-only helper `server_identity(tool)` in `agents/mcp_client.py` returns
  `{"server": name, "script": <server script path relative to the repo>}`. It is built from the same
  `TOOL_TO_SERVER` and `SERVERS` tables that the client uses to route calls.
- **Reason:**
  - The identity checked at execution time should come from the routing the client will actually
    use, not from a separate copy such as the one in `governance/provenance.py`.
  - Including the script path also binds the approval to which server program receives the call,
    not only to its name.
- **Effect:**
  - No behavioural change.
  - Used only by v2 binding (`ApprovalService(binding="v2")` and `agents.tools.execute_send(..., binding=...)`).
- **Approved:** 14 Nov 2026.

## Related change outside the plan (not a deviation of a work package)

- `PRIVAGENT_MCP_START_TIMEOUT`: an environment variable for the MCP startup wait, in
  `agents/mcp_client.py`.
  - The default is unchanged at 30 s.
  - It was added because, on a loaded machine, the four stdio servers did not all connect within
    30 s. That made the regression gate fail the same way on pre-WP1 code.
- `tests/test_restart_recovery.py`: the restart worker's stderr goes to a temporary log file
  instead of `DEVNULL`. Test-only, so a failing worker shows its cause.

## D3. WP2.5: offline Phase 3 re-run skipped; the live test moves to WP4

- **Plan:** re-run Phase 3's pre-registered 2-SE flow-feature comparison with handoffs scored in
  the live replays (Attack Lab + E5), plus the offline set.
- **Decision:** the offline part is skipped. The live part moves to the WP4 scenario set.
- **Reason (offline):** handoff scoring changes only what the *live* monitor appends to the
  trajectory. The synthetic generator, its training / validation / variant-C data and the frozen
  model are unchanged. The generator already encodes cross-agent moves as `cross_agent` actions, so
  an offline re-run would reproduce the frozen Phase 3 result
  (`experiments/results/phase3_flow_features.*`) exactly and add no evidence.
- **Reason (live):** the current live replays cannot carry the comparison.
  - The Attack Lab produces no handoff events. It replays scripted actions without a graph run.
  - E5 has only 8 scenarios, each with exactly 2 scored handoffs.
  - A flow-feature comparison on these would have no power and could not test path-dependent
    attacks live.
  - The WP4 scenario set (graph-based benign and attack scenarios with canary ground truth) is
    the first live set where the comparison is meaningful. It will be pre-registered with the
    rest of the confirmatory protocol.
- **Status:** development observations of shadow vs score are in
  `experiments/v2/results/handoff_scoring_dev.md` and `experiments/v2/HANDOFF_ENCODING.md`. No
  flow-feature result is claimed for v2.
- **Approved:** 14 Nov 2026.

## Note: v1 evidence logs are not in version control

- **What:** `logs/audit_log.jsonl`, `logs/approval_log.jsonl` and `logs/handoff_log.jsonl` are the
  persisted v1 logs cited as evidence in the paper (for example the demo runs `demo_9e6a8ae2`,
  `demo_cc0f5f9e` and `demo_89c31726`).
  - They stay on disk, unchanged, and are not committed. `logs/` is git-ignored.
  - A scan on 14 Nov 2026 found no emails, API keys or task text. However, the `approval.reviewer`
    field holds names typed into the Human Approval page, including the author's own name.
- **Integrity:**
  - The files are covered by the committed hash manifest `experiments/v2/V1_EVIDENCE_LOGS.sha256`
    (check with `sha256sum -c experiments/v2/V1_EVIDENCE_LOGS.sha256`).
  - The manifest records them as they were on 13–14 Nov 2026, identical to the pre-WP1 snapshot.
  - The logs are append-only. They gained live dashboard runs on 12 Nov 2026, after the paper's
    11 Nov validation, but the entries the paper cites are unchanged.
  - Before this manifest, no committed manifest covered them.
- **Release:** a redacted copy, with reviewer names replaced by stable pseudonyms and every other
  field unchanged, will be released with the research artifact. The script that produces it will
  be released too, so the redaction can be reproduced and checked against these hashes. Neither
  exists yet.
