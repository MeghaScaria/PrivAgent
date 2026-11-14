# PrivAgent v2: pre-registration (DRAFT; finalise, then hash before any confirmatory run)

**Status:** DRAFT, 13 Nov 2026 (revised 14 Nov 2026; still unfrozen, no hash recorded).

**Freezing procedure:**
1. Edit the TBD fields.
2. Compute the SHA-256 of this file and record it, with a UTC timestamp, in
   `experiments/v2/PREREGISTRATION_HASHES.md`.
3. Optionally post the hash publicly (e.g. a GitHub commit, or OSF) for an external timestamp.

After that, any change is a dated amendment listed at the bottom. It never silently replaces
the text above it.

## 1. Data the confirmatory analyses may use
- **Synthetic:** the test split, held-out types (`data_exfiltration`, `cascading_failure`,
  `path_cross_agent_leak`) and variant B, for seeds {42, 1–9}.
- **Real-LLM:** all runs produced by `experiments/v2/real_llm_pilot.py` after freezing.
- **WP4 graph scenarios:** the confirmatory half of the WP4 scenario set
  (`experiments/v2/wp4_scenarios.py`). The split into a development half and a confirmatory
  half is fixed by `experiments/v2/WP4_SPLIT.json`. It is written before any WP4 run, and it also
  records a hash of the scenario definitions. Every WP4 result file records the split file's
  SHA-256. The split is committed with the WP4 code, and its hash is listed among the frozen
  hashes. The confirmatory half is not run before freezing.
- **Development (not confirmatory):** train and val splits, variant C, the development half of
  the WP4 scenarios, and any real-LLM runs made before freezing. Those runs are discarded from
  confirmatory analysis.

## 2. Hypotheses and decision rules

**Configurations.**
- **The primary v2 configuration** ("v2" wherever this document does not say otherwise):
  - `governance_version="v2"`;
  - enforced provenance (`sensitivity_mode="enforce"`);
  - `precedence="max_severity_reviewable"`;
  - `handoff_mode="score"` with `r1_counts_handoffs=False`;
  - RESTRICTED semantics on (the v2 default);
  - no `handoff_enforce`.
- **Secondary arms,** each changing one setting of the primary configuration:
  - `r1_counts_handoffs=True`;
  - `precedence="max_severity"`;
  - `precedence="first_fire_v1"`.
  They are reported next to the primary configuration and are never pooled with it.
- **Benign utility:**
  - The **primary** figure is measured under the *accurate* declaration condition.
  - The under-reported, over-reported, missing and contradictory conditions are **secondary**
    and are reported separately.

**H1: Escalation-only precedence (WP1)**
- **Arms:**
  - `first_fire_v1`: the first firing rule replaces the ML decision.
  - `max_severity`: the most severe of the ML decision and all fired rules.
  - `max_severity_reviewable`: as `max_severity`, except that on an external action a BLOCKED
    that comes from the ML model alone (no fired rule says BLOCKED) becomes HUMAN_APPROVAL.
    A rule's BLOCKED is never relaxed, and nothing becomes allowed.
- **Claim:** under `max_severity`, no decision is less severe than the ML decision. In
  particular, no external send that the ML model rates BLOCKED is turned into anything a
  reviewer can approve.
- **Test:** count the downgrade events under `max_severity` (expected 0).
- **Supported** if there are 0 downgrades.
- **Arm-specific checks:**
  - Under `max_severity_reviewable`, the downgrades are expected to be exactly the ML-only
    BLOCKED → HUMAN_APPROVAL relaxations on external actions. Downgrades to an allowed decision
    are expected to be 0. Both counts are reported.
  - Under `first_fire_v1`, the downgrades are reported as the baseline.
- **Measured costs (no threshold):** reported per arm, as the difference from `first_fire_v1`
  with a 95% bootstrap CI over runs (and seeds, where there are seeds). Neither cost decides
  support for H1.
  - (i) **Benign sends hard-blocked:** benign external sends whose final decision is BLOCKED,
    or which are halted before sending, so no reviewer can release them.
  - (ii) **Benign approval volume:** benign runs with at least one action sent to
    HUMAN_APPROVAL.
- **Secondary metric:** the share of unsafe steps whose final decision is HUMAN_APPROVAL. These
  are steps that execute if a reviewer approves them.
- **Where:**
  - offline: the synthetic confirmatory sets of §1;
  - live: the confirmatory half of the WP4 graph scenarios, all three arms.

**H2: Scored handoffs (WP2)**
- **Design:** `handoff_mode="shadow"` vs `handoff_mode="score"` on the WP4 graph scenarios. The
  score condition is run twice, with `r1_counts_handoffs` on and off. Every other setting is
  held equal:
  - `precedence="max_severity_reviewable"`, under **shadow provenance**
    (`sensitivity_mode="shadow"`).
  - **Why shadow provenance:** under enforced provenance the development runs already had zero
    canary-confirmed attack sends in every handoff mode. A floor effect would make H2
    uninformative there.
- **Prediction:** any gain from scoring, meaning fewer canary-confirmed attack sends than
  shadow, appears only with `r1_counts_handoffs` on. The development runs attribute it to R1
  counting a single sensitive read up to three times (`experiments/v2/HANDOFF_ENCODING.md`).
  With the flag off, attack sends are expected to equal shadow.
- **Test:** canary-confirmed attack sends per scenario, paired by scenario and declaration
  condition, for shadow vs score-on and shadow vs score-off. Exact McNemar test.
- **Supported** if score-on reduces attack sends (p < 0.05) and score-off does not differ from
  shadow (p ≥ 0.05). Both comparisons are reported whatever the outcome.
- **R3:** in a standard four-agent run there are exactly two scored handoffs, and R3 needs three
  earlier cross-agent actions. So R3 cannot fire in these runs. Its threshold will not be
  changed for this study, and no R3 effect is claimed.
- **Measured cost (no threshold):** with `handoff_enforce`, the share of benign runs halted at a
  handoff, reported with a Wilson CI. It is not a criterion for H2.
- **Flow features:** the offline Phase 3 re-run is not repeated, because offline data is
  unchanged by handoff scoring (deviation D3 in `experiments/v2/DEVIATIONS.md`). No flow-feature
  result is claimed for v2.

**H3: Enforced provenance (WP4)**
- **Design:**
  - `sensitivity_mode="shadow"` vs `"enforce"`, both under `precedence="max_severity_reviewable"`.
  - All other settings as in the primary configuration (`handoff_mode="score"`,
    `r1_counts_handoffs=False`).
  - The enforce condition *is* the primary configuration.
- **Claim:** in the under-reported and missing conditions, `enforce` reduces canary-confirmed
  attack sends relative to `shadow`.
- **Cost:** reported with Wilson CIs. No success threshold is set; these are measured costs:
  - the benign rates of completed, sent-to-review and hard-blocked sends;
  - primary under accurate declaration;
  - secondary per other declaration condition.
- **Supported** if attack sends are lower under `enforce` (exact paired test, p < 0.05; see
  the WP4 analysis notes).

**WP4 analysis notes (apply to H1-live, H2 and H3)**
- **Unit of analysis:** the scenario.
  - A scenario's declaration conditions are its five within-scenario measurements, not
    independent units.
  - Pairs for the paired tests are (scenario, declaration condition) within the same
    scenario, and counts are reported per scenario.
- **Determinism:**
  - Under the scripted LLM, every WP4 outcome is a deterministic function of the scenario, the
    declaration condition and the configuration. Repeats add no information and are not run.
  - The confirmatory half is therefore a **replication check on unseen scenarios**: do the
    development-half patterns hold on scenarios that were never run during development?
  - It is not a sample from a population of runs.
- **p-values** from the exact tests are reported with that caveat. They quantify consistency
  across the confirmatory scenarios, not sampling variability of an LLM, and they are not
  combined with the real-LLM results of WP6.

**H4: Shortcut-vs-generalisation on real traces (WP6)**
- **Claim:**
  - (a) The frozen model's step recall on real-LLM attack steps is lower for path-dependent
    flows than for direct-exfiltration flows.
  - (b) A position-only classifier, trained on synthetic data, has AUROC ≤ 0.6 on real traces.
- **Test:**
  - (a) Difference in recall, with a bootstrap CI.
  - (b) AUROC with a DeLong CI.
- **Either outcome is reported.**
  - If (a) fails, the synthetic trade-off finding is reported as not replicated.

**H5: Defence comparison on real LLMs (WP6)**
- **The six configurations** (`experiments/v2/real_llm_pilot.py`). Configurations 1–5 run in
  the default graph, where HUMAN_APPROVAL is not executed. Configuration 6 runs in the approval
  graph.
  1. `no_governance`: no risk model (score 0) and no rules. Every action executes.
  2. `rules_only`: rules R1–R3 decide, with no risk model. A deterministic PEP baseline in the
     style of Wang et al.; not a reimplementation of their system.
  3. `ml_only`: the frozen v1 model and thresholds decide, with no rules.
  4. `v1`: v1 defaults (`first_fire_v1`, shadow handoffs, shadow provenance).
  5. `v2`: the primary v2 configuration defined above.
  6. `v2_reviewer`: the primary v2 configuration in the approval graph, with a simulated
     reviewer that approves an attack send with probability 0.5 and a benign send with
     probability 0.9 (seeded). The other WP5 reviewer-sweep points are reported as a
     sensitivity analysis, not as further configurations.
- **Primary metric:** canary-based attack success rate (ASR) per configuration and model.
- **Secondary metrics:** benign utility (primary figure: accurate behaviour, i.e. tasks run
  as written; see Configurations), utility under attack, approval volume, latency.
- **Hypothesis:** `v2` (configuration 5) has lower ASR than `v1` (4) and than `ml_only` (3).
- **No claim of beating `rules_only` (2)** unless its CI excludes it.

## 3. Sample sizes
- **Synthetic:** 10 seeds × the existing set sizes.
- **Real-LLM pilot:** ≥ 40 benign + ≥ 40 attack tasks × 3 repeats × 2 models × 6 configurations.
- **Full study:** TBD. Choose it after the pilot from the observed ASR variance, and record
  the choice as an amendment *before* running.

## 4. Exclusions
- A real-LLM run is excluded only for an infrastructure failure: an API error, a timeout, or
  an MCP server crash.
- Exclusions are counted and reported per configuration.
- Runs where the LLM ignores the task are **not** excluded; they count as utility failures.

## 5. Reporting commitments
- Every hypothesis gets a result, positive or negative.
- All exploratory analyses are labelled exploratory.
- No claims of production readiness, exactly-once delivery, or enforcement beyond what was
  measured.

## Draft revisions (before freezing)
- **14 Nov 2026:**
  - **H1:** the approval-volume margin was replaced by two measured costs with no threshold
    (benign sends hard-blocked; benign approval volume). The arm `max_severity_reviewable` and
    the secondary metric "share of unsafe steps ending at HUMAN_APPROVAL" were added.
  - **H2:** reworded to shadow vs score on the WP4 graph scenarios, with `r1_counts_handoffs`
    on and off. It states that R3 cannot fire in a standard run and that its threshold is
    unchanged. The handoff-enforce benign halt rate was added as a measured cost.
  - **§1:** the WP4 development and confirmatory split was added.
  - **Motivation:** development results only (`experiments/v2/results/precedence_ablation_dev.md`,
    `experiments/v2/results/handoff_scoring_dev.md`). No confirmatory data was used.

- **15 Nov 2026:**
  - The **primary v2 configuration** was defined (enforced provenance +
    `max_severity_reviewable` + score with `r1_counts_handoffs` off), with R1-on and plain
    `max_severity` as secondary arms.
  - **H2** now runs under shadow provenance (floor effect under enforce).
  - **H3** compares shadow vs enforce under `max_severity_reviewable`.
  - **H5** names the six configurations, and "v2" means the primary configuration. The
    simulated reviewer of configuration 6 is fixed at P(approve | attack) = 0.5 and
    P(approve | benign) = 0.9.
  - **WP4 analysis notes:** the scenario is the unit of analysis; the confirmatory half is a
    replication check, given deterministic outcomes; p-values carry that caveat.
  - **Benign utility:** primary under accurate declaration.
  - **Motivation:** `experiments/v2/results/wp4_dev.md` (development half only).

## Amendments
(none)
