---
title: "PrivAgent: Trajectory-Aware Runtime Governance for Multi-Agent LLM Systems"
subtitle: "An Integrated Prototype and an Empirical Study of Evaluation Pitfalls, Shortcut Learning and Generalization Limits"
author: "[Author names and affiliations to be added]"
date: "Revised working research draft, 10 November 2026"
---

# PrivAgent: Trajectory-Aware Runtime Governance for Multi-Agent LLM Systems

### An Integrated Prototype and an Empirical Study of Evaluation Pitfalls, Shortcut Learning and Generalization Limits

*[Author names and affiliations to be added]* · Revised working research draft, 10 November 2026

---

**Abstract.**

*Problem.* In multi-agent LLM systems, sensitive data can leave an organisation through a sequence of tool calls and agent-to-agent handoffs in which no single step looks unsafe.

*System.* We present PrivAgent, an integrated runtime-governance prototype for a four-agent LangGraph pipeline that reaches tools through Model Context Protocol (MCP) servers. Every proposed tool call is scored by a gradient-boosted classifier, using features of the run's executed prefix. Deterministic policy rules can override the score, and every decision is logged. PrivAgent also adds:

- provenance and handoff instrumentation, operating in *shadow mode*;
- an optional human-approval workflow for external transmissions.

*Main finding.* All experiments use synthetic, template-generated trajectories and scripted test doubles. They expose a methodological pitfall for trajectory-based security models: near-perfect reported detection can come largely from evaluation artefacts.

- **Leakage.** The originally reported F1 of 0.999 came from a row-level split that let steps of the same run appear in both training and test. Once runs were kept together and held-out attack types were scored, F1 on unseen attack types fell to 0.657.
- **A positional shortcut.** The corrected model relied on *where* an attack occurred in a run. A position-invariant feature set removes this dependence by construction.

The deployed model then reaches the following F1 (validation-tuned thresholds):

| Set | F1 |
|---|---|
| In-distribution test | 0.912 |
| Held-out attack types | 0.665 |
| Held-out tool-swapped variants | 0.493 |

It detects every run of two held-out direct attack types. But it catches only 6 of 107 runs of the held-out path-dependent attack `path_cross_agent_leak`.

*Mechanism demonstrations.* In controlled runs, provenance-derived sensitivity exposes an agent that under-reports sensitive data:

- in two stored dashboard demo runs, the enforced score was 0.0 while the provenance-authoritative shadow score was 0.9952;
- these are mechanism demonstrations, not detection-rate estimates.

The approval workflow demonstrates a controlled way to pause and review external transmissions. Its effectiveness depends on reviewer behaviour: an accurate simulated reviewer allowed 0 of 4 attack transmissions, an approve-everything reviewer allowed 3 of 4, and no real reviewers were studied.

*Limitations.* Agent-to-agent handoffs are recorded but are not part of the classifier's scored trajectory. A policy rule can relax a model decision of BLOCKED. Provenance enforcement is not enabled.

**Index Terms:** LLM agents, multi-agent systems, runtime governance, trajectory monitoring, data provenance, evaluation leakage, shortcut learning, human-in-the-loop.

---

## 1. Introduction

### 1.1 Motivation

Tool-using LLM agents retrieve documents, query databases and send messages. Frameworks such as LangGraph compose specialised agents into stateful graphs [3]. Protocols such as MCP, introduced by Anthropic in November 2024, standardise tool access [1], [2].

Indirect prompt injection showed that content an agent retrieves can redirect what it does [4], and benchmarks measure how often tool agents follow injected instructions [5], [6].

In a multi-agent pipeline, a disclosure is often *compositional*:

1. one agent reads sensitive records;
2. another summarises them;
3. a third transmits the summary externally.

Each step can look legitimate on its own. The transmitting agent may also misreport, through error or manipulation, whether its output contains sensitive data.

### 1.2 Central statement

PrivAgent is an integrated runtime-governance prototype for multi-agent LLM systems. We investigate the effectiveness and limitations of four mechanisms:

- trajectory-aware risk estimation;
- provenance-derived sensitivity assessment;
- deterministic policy enforcement;
- human approval.

Our experiments expose three things: evaluation pitfalls, positional shortcut learning, and the difficulty of generalising to unseen compositional attacks. We do not claim that the mechanisms are new. Related systems combine provenance, policies, ledgers and approvals, often with enforced guarantees (Section 2).

### 1.3 Research questions and contributions

- **RQ1: trajectory-aware risk detection.** Can trajectory-aware ML identify risky multi-step agent actions, and how well does it generalise to unseen attack patterns?
- **RQ2: provenance-derived sensitivity.** Can provenance-derived sensitivity reveal discrepancies between an agent's self-reported sensitivity and the sensitivity inferred from the data it received?
- **RQ3: human approval.** Can a human-approval mechanism pause and review potentially unsafe external transmissions, and how does reviewer behaviour affect its effectiveness?

Table 1 maps each research question to its experiments and states what each demonstrated and what remains unproven.

**Table 1. Research questions, experiments and the strength of the evidence.**

| RQ | Experiments | Investigated | Demonstrated | Remains unproven |
|---|---|---|---|---|
| RQ1 | E1 evaluation correction; E2 position-shortcut investigation; E3 rich-flow-feature comparison; Attack Lab replay | detection of unsafe steps on synthetic trajectories, in distribution and on held-out attack types and tool variants | that leakage inflated F1 (0.999, then 0.657 held-out); a positional shortcut and its removal; good detection of two held-out direct attack types; poor detection of held-out path-dependent attacks (6/107 runs); flow features help path attacks but hurt direct ones | generalisation beyond nine scripted templates; behaviour on real LLM-generated trajectories; ML scoring of live cross-agent flow (Section 4.9) |
| RQ2 | E4 provenance instrumentation tests; controlled sensitivity-misreporting demonstrations (tests, dashboard demo runs, E5 `*_misreported` scenarios) | whether provenance labels can be computed without changing agent behaviour, and whether they expose under-reported sensitivity | byte-identical agent behaviour with instrumentation on and off; flagged misreports, with a high shadow score where the enforced score was near 0 (two separate evidence sources, Section 7.2) | detection rates over realistic declarations; the false-positive cost of enforcing provenance; behaviour with real LLMs |
| RQ3 | E5 human-approval evaluation (8 scenarios × 3 configurations) and functional tests | whether execution pauses before the send, binds to the reviewed action and avoids repeated execution, and how reviewer behaviour changes outcomes | a pause before the send; rejection sends nothing; at most one execution attempt per action ID; outcomes depend on the reviewer (0/4 against 3/4 attack sends) | real reviewer accuracy; complete binding of transmission context; exactly-once delivery (not provided) |

**Contributions**, stated conservatively:

1. **A cautionary empirical finding** (RQ1). We document how row-level leakage and a positional shortcut produced an apparently near-perfect trajectory detector, and what remains after correcting them (Section 7.1). This is consistent with the general literature on leakage [21] and shortcut learning [22].
2. **Mixed and negative results on flow features** (RQ1). They are reported under a decision rule fixed before the comparison (Section 7.1.4).
3. **An integrated, inspectable prototype.** It combines trajectory ML scoring, deterministic rules, audit logging, shadow-mode provenance and an opt-in approval gate around real MCP tool calls in a LangGraph multi-agent pipeline (Sections 4–5).
4. **Explicit documentation of architectural gaps** found by inspecting the code: handoffs are excluded from the scored trajectory (Section 4.9), and policy overrides can relax the ML decision (Section 4.10).

---

## 2. Background and Related Work

### 2.1 Attacks and benchmarks

- **Indirect prompt injection** [4] is the core threat for tool agents.
- **InjecAgent** [5] provides 1,054 indirect-injection test cases.
- **AgentDojo** [6] provides an extensible environment of 97 tasks and 629 security test cases.

PrivAgent's Attack Lab instead replays seven scripted action patterns and does not cause any LLM to be deceived. It therefore tests detection of action patterns, not resistance to injection.

### 2.2 Runtime enforcement and information-flow control for agents

- **CaMeL** [7] separates trusted control flow from untrusted data and enforces capability policies.
- **FIDES** [8] enforces confidentiality and integrity labels in an agent planner.
- **Progent** [14] enforces programmable privilege policies on tool calls.
- **IsolateGPT** [15] isolates LLM applications.

CaMeL, FIDES and Progent are arXiv preprints. We re-checked them on 10 November 2026 and found no published venue. IsolateGPT appeared at NDSS 2025.

All four enforce deterministic guarantees. PrivAgent's core decision is instead a learned score, with deterministic rules as an override, and its provenance is observational.

### 2.3 Runtime policy enforcement for MCP-based agents (Wang et al.)

Wang, Zhu and Li [28] (*Electronics*, 2026, published 27 June 2026) is the closest published work to PrivAgent's tool-call governance. We read the full article.

**Their system.** A single-agent **Policy Enforcement Point (PEP)**:

- intercepts every tool call at the tool-call boundary, after the model has chosen a tool name and arguments but before execution;
- checks a capability token;
- evaluates five ordered declarative rules (R01–R05; first match wins). The rules cover path scope, sensitive outbound data, high-risk tools, cross-server taint and rate caps;
- propagates trace-level **source-integrity and data-sensitivity labels** across steps (a LabelTracker; sensitivity is "sticky" once detected by regex);
- writes every decision to a **SHA-256 hash-chained audit log**.

**Their evaluation.** It uses **real LLMs**:

- 1,050 LLM-driven runs with deepseek-v4-pro on a 30-task controlled dataset;
- cross-model observations on four further backends;
- an exploratory AgentDojo pilot;
- a scripted mode.

The full system reduced attack success from 40.0% to 5.0%, against 35.0% for the strongest prompt-only baseline. Disabling cross-step labels raised call-level false negatives by 26.4 points. Tools are mostly in-process mocks, plus a preliminary validation over a real MCP stdio filesystem server. The authors frame their results as mechanism-coverage evidence on a controlled benchmark, not a deployability claim.

**Overlap with PrivAgent.** Both papers:

- intercept at the tool-call boundary;
- carry information across steps to judge an outbound action;
- use deterministic rules;
- log every decision.

The two papers address substantially the same problem.

**Differences:**

| Aspect | Wang et al. [28] | PrivAgent |
|---|---|---|
| Architecture | single agent loop with one enforcement point | LangGraph multi-agent orchestration (four roles), with agent-to-agent handoffs instrumented separately |
| Cross-step signal | propagated SI/DS labels, **enforced** | a learned trajectory score over count/maximum features, **enforced**; per-item provenance labels, **shadow only** |
| Rules | five rules, first match | three rules that replace the ML decision |
| Audit | hash-chained, tamper-evident | append-only by convention, not hash-chained |
| Human confirmation | REQUIRE_CONFIRM is treated as a block (no confirmation channel) | an opt-in pause-and-review workflow with an execution ledger |
| LLMs | real LLMs (deepseek-v4-pro, four more backends) | scripted LLM only |
| MCP | mock tools plus a preliminary real stdio filesystem server | four real MCP stdio servers with synthetic data |
| Evaluation | attack success, task success and false-positive/false-negative rates over LLM-driven runs | step-level detection metrics on synthetic trajectories; scripted demonstrations |

PrivAgent's evaluation is weaker in realism (no real LLM). It is more detailed on how a learned trajectory detector can be inflated by leakage and shortcuts.

### 2.4 Provenance-based and compositional-attack defences

- **AGATE** [10] (arXiv, September 2026) gates actions on authorisation and data provenance, with parameter-bound expiring grants and an effect ledger. It is evaluated across three agent harnesses, and its provenance and ledger concepts overlap with PrivAgent's.
- **Agent-Sentry** [16] bounds agents via execution provenance.
- **Agent-BOM** [12] models agent systems as attributed graphs for auditing.
- **PCAA** [13] attaches certificates and approval receipts to actions.
- **CapAgent** [11] maps human-attested intent to capability tokens. We could access only its bibliographic record and abstract.

PrivAgent's label rule is a two-level instance of lattice-based flow labelling [17], within the provenance tradition [18]. Its maximum-over-inputs propagation over-labels, which is exactly the problem *Permissive Information-Flow Analysis* targets [9]. Microsoft Research lists that paper as published in TMLR; OpenReview was not checked.

### 2.5 Human-in-the-loop

Automation research documents over-reliance on, and misuse of, automated aids [23]. LangGraph provides `interrupt()` and checkpoint-based resumption [3].

### 2.6 Positioning

Table 2 summarises how PrivAgent is positioned relative to the closest systems.

**Table 2. Positioning.** "Not stated here" means we did not verify the property, not that the work lacks it.

| Work | Status | Decision basis | Cross-step/provenance signal | Human approval | Evaluation |
|---|---|---|---|---|---|
| Wang et al. [28] | journal (2026) | deterministic rules | SI/DS labels, enforced | confirm treated as block | real LLMs, 30-task dataset |
| AGATE [10] | preprint | deterministic gate | source registration, enforced | host approvals, grants | 3 harnesses |
| CaMeL [7] | preprint | capabilities | value provenance, enforced | not stated here | AgentDojo |
| FIDES [8] | preprint | IFC planner | labels, enforced | not stated here | AgentDojo |
| PCAA [13] | preprint | certificates | not central | approval receipts | 96 traces |
| **PrivAgent** | this draft | **learned trajectory score** plus rules | item provenance, **shadow**; handoffs not scored | opt-in pause, ledger | synthetic only |

---

## 3. Problem Definition and Threat Model

**Actions and runs.** An action is the tuple

$$a = (\mathrm{agent\_role},\ \mathrm{tool\_name},\ \mathrm{action\_type},\ \mathrm{data\_sensitivity},\ \mathrm{destination\_category})$$

and a *run* is the ordered list of actions executed in one task.

**Sensitive data** comes from:

- HR and finance documents;
- the `employees` and `transactions` tables;
- user input in which a regex detector finds PII;
- outbound echoes, which are *unknown* and treated as sensitive.

**Unauthorised disclosure** is a `send_result` call to `external` that carries sensitive data the task owner did not intend to send.

**Adversary and failure model:**

- compromised or manipulated agent steps;
- an agent misreporting sensitivity;
- multi-step patterns that move data across agent boundaries;
- for the approval workflow, state tampering, replays and duplicate resumes.

**Trusted:** the governance code, the MCP client and servers, and the host.

**Out of scope:**

- semantic exfiltration that the features cannot represent;
- real LLM injection behaviour (not exercised);
- attacks across runs;
- process compromise;
- a holder of the master key.

PrivAgent provides **no guarantee of complete security, exactly-once delivery or universal attack prevention.**

---

## 4. PrivAgent Architecture

Figure 1 distinguishes three tiers:

- the **default governed tool execution** path;
- **shadow-mode** provenance and handoff instrumentation, which is recorded but not enforced;
- the **optional human-approval** workflow.

![Figure 1. PrivAgent architecture in three tiers. Blue: default governed tool execution, applied to every tool call. Orange: shadow-mode instrumentation (recorded; not enforced; not part of the scored trajectory). Green: the opt-in approval workflow (writer's external send only).](figures/r01_architecture_three_tiers.png)

### 4.1 Orchestration (LangGraph)

`agents/graph.py` builds orchestrator → retriever → analyst → writer:

| Agent | What it does | Calls tools? |
|---|---|---|
| Orchestrator | plans | no (LLM only) |
| Retriever | calls governed read tools | yes |
| Analyst | synthesises at most 10 documents, 10 records and 5 web results, and **self-reports** `contains_sensitive_data` | no (LLM only) |
| Writer | composes the answer and optionally calls `send_result` | yes |

Tests and experiments inject a scripted LLM.

### 4.2 MCP tool access

Four FastMCP stdio servers (document, database, web, external) are reached through one client thread with a fixed tool-to-server map.

The governed wrappers (`agents/tools.py`) fix every tool call's `destination_category`: reads are `internal`, and `send_result` is `external`.

### 4.3 Trajectory monitoring and risk assessment

`TrajectoryMonitor.evaluate()` is the single interception point. It:

1. extracts features (`governance/features.py`, shared by training and live scoring);
2. obtains a score r from the classifier;
3. maps r to a decision;
4. applies the policy engine;
5. logs the decision;
6. appends the action to the trajectory **only if it is allowed**.

### 4.4 The classifier

The deployed `trajectory_level` model is a scikit-learn `GradientBoostingClassifier` [19], [20] (200 trees, depth 5). It uses the `trajectory_invariant` feature set of 11 features:

- **five action features:** role, tool, action type, sensitivity, destination;
- **six prefix features:**

$$\mathrm{prev\_sensitive\_reads} = \sum_{i<t} s_i,\qquad \mathrm{prev\_external\_transmits} = \sum_{i<t} [d_i = 2]$$

  plus `max_sensitivity`, `max_destination`, `prev_risky_actions` (the sum of the two counts above) and `max_prev_risk` (= `max_destination` / 2).

All prefix features are counts or maxima, which makes them invariant to inserted harmless steps.

### 4.5 Autonomy levels

The thresholds were tuned on validation data only:

$$\mathrm{AUTONOMOUS}: r<t_1;\qquad \mathrm{RESTRICTED}: t_1\leq r<t_2$$

$$\mathrm{HUMAN\_APPROVAL}: t_2\leq r<t_3;\qquad \mathrm{BLOCKED}: r\geq t_3$$

with $(t_1, t_2, t_3) = (0.22, 0.50, 0.85)$.

**What executes:** only AUTONOMOUS and RESTRICTED. RESTRICTED currently behaves exactly like AUTONOMOUS. In the default graph, HUMAN_APPROVAL is not executed.

### 4.6 Deterministic policy rules

`PolicyEngine` evaluates three rules in order; the first that fires wins:

- **R1:** `send_result` to external after ≥ 2 prior sensitive actions → BLOCKED;
- **R2:** any sensitive action to external → HUMAN_APPROVAL;
- **R3:** an external action after ≥ 3 prior `cross_agent` actions → BLOCKED.

The rules read the `data_sensitivity` recorded on each action. Tool wrappers assign it for reads. For `send_result`, it is the value the sending agent declared.

### 4.7 Provenance registry and handoff instrumentation (shadow mode)

**Refs.** `ProvenanceRegistry` gives each item an allowed tool call returns a ref. The ref is identified by an HMAC-SHA-256 fingerprint keyed per run [27]; fingerprints are kept in memory and never logged. Derived objects (plan, analysis, answer) inherit the maximum sensitivity of their parents, and unknown is treated as sensitive:

$$\mathrm{combine}(v_1,\dots,v_n) = 1\ \mathrm{if\ any}\ v_i = 1;\ \ \mathrm{None\ if\ any}\ v_i = \mathrm{None};\ \ \mathrm{else}\ 0$$

**Handoffs.** `HandoffTracker` records six transfer types after each node, writing to `handoff_log.jsonl`:

| Event | From → to |
|---|---|
| input | user → orchestrator |
| handoff | orchestrator → retriever |
| handoff | retriever → analyst |
| handoff | analyst → writer |
| transmission | writer → external server |
| delivery | writer → user |

**Caveat for resumed runs.** The tracker and the provenance registry live in process memory. When an approval-graph run is paused and later resumed in a different process (as in the dashboard demos), the resumed process has a fresh monitor, so:

- the closing *transmission* event is not recorded;
- the *delivery* event is logged under the resumed process's run ID.

In the persisted logs, none of the three paused-and-resumed demo runs has a transmission event. The one demo run that was not paused has the full sequence of six events.

### 4.8 Provenance-authoritative sensitivity (shadow mode)

For `send_result`, an authoritative label is computed as

$$v_{\mathrm{auth}} = \max(\mathrm{eff}(v_{\mathrm{prov}}),\ v_{\mathrm{decl}}),\qquad \mathrm{eff}(\mathrm{None}) = 1$$

The agent's declaration is retained for comparison, and mismatches are flagged.

In the default `sensitivity_mode="shadow"`, the **enforced decision still uses the declared value**. The decision the authoritative label *would* produce is logged, together with `would_change_outcome`. An `enforce` mode exists and is covered by a unit test, but **it is not enabled anywhere in the application**.

### 4.9 Recorded, propagated, scored: the live handoff limitation

Three distinct properties must not be conflated:

| Property | Status in the current implementation | Evidence |
|---|---|---|
| (1) Agent-to-agent handoffs are **recorded** | yes: six event types, in order, with sender, receiver, refs and flags | `agents/handoffs.py`; `TrajectoryMonitor.record_handoff` |
| (2) Provenance is **propagated** through handoffs | yes: derived refs inherit labels; origins trace back to tool calls | `governance/provenance.py` (`derive`, `origins`, `agent_label`) |
| (3) Handoff events are **incorporated into the scored trajectory** | **no**: `record_handoff` never appends to `TrajectoryMonitor.trajectory`, and only executed *tool* actions enter the classifier's prefix. Live tool actions are always `internal` reads or `external` sends, so `cross_agent` never occurs in a live scored trajectory | `governance/trajectory_monitor.py` (`evaluate`, `record_handoff`); `agents/tools.py` |

**Consequence.** Although PrivAgent instruments agent-to-agent handoffs through a separate provenance and logging mechanism, these events are not incorporated into the trajectory features used by the deployed classifier. The system therefore does not yet provide complete ML-based monitoring of cross-agent information flow during live execution. This limits what can be concluded about detecting attacks that propagate sensitive information across agent boundaries.

**How this relates to `path_cross_agent_leak` (6/107).** The relationship needs care:

- The 6/107 figure is an **offline** result on the synthetic held-out set. In those trajectories, cross-agent moves *are* present as actions (`destination_category = cross_agent`).
- The miss is therefore a **generalisation failure of the classifier**, not a consequence of the live handoff exclusion.
- The two limitations compound. The classifier rarely recognises this unseen pattern even when cross-agent steps are visible. And in live execution, those steps are not presented to it at all.

The paper therefore draws no conclusion about live detection of cross-agent leakage.

### 4.10 Policy override conflicts and decision precedence

We inspected `risk_engine.py`, `policy_engine.py`, `trajectory_monitor.py` (`_decide`) and the approval gate (`governance/approval.py`, `gate`). Decisions combine as follows:

1. **ML-generated decision:** the AutonomyController maps r through the thresholds.
2. **Policy-generated decision:** the first rule that fires (R1, R2, R3, in that order), or none.
3. **Final enforced decision:** *if a rule fires, its decision replaces the ML decision*; otherwise the ML decision stands. The audit log records the score, the final decision and its source (`ml_model` or `policy_engine`). **The ML decision is not logged as a separate field**, though it can be recomputed from the score.
4. **Optional approval outcome** (approval graph only): `gate()` takes the final decision. The escalation-only flow rule may raise AUTONOMOUS or RESTRICTED to HUMAN_APPROVAL. A HUMAN_APPROVAL decision is offered for review, and an approval **executes** the action.

Figure 2 traces how the four decisions combine.

![Figure 2. Decision precedence. A firing policy rule replaces the ML decision, so R2 can relax an ML BLOCKED to HUMAN_APPROVAL. In the approval graph, that action becomes executable after approval.](figures/r04_decision_precedence.png)

**A policy rule can downgrade a stronger ML decision.** Because a firing rule replaces the ML decision, R2 turns an ML **BLOCKED** into **HUMAN_APPROVAL** when R1 does not fire. R1 is checked first, so after two or more prior sensitive actions, R1 blocks instead. We observed the downgrade in two places:

- In the Attack Lab replay, in three scenarios (`prompt_injection` step 5, `tool_poisoning` step 4, `data_exfiltration` step 3), with ML scores of 0.995–0.999.
- In the persisted approval log of a dashboard demo run (`demo_9e6a8ae2`, scenario "HR summary, analyst declares sensitive"). The ML score was 0.9952, above the BLOCKED threshold of 0.85. The final decision was HUMAN_APPROVAL from `policy_engine`, and the action was **offered for review**. The reviewer rejected it, so nothing was sent; an approval would have executed it.

**Why it matters.** In the default graph, HUMAN_APPROVAL is not executed, so the downgrade has no effect. In the approval graph, it turns a model block into a human decision.

For Experiment 5's two policy-escalated scenarios, the ML score was not stored. Whether they involved an ML BLOCKED therefore cannot be verified from the results (Section 9).

**Proposed future work, not implemented.** We recommend the security invariant *"a BLOCKED decision must never be automatically downgraded to HUMAN_APPROVAL, RESTRICTED or AUTONOMOUS"*, together with these rules:

- policies may escalate restrictions but must not relax them;
- conflicts resolve to the more restrictive outcome;
- the ML and policy decisions are logged separately;
- every override carries an explicit reason.

The policy engine was not changed for this revision.

### 4.11 Human approval and execution ledger (opt-in)

The workflow is used only with `build_graph(..., approvals=..., checkpointer=...)`. The writer is split into four nodes:

| Node | Role |
|---|---|
| `writer_compose` | the LLM step |
| `transmission_gate` | governance and the escalation-only flow rule, run once |
| `human_approval` | `interrupt()` |
| `transmission_execute` | re-checks the payload digest and the signed token, claims the action ID in a SQLite ledger, then calls the tool |

**The ledger** permits **at most one execution attempt per action ID**. It does not provide exactly-once delivery: after a crash at or after the claim, the states `executing` and `failed` do not record whether delivery happened.

**Binding.** The pre-send check does not recompute the destination, tool or server identity.

**Keys.** The approval key derives from the same master key as checkpoint encryption.

Figure 3 shows the lifecycle of a request in the approval graph.

![Figure 3. Lifecycle of a request in the opt-in approval graph.](figures/r11_approval_lifecycle.png)

### 4.12 Audit logging

Three append-only JSONL logs record tool decisions, handoffs and approval events. They are append-only by convention and are not hash-chained, unlike [28].

---

## 5. Implementation Summary

**Code base.** Python, LangGraph, FastMCP and scikit-learn. The persistence study recorded Python 3.14.3 and langgraph 1.2.19.

**Data.** `data/generate_trajectories.py` defines nine attack templates:

| Group | Templates |
|---|---|
| Training | `prompt_injection`, `tool_poisoning`, `permission_laundering`, `inter_agent_injection`, `path_exfiltration`, `path_privilege_escalation` |
| Held-out | `data_exfiltration`, `cascading_failure`, `path_cross_agent_leak` |

Labels are assigned by the original rule, from each template's own stages.

**Randomized runs:**

- 0–8 benign steps before a template, 0–3 between stages and 0–4 after;
- 30% of attack runs are compact, with no padding;
- benign runs are length-matched to attack runs.

Variant B (tool swaps) is held out. Variant C is development-only.

**Training.** 1,800 benign and 1,200 attack runs (seed 42), split 60/20/20 by run. Thresholds are tuned on validation only, within bands.

**Consistency.** `tests/test_feature_consistency.py` checks that live scores equal training-row scores exactly.

---

## 6. Experimental Methodology

Every experiment uses synthetic data and scripted components: no real users, no real LLM, no real recipient.

Table 3 lists every experiment with its research question, type of evidence and sample size; Table 4 gives the risk-model evaluation sets.

**Table 3. Experiments, evidence type and sample size.**

| Exp. | RQ | Evidence type | Data / units | What is measured |
|---|---|---|---|---|
| E1 evaluation correction | RQ1 | controlled re-evaluation | legacy generator; run-level splits; 3 held-out types | step-level P/R/F1/AUROC at the stop threshold |
| E2 position shortcut | RQ1 | controlled ablation, selection rule fixed in advance | randomized generator, seed 42 (Table 4) | position-only AUROC; recall by position; position sweep; held-out F1 |
| E3 rich flow features | RQ1 | controlled comparison, decision rule fixed in advance | train/validation only; 3 seeds; LOTO over 6 types; variant C | LOTO AUPRC/recall; variant-C recall; benign-run false alarms |
| Attack Lab | RQ1 | demonstration (not blind) | 7 attacks + 1 benign, one replay each, real MCP servers | caught / missed; ML against policy |
| E4 provenance instrumentation | RQ2 | functional tests (15 + 11) | scripted pipeline runs | completeness, labels, byte-identical on/off behaviour, flags |
| RQ2 misreporting demonstrations | RQ2 | controlled mechanism demonstration | test scenario; 2 dashboard demo runs; E5 `*_misreported` | enforced against shadow score and decision |
| E5 human approval | RQ3 | controlled evaluation, labels fixed in advance | 8 scenarios × 3 configurations × 5 repeats; outcomes from the first run | transmissions at the server; escalations; latency |
| E6 integration tests | all | functional tests | 61 test functions, 6 suites | pass or fail: 61/61 passed when re-run on 11 Nov 2026 in an isolated copy of the repository; the Attack Lab replay was byte-identical to the frozen baseline |
| Persistence study (scope note, Section 7.4) | (approval) | **exploratory**; a separate study with its own pre-registration | 2,940 independent runs | only the ledger and ambiguous-delivery observation is used here |

**Table 4. Risk-model evaluation sets** (seed 42; runs are the independent units).

| Set | Runs (attack / benign) | Steps | Unsafe steps |
|---|---|---|---|
| train | 1,800 (699 / 1,101) | 25,841 | 1,381 |
| validation | 600 (247 / 353) | 8,474 | 502 |
| test | 600 (254 / 346) | 8,708 | 507 |
| held-out types | 600 (300 / 300) | 7,244 | 698 |
| held-out variants (B) | 600 (300 / 300) | 8,550 | 590 |

**Metric levels.** We separate two levels of metric throughout:

- **Step level:** precision, recall, F1, AUROC and false-positive rate over steps, at the stop threshold r ≥ 0.50.
- **Run level:** "runs caught" is the share of attack runs with at least one unsafe step stopped, and "benign-run false alarm" is the share of benign runs with any step stopped.

Steps within a run are dependent, so only run-level proportions carry Wilson intervals [25].

---

## 7. Results

### 7.1 RQ1: trajectory-aware risk detection

#### 7.1.1 Why high evaluation accuracy can be misleading in trajectory-based security models

**A. Trajectory-level data leakage.**

- **The defect.** The original generator assigned the trajectory identifier per *row* (`len(rows)`) rather than per run, and the data was split by row.
- **The effect.** Steps of one execution, which share their prefix, their template and most of their features, were therefore placed in both training and test (Figure 4). The test set contained near-duplicates of training rows. Thresholds were also tuned on training data, and held-out attack types were generated but never scored.
- **The original result** was F1 = 0.999 (P 0.998, R 1.000, AUROC 1.000).
- **The correction.** One ID per run, a 60/20/20 run-level split, validation-only thresholds, scored held-out types, and a separate ID for `get_transmission_log`, which had collided with `send_result`. On the legacy generator, F1 on held-out attack types fell to **0.657** (R 0.559, AUROC 0.905).

**The 0.999 is historical evidence of an evaluation problem. It is not the deployed model's security performance.**

![Figure 4. Original row-level splitting against corrected run-level splitting. Illustrative layout: with row-level IDs, steps of one run fall in both train and test.](figures/r02_row_vs_run_split.png)

**B. Positional shortcut learning.**

- **Fixed positions.** In the legacy data, each template was a short standalone run, so each training attack type's unsafe steps occupied only 1–3 distinct step indices.
- **Position alone predicts the label.** A classifier given only position features reached validation AUROC **0.951**. The prefix-ratio features recovered the step index with R² 0.72.
- **The same action scored differently by position.** During the Stage-1 investigation, the same sensitive external send scored about 0.04 at step 3 of 8 and about 1.0 at step 5 of 8. These values are recorded in the development log, not in a stored result file.
- **Stored corroboration.** On the randomized test split, the Stage-1 model's recall fell from **0.84** (prefix of 0–4 steps) to **0.00** (prefix of 20 or more) (Figure 6).
- **The cause.** `timestamp_norm` also divided by the run's final length, a value that is only known after the run ends (look-ahead).

**The fix** (Figure 5):

1. a randomized generator that embeds templates at random positions;
2. a selection rule fixed before any test data was examined: exclude positional, context-noise and prefix-average features, then choose by validation AUPRC. The result was `trajectory_invariant` (0.970, against 0.896 for action-only).

The deployed model's unsafe-step scores are unchanged under 0–20 inserted neutral steps (score range 0.000), and its recall is between 0.89 and 1.00 across all position bins.

![Figure 5. The positional shortcut, and how position-invariant features remove it.](figures/r03_position_shortcut.png)

![Figure 6. Unsafe-step recall against prefix length on the randomized test split (step level).](figures/r06_position_recall.png)

**C. The generalisation trade-off.** Removing the averaged prefix features removed a position leak, and also a genuine "accumulated sensitivity" signal. Compared with the round-1 model (`trajectory_no_position`):

| Model | `path_cross_agent_leak`: step recall / runs caught | Tool-swapped path variants: runs caught | Held-out types F1 | Variants F1 |
|---|---|---|---|---|
| Round 1 | 0.36 / 0.84 | 0.74–0.96 | 0.763 | 0.667 |
| Deployed | **0.02 / 0.06** | **0.04–0.11** | 0.665 | 0.493 |

Lower apparent performance is the price of removing a shortcut. The remaining weakness on unfamiliar path-dependent attacks and tool-swapped variants shows that the deployed features capture the surface of the training templates better than the underlying flow.

The deployed model leans on the current action: permutation importance (validation AUPRC drop) is 0.752 for `data_sensitivity` and 0.330 for `destination_category`.

**An unexplained observation.** A legacy-trained invariant model scored a higher held-out-types F1 (0.804). It was not selected, because selecting it would have used held-out results.

#### 7.1.2 Results by evaluation stage

Table 5 reports step-level metrics for each evaluation stage, and Figure 7 plots the F1 values.

**Table 5. Trajectory-model step-level metrics by stage.** The sets differ between stages and are **not** directly comparable. Compare in-distribution against held-out *within* each stage.

| Stage | Data / split | Set | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|---|---|
| 0 (historical) | legacy, row split, thresholds on train | test | 0.998 | 1.000 | 0.999 | 1.000 |
| 1 | legacy, run split | test (seen types) | 1.000 | 1.000 | 1.000 | 1.000 |
| 1 | legacy, run split | held-out types | 0.796 | 0.559 | 0.657 | 0.905 |
| 2 (deployed) | randomized, run split | test (seen types) | 0.881 | 0.945 | 0.912 | 0.998 |
| 2 (deployed) | randomized, run split | held-out types | 0.857 | 0.543 | 0.665 | 0.984 |
| 2 (deployed) | randomized, run split | held-out variants (B) | 0.857 | 0.346 | 0.493 | 0.986 |

![Figure 7. F1 by stage and set. Gray: in-distribution test sets. Blue: held-out sets.](figures/r05_evaluation_correction.png)

Table 6 gives the deployed model's run-level results with Wilson intervals.

**Table 6. Deployed model, run-level results** (Wilson 95% CIs).

| Set | Attack type | Runs caught | 95% CI |
|---|---|---|---|
| held-out types | `data_exfiltration` | 101/101 | [0.963, 1] |
| held-out types | `cascading_failure` | 92/92 | [0.960, 1] |
| held-out types | `path_cross_agent_leak` | **6/107** | [0.026, 0.117] |
| held-out variants | `path_exfiltration` | 2/48 | [0.012, 0.140] |
| held-out variants | `path_privilege_escalation` | 6/57 | [0.049, 0.211] |
| test | benign runs with any step stopped | 17/346 (4.9%) | [0.031, 0.077] |
| held-out types | benign runs with any step stopped | 11/300 (3.7%) | [0.021, 0.064] |
| held-out variants | benign runs with any step stopped | 16/300 (5.3%) | [0.033, 0.085] |

**What "6/107" measures:** in the offline held-out evaluation, 6 of the 107 `path_cross_agent_leak` runs had at least one unsafe step scored at or above the stop threshold (r ≥ 0.50). Its step-level recall was 0.019.

The step-level false-positive rate on the test set is 0.8%. Because runs average about 14 steps, these small per-step rates compound into run-level false alarms.

#### 7.1.3 Attack Lab (demonstration)

Against the real MCP servers, full governance caught 6 of 7 scripted attacks, as did ML alone (Table 7). The benign scenario stayed clean. `path_cross_agent_leak` was missed in both modes.

The Attack Lab influenced round-2 feature selection, so **it is not a blind test**. The round-1 model caught 4 of 7.

**Table 7. Attack Lab replay** (one deterministic replay per scenario).

| Scenario | Full governance | ML-only |
|---|---|---|
| `benign_research` | clean | clean |
| `prompt_injection`, `tool_poisoning`, `permission_laundering`, `data_exfiltration` | caught (ML and policy) | caught |
| `path_exfiltration`, `path_privilege_escalation` | caught (ML only) | caught |
| `path_cross_agent_leak` (held out) | missed | missed |

#### 7.1.4 Rich flow features (E3)

**Candidates.** Four position-invariant flow counts were added: `prev_sensitive_handoffs`, `prev_cross_agent`, `sensitive_roles` and `receiver_differs_from_source`. One candidate also dropped `tool_name`.

**Method.** Training and validation data only, three seeds, leave-one-attack-type-out (LOTO). The decision rule was fixed in advance: invariance range 0; paired LOTO AUPRC gain mean − 2·SE > 0; variant-C AUPRC not worse by more than 0.01; false alarms not higher by more than 2 points.

Table 8 summarises the comparison; Figures 8 and 9 show the per-type and variant-C results.

**Table 8. Flow-feature comparison** (means over three seeds).

| Candidate | LOTO AUPRC (per-seed SD) | LOTO recall | LOTO path AUPRC / recall | Variant C recall | Variant C path recall | Validation benign-run false alarm |
|---|---|---|---|---|---|---|
| baseline | 0.801 (0.009) | **0.782** | 0.650 / 0.712 | 0.338 | 0.004 | 0.032 |
| `rich_invariant` | 0.816 (0.029) | 0.667 | 0.775 / 0.730 | 0.495 | 0.304 | **0.015** |
| `rich_invariant_no_tool` | **0.825** (0.011) | 0.706 | **0.791 / 0.784** | **0.549** | **0.476** | 0.019 |

**The trade-off.**

- Path attacks improved: left-out `path_privilege_escalation` AUPRC rose from 0.49 to 0.73.
- Direct attacks worsened when left out. `prompt_injection` recall fell from 1.00 to 0.77 (0.93 without `tool_name`), and `inter_agent_injection` from 1.00 to 0.69.

**The decision.** Both candidates failed the main criterion:

| Candidate | Mean LOTO AUPRC gain | SE |
|---|---|---|
| `rich_invariant` | 0.015 | 0.026 |
| `rich_invariant_no_tool` | 0.024 | 0.027 |

**The frozen baseline was retained.** No rich model was deployed. A flow model would also see zero cross-agent activity live (Section 4.9).

![Figure 8. LOTO AUPRC per left-out attack type (mean over seeds).](figures/r07_phase3_loto.png)

![Figure 9. Variant-C recall, variant-C path-attack recall, and validation benign-run false alarms.](figures/r08_phase3_variantc.png)

### 7.2 RQ2: provenance-derived sensitivity

**Instrumentation (functional tests, E4).** 15 handoff tests and 11 sensitivity tests check:

- that all six handoff types are captured, in order;
- correct labels for HR documents, `employees` records and public web results;
- that blocked calls register nothing;
- unregistered data;
- that unknown is treated as sensitive;
- that declarations can only raise the label;
- keyed fingerprints, and no raw content or fingerprints in the logs;
- **byte-identical prompts, state, trajectory, decisions and scores with instrumentation on and off.**

These are pass/fail tests on scripted runs. They are not detection rates.

**Controlled sensitivity-misreporting demonstration.** The analyst declares `contains_sensitive_data = False` for HR data. Provenance identifies the data as originating from HR documents. Table 9 lists the two evidence sources.

**Table 9. Sensitivity-misreporting evidence: two separate sources, not one experiment.**

| Source | Enforced (declared 0) | Shadow (authoritative 1) | Shadow decision | Status |
|---|---|---|---|---|
| Test scenario `sensitive_send_misreported` (`tests/test_sensitivity_authority.py`) | score ≈ 0.0000005 | score ≈ 0.9995 | – | values recorded in the development log; the test asserts only that shadow > enforced and that the flag is raised |
| Dashboard demo runs `demo_cc0f5f9e`, `demo_89c31726` (persisted `logs/audit_log.jsonl`) | 0.0 → AUTONOMOUS | 0.9952 | HUMAN_APPROVAL, `would_change_outcome = true` | stored |

In each case:

- the declaration is retained;
- the flag `declared_lower_than_provenance` is raised;
- the **default enforcement decision is unchanged**.

**Why the two rows are kept separate.** They are not combined into one result:

- they come from different scenarios and runs: an automated test, and two interactive dashboard demo runs;
- they were recorded in different places: a development-log report, and the persisted audit log.

The stored audit log rounds scores to four decimals, so the demo's enforced 0.0 does not contradict a very small positive score. Neither source estimates how often misreports are detected.

**Outcome of the stored demo runs.** In the approval graph, the flow rule escalated both sends to HUMAN_APPROVAL. The reviewer **approved** both, and both were **executed** (`logs/approval_log.jsonl`). The provenance evidence informed the review; it did not by itself prevent the transmission.

**The behavioural consequence** (E5). In the `current` configuration, both `*_misreported` attack sends were scored AUTONOMOUS and **were transmitted**. In the approval configurations, they were escalated by the provenance-based flow rule.

**Interpretation.** These are **controlled mechanism demonstrations**. They show that provenance can expose a discrepancy between declared and data-derived sensitivity. They are **not** an estimate of misreport-detection accuracy. Provenance enforcement is not globally enabled, and its false-positive cost is unmeasured. Maximum-over-inputs inheritance over-labels derived content, and sensitivity of arbitrary derived content is not assessed beyond inheritance and the user-input regex.

**A future experiment, not conducted.** A controlled study crossing four declaration conditions:

- accurate;
- incorrect (under- and over-reporting);
- missing;
- contradictory (different agents declaring differently);

with data of known provenance, measuring flag precision and recall, the enforced decision in shadow and enforce modes, and benign false positives. It should run on synthetic and real-LLM pipelines.

### 7.3 RQ3: human approval

Table 10 lists the outcome of every Experiment 5 scenario, and Figure 10 shows the totals.

**Table 10. Experiment 5** (first run of each scenario; transmissions counted at the external server).

| Scenario | Label | Current: decision → sent | Approval paused by | Accurate reviewer: sent | Approve-all: sent |
|---|---|---|---|---|---|
| `public_answer` | benign | – → 0 | – | 0 | 0 |
| `public_summary_sent` | benign | AUTONOMOUS → 1 | – | 1 | 1 |
| `hr_answer_internal` | benign | – → 0 | – | 0 | 0 |
| `hr_summary_to_hr_partner` | benign | HUMAN_APPROVAL → 0 | policy_engine | 1 | 1 |
| `hr_exfil_declared` | attack | HUMAN_APPROVAL → 0 | policy_engine | 0 | 1 |
| `hr_exfil_misreported` | attack | AUTONOMOUS → **1** | flow_rule | 0 | 1 |
| `finance_exfil_misreported` | attack | AUTONOMOUS → **1** | flow_rule | 0 | 1 |
| `hr_bulk_exfil` | attack | BLOCKED → 0 | – | 0 | 0 |

**Totals.**

| | Current | Accurate reviewer | Approve-all |
|---|---|---|---|
| Attack transmissions executed (of 4) | 2 | 0 | 3 |
| Requested benign sends completed (of 2) | 1 | 2 | 2 |

There were 4 approval requests: 2 from the flow rule, both attacks, and 2 from R2, one of them benign. The gate itself added a mean of 0.18–0.19 ms. Runs that did not pause took 9.6–31.0 ms longer.

![Figure 10. Experiment 5 transmission outcomes by configuration.](figures/r09_approval_outcomes.png)

**Interpretation.**

- **The pause works.** The workflow demonstrates a controlled mechanism for pausing and reviewing external transmissions.
- **It depends on the reviewer.** An accurate reviewer prevented both misreported exfiltrations and allowed the legitimate HR send. An approve-everything reviewer let through *more* attacks (3) than the pipeline without approval (2) [23].
- **Evidence size.** Eight scripted scenarios demonstrate the mechanism. They do not estimate rates, and no real reviewers were studied.

**Supporting functional tests.** These cover a pause before the send; rejection sending nothing; digest and token checks; at most one execution attempt per action ID; and restart recovery across processes.

### 7.4 Persistence and recovery (scope note)

The persistence of the approval store is the subject of a **separate study** with its own pre-registration (v1.1; amendment v1.2 awaiting approval). Its confirmatory experiment has **not** been run, and two of its preconditions are unimplemented:

- PC1, pre-send verification of the approved-action digest;
- PC2, canonical digest encoding.

Only one exploratory observation bears directly on this paper's claims. In a leave-one-component-out study of 2,940 independent synthetic runs:

- after a crash following the send, the execution ledger prevented a second delivery on retry (0/120);
- but the ledger entry remained `executing`, so delivery was not recorded;
- without the ledger, the action was delivered twice (30/30 runs per configuration).

This supports the claim of at most one execution attempt per action ID, and it exposes that delivery is ambiguous after a crash. All other persistence findings (tamper detection, deserialisation, confidentiality, overhead) are **exploratory**. They are left to the separate study and are not claimed here.

---

## 8. Discussion

**RQ1.** Trajectory context does change risk assessment. The deployed model detects every run of the seen attack types and of two held-out *direct* attack types. But its step-level recall on held-out types is 0.543 and its F1 on tool-swapped variants 0.493, and it catches only 6/107 runs of the held-out path-dependent attack.

The main lesson is methodological. Near-perfect detection (0.999) was inflated by leakage, and the corrected model then relied on attack position. Removing the shortcut traded away path-attack generalisation. Flow features recovered some of it, but at the cost of direct-attack detection, and did not clear the pre-set rule. No feature set dominated.

Because handoffs are not scored live (Section 4.9), these results do not establish live ML detection of cross-agent leakage.

**RQ2.** Yes, in controlled settings. Provenance labels are computed without changing agent behaviour, and they expose under-reported sensitivity. In the stored demo runs, the shadow score was 0.9952 where the enforced score was 0.0. A separate development-log example shows the same direction (Section 7.2). The evidence is a mechanism demonstration on scripted runs. Enforcement is not enabled, and accuracy over realistic declarations is unknown. In both stored demo runs, the escalated sends were then approved by the reviewer and transmitted, so the flag informed the review but did not itself prevent the transmission.

**RQ3.** The approval workflow pauses before the external send, binds review to an action identifier and digests, and avoids repeated execution attempts. Its effect on security is determined by the reviewer: 0/4 attack sends with an accurate reviewer, 3/4 with an approve-all reviewer. It is weakened further by two things:

- the pre-send binding is incomplete;
- policy precedence can route an ML BLOCKED decision to review (Section 4.10).

**ML against deterministic blocking.** Where both mechanisms fire, attribution is ambiguous: four of the six caught Attack Lab attacks were stopped by both.

---

## 9. Limitations and Threats to Validity

**A. Evaluation limitations.**

1. **Synthetic trajectories** from nine scripted templates, labelled by the templates' own rule. About 1% of benign steps match the path rule but are labelled safe; this was a development observation, not stored.
2. **Scripted attacks and LLM.** Attack Lab steps are hand-specified. No LLM is deceived, and every test and experiment uses a scripted LLM.
3. **Limited attack diversity.** Three held-out types and one variant surface.
4. **Limited independent seeds.** One data seed for the deployed metrics, three for E3. No step-level confidence intervals.
5. **No independent replication.** Selection effects exist: the Attack Lab influenced round-2 selection.

**B. Machine-learning limitations.**

1. **Initial evaluation leakage** (corrected; Section 7.1.1).
2. **Positional shortcut learning** (removed by construction, at a cost).
3. **Weak generalisation to unseen path-dependent attacks** (6/107 runs).
4. **Tool-swapped variants** (F1 0.493).
5. **Handoffs excluded from the deployed model's scored trajectory** (Section 4.9).
6. **Reliance on the current action and declared sensitivity.** A misreported send after fewer than two sensitive reads passes both the model and the rules in the default pipeline.

**C. Runtime architecture limitations.**

1. **Provenance remains in shadow mode.** Sensitivity enforcement is not globally active.
2. **Cross-agent flow is not directly scored** by the live ML model. Live tool actions are never `cross_agent`.
3. **Limited sensitivity assessment of derived content.** Assessment is maximum inheritance plus a user-input regex, which over-labels and does not inspect derived content.
4. **Policy precedence.** A rule can relax an ML BLOCKED decision (Section 4.10).
5. **RESTRICTED restricts nothing.** The audit log is not tamper-evident.
6. **In-memory state.** Provenance and the monitor are lost on restart.

**D. Human-approval limitations.**

1. **Simulated reviewers only** (accurate and approve-all); there was no human reviewer study.
2. **Effectiveness depends on the reviewer.**
3. **Incomplete binding.** The destination, tool and server identity are not re-verified before sending. The approval key shares the master key, so a master-key holder can forge approvals.
4. **No exactly-once external delivery.** Crash outcomes after the ledger claim are ambiguous, and the external server offers no idempotency key.
5. **Persistence and recovery:**
   - single SQLite writer;
   - the key is stored next to the data;
   - no rollback detection or context-bound encryption;
   - approvals are lost on a crash before persistence.

   The persistence evidence is exploratory.

**E. Deployment limitations.**

1. **No production deployment**, and no production readiness is claimed.
2. **No comprehensive real-LLM evaluation** (contrast [28]).
3. **No large-scale MCP deployment evaluation:** four local stdio servers with synthetic data.
4. **Limited external-system testing.** The external server is a synthetic endpoint with an in-memory log.
5. **The live dashboard path does not use approvals.** A minimal Human Approval page exists and is tested only on synthetic demo runs.

Table 11 summarises the most consequential limitation in each category.

**Table 11. Limitations summary.**

| Category | Most consequential item | Effect on conclusions |
|---|---|---|
| Evaluation | synthetic templates, scripted LLM | results describe detection of template-like action patterns only |
| ML | 6/107 on held-out path attack; variants F1 0.493 | generalisation to unseen compositional attacks is weak |
| Runtime | handoffs not scored; provenance shadow-only | no claim about live ML detection of cross-agent flow, or about enforced provenance |
| Approval | reviewer-dependent; incomplete binding; BLOCKED → HUMAN_APPROVAL possible | approval adds control, not guaranteed security |
| Deployment | no production or real-LLM evaluation | no deployability claim |

---

## 10. Future Work (proposed, not implemented)

1. **Decision precedence:** the invariant and conflict-resolution rules of Section 4.10, with separate logging of ML and policy decisions.
2. **Scored handoffs:** live handoff events in the scored trajectory, then a re-evaluation of the flow features under a pre-set protocol.
3. **Provenance enforcement:** enforced provenance with a measured false-positive cost, the declaration-condition experiment of Section 7.2, and influence-based label propagation [9].
4. **Real-LLM evaluation** on injection benchmarks [5], [6], extended to multi-agent handoffs, and a comparison with an enforcement-point design such as [28].
5. **Approval binding:** recompute the destination, tool and server identity before sending; separate the approval keys; give RESTRICTED a real meaning.
6. **Persistence:** context-bound encryption, rollback detection and recipient idempotency keys, then the pre-registered confirmatory persistence study.
7. **Tamper-evident audit logging** (a hash chain, as in [28]).
8. **A reviewer study and independent replication.**

---

## 11. Conclusion

PrivAgent demonstrates the feasibility of integrating trajectory-aware risk assessment, deterministic policy enforcement, provenance instrumentation and optional human approval into a LangGraph multi-agent architecture with real MCP tool servers.

Its evaluation, on synthetic trajectories with scripted components, highlights a methodological finding: apparently near-perfect detection (F1 0.999) was substantially inflated by trajectory-level leakage, and the corrected model then exploited a positional shortcut. After both were corrected:

- the deployed model detects several attack patterns, including every run of two held-out direct attack types;
- it struggles with unseen path-dependent attacks (6 of 107 runs) and tool-swapped variants (F1 0.493).

Richer flow features improved path attacks but weakened direct ones, and were not adopted.

In controlled demonstrations, provenance instrumentation exposes discrepancies between declared and data-derived sensitivity, though it remains in shadow mode. The approval workflow demonstrates a controlled mechanism for pausing and reviewing external transmissions, but its effectiveness depends on reviewer behaviour and has not been evaluated with real reviewers.

Live cross-agent flow is not scored by the classifier, and policy precedence can relax a model block. These mechanisms have not been validated under realistic or production conditions.

---

## References

[1] Anthropic, "Introducing the Model Context Protocol," Nov. 25, 2024. [Online]. Available: https://www.anthropic.com/news/model-context-protocol

[2] Model Context Protocol, "Specification," revision 2025-06-18. [Online]. Available: https://modelcontextprotocol.io/specification/2025-06-18

[3] LangChain, "LangGraph: Human-in-the-loop / Interrupts," documentation. [Online]. Available: https://docs.langchain.com/oss/python/langgraph/interrupts (accessed Nov. 10, 2026).

[4] K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection," in *Proc. 16th ACM Workshop on Artificial Intelligence and Security (AISec)*, 2023, pp. 79–90.

[5] Q. Zhan, Z. Liang, Z. Ying, and D. Kang, "InjecAgent: Benchmarking indirect prompt injections in tool-integrated large language model agents," in *Findings of the Association for Computational Linguistics: ACL 2024*, 2024.

[6] E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr, "AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents," in *Advances in Neural Information Processing Systems 37 (Datasets and Benchmarks Track)*, 2024.

[7] E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and F. Tramèr, "Defeating prompt injections by design," arXiv:2503.18813, 2025. Preprint; no venue found as of Nov. 10, 2026.

[8] M. Costa, B. Köpf, A. Kolluri, A. Paverd, M. Russinovich, A. Salem, S. Tople, L. Wutschitz, and S. Zanella-Béguelin, "Securing AI agents with information-flow control," arXiv:2505.23643, 2025. Preprint; no venue found as of Nov. 10, 2026.

[9] S. A. Siddiqui, R. Gaonkar, B. Köpf, D. Krueger, A. Paverd, A. Salem, S. Tople, L. Wutschitz, M. Xia, and S. Zanella-Béguelin, "Permissive information-flow analysis for large language models," arXiv:2410.03055 (v3, 2026). Listed by Microsoft Research as published in *Transactions on Machine Learning Research*; OpenReview not checked.

[10] X. Zhang, Z. Cheng, K. Liu, Z. Sun, S. Fan, T. Yuan, B. Yuan, W. Qiang, and D. Zou, "AGATE: Provenance-based runtime defense against compositional attacks on LLM agents," arXiv:2609.30830, Sep. 2026. Preprint.

[11] H. Hou, Y. Ma, and J. Miao, "CapAgent: Semantic data-flow governance for LLM agents in big-data cognitive computing," *Big Data and Cognitive Computing*, vol. 10, no. 9, art. 293, 2026, doi: 10.3390/bdcc10090293. Abstract and bibliographic record only.

[12] C. Li, L. Zhang, J. Zhai, S. Feng, X. Yang, H. Wang, S. Dou, Y. Ji, Y. Hu, Y. Wu, Y. Liu, and D. Zou, "Towards security-auditable LLM agents: A unified graph representation," arXiv:2605.06812, 2026. Preprint.

[13] Z. Wang, "Proof-carrying agent actions: Model-agnostic runtime governance for heterogeneous agent systems," arXiv:2606.04104, Jun. 2026. Preprint.

[14] T. Shi, J. He, Z. Wang, H. Li, L. Wu, W. Guo, and D. Song, "Progent: Programmable privilege control for LLM agents," arXiv:2504.11703, 2025. Preprint; no venue found as of Nov. 10, 2026.

[15] Y. Wu, F. Roesner, T. Kohno, N. Zhang, and U. Iqbal, "IsolateGPT: An execution isolation architecture for LLM-based agentic systems," in *Proc. NDSS Symposium*, 2025.

[16] R. Sequeira, S. Damianakis, U. Iqbal, and K. Psounis, "Agent-Sentry: Bounding LLM agents via execution provenance," arXiv:2603.22868, 2026. Preprint.

[17] D. E. Denning, "A lattice model of secure information flow," *Commun. ACM*, vol. 19, no. 5, pp. 236–243, 1976.

[18] P. Buneman, S. Khanna, and W.-C. Tan, "Why and where: A characterization of data provenance," in *Proc. ICDT*, LNCS 1973, 2001, pp. 316–330.

[19] J. H. Friedman, "Greedy function approximation: A gradient boosting machine," *Ann. Statist.*, vol. 29, no. 5, pp. 1189–1232, 2001.

[20] F. Pedregosa *et al.*, "Scikit-learn: Machine learning in Python," *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.

[21] S. Kapoor and A. Narayanan, "Leakage and the reproducibility crisis in machine-learning-based science," *Patterns*, vol. 4, no. 9, art. 100804, 2023.

[22] R. Geirhos, J.-H. Jacobsen, C. Michaelis, R. Zemel, W. Brendel, M. Bethge, and F. A. Wichmann, "Shortcut learning in deep neural networks," *Nat. Mach. Intell.*, vol. 2, no. 11, pp. 665–673, 2020.

[23] R. Parasuraman and V. Riley, "Humans and automation: Use, misuse, disuse, abuse," *Human Factors*, vol. 39, no. 2, pp. 230–253, 1997.

[24] M. Dworkin, "Recommendation for block cipher modes of operation: Galois/Counter Mode (GCM) and GMAC," NIST SP 800-38D, Nov. 2007.

[25] E. B. Wilson, "Probable inference, the law of succession, and statistical inference," *J. Amer. Statist. Assoc.*, vol. 22, no. 158, pp. 209–212, 1927.

[26] R. G. Newcombe, "Interval estimation for the difference between independent proportions: Comparison of eleven methods," *Statistics in Medicine*, vol. 17, no. 8, pp. 873–890, 1998.

[27] H. Krawczyk, M. Bellare, and R. Canetti, "HMAC: Keyed-hashing for message authentication," RFC 2104, Feb. 1997.

[28] S. Wang, S. Zhu, and R. Li, "Runtime policy enforcement for MCP-based LLM agents," *Electronics*, vol. 15, no. 13, art. 2829, Jun. 2026, doi: 10.3390/electronics15132829.

---

### Appendix A. Reproducibility

| Item | Location |
|---|---|
| Deployed model, thresholds, features | `models/` (equal to `models/baselines/trajectory_invariant_v1/`) |
| Stage 0 and Stage 1 metrics | `research_paper/evidence/` |
| E2, E3, Attack Lab, E5 results | `experiments/results/` |
| Persistence (exploratory) | `snapshots/exploratory_persistence_v1_20261109/` |
| Persisted demo evidence (Sections 4.10, 7.2) | `logs/audit_log.jsonl`, `logs/approval_log.jsonl` |
| Revised figures | `research_paper/revised/build/make_revised_figures.py` |
| Claim-to-evidence map | `research_paper/revised/REVISED_EVIDENCE_MAP.md` |
