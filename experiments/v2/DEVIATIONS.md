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
