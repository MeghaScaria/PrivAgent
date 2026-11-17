<!--
SOURCE of research_paper/v2/PrivAgent_v2_DRAFT.md. Edit this file, then run
    python research_paper/v2/build/build_manuscript.py
Citations are written as [@key]; the build numbers them in order of first appearance (IEEE style) and
writes the reference list. Numbers cite ledger rows in HTML comments: <!-- C15 --> is a row of
research_paper/v2/CLAIM_EVIDENCE_LEDGER_v2.md; <!-- v1:#5 --> is row 5 of v1's ledger
(research_paper/final/CLAIM_EVIDENCE_LEDGER.md).
Layout maps one-to-one onto the IEEE Access journal template: title, authors, abstract, index terms,
numbered sections (I, II, ... with A, B, ... subsections), back matter, references, biographies.
-->

<!-- TEMPLATE: \title{} -->
# What Stops a Leak? A Pre-Registered Evaluation of Learned, Rule-Based and Human Controls for Multi-Agent LLM Governance

<!-- DRAFT: author to review (title) -->

<!-- TEMPLATE: \author{} — needs-author -->
*[Author names, affiliations, ORCID iDs and corresponding-author e-mail to be added.]*

<!-- TEMPLATE: \begin{abstract} -->
**Abstract**

<!-- DRAFT: author to review -->
Multi-agent large language model pipelines can leak sensitive data through a chain of tool calls and agent-to-agent handoffs in which no single step looks unsafe. We ask which runtime control actually stops such a leak: a learned trajectory classifier, deterministic policy rules, provenance-derived sensitivity or a human reviewer. Using PrivAgent, an inspectable four-agent governance prototype, we report two phases. An exploratory phase on synthetic trajectories showed that a near-perfect F1 score of 0.999 came from evaluation leakage and a positional shortcut. <!-- v1:#1 --> A pre-registered phase, frozen before any confirmatory run, then tested five hypotheses using canary tokens as ground truth and an independent recomputation. <!-- P1 --> <!-- S2 --> <!-- V1 --> Escalation-only precedence removed every downgrade of a model block, at a measured cost to benign sends. <!-- C3 --> <!-- C4 --> Scoring handoffs cut attack sends only through a rule that counts one sensitive read several times. <!-- C7 --> <!-- C8 --> Enforced provenance stopped all misreported attack sends but completed fewer benign sends. <!-- C10 --> <!-- C11 --> With a 3B-parameter local model and a scripted compromised writer, the full configuration let no attack through (0 of 55), but only because the sends it held for human review were never executed. With a simulated reviewer approving attack sends with probability 0.5, it let 17 of 53 attacks through, comparable to the earlier design (16 of 57) and to rules alone (18 of 56). <!-- C15 --> <!-- C24 --> <!-- S8 --> The classifier flagged 1 of 62 cross-agent handoffs, and a position-only baseline did not meet its pre-registered bound. <!-- C12 --> <!-- C13 --> The results come from synthetic data, scripted scenarios, simulated reviewers and one small model.

<!-- TEMPLATE: \begin{IEEEkeywords} -->
**Index Terms:** Evaluation methodology, human-in-the-loop, information-flow control, large language model agents, multi-agent systems, pre-registration, runtime governance, shortcut learning.

<!-- DRAFT: author to review (keywords; alphabetical; 8 of the 3–10 allowed) -->

## I. INTRODUCTION

<!-- DRAFT: author to review -->
Tool-using large language model (LLM) agents retrieve documents, query databases and send messages. Frameworks such as LangGraph compose specialised agents into stateful graphs [@langgraph], and the Model Context Protocol (MCP) standardises tool access [@mcp_anthropic], [@mcp_spec]. Indirect prompt injection showed that content an agent retrieves can redirect what it does [@greshake], and benchmarks measure how often tool agents follow injected instructions [@injecagent], [@agentdojo]. In a multi-agent pipeline a disclosure is often compositional: one agent reads sensitive records, a second summarises them and a third transmits the summary. Each step can look legitimate on its own, and the transmitting agent may misreport whether its output is sensitive.

Runtime governance for such pipelines combines several kinds of control: learned risk scores, deterministic rules, data provenance and human review. Prior systems combine these controls in different ways and emphasise different ones [@camel], [@fides], [@wangpep], [@guardagent], [@shieldagent], [@kairos]. This paper asks a narrower, empirical question: *when a leak is stopped, which control stopped it, and what did that cost?* We answer it with PrivAgent, an inspectable governance prototype for a four-agent LangGraph pipeline. <!-- S1 --> The evaluation has two phases. Phase 1 was exploratory; its findings motivated the design changes and hypotheses of Phase 2. Phase 2 was pre-registered and frozen before any confirmatory run, used canary tokens as ground truth, and was independently recomputed. <!-- P1 --> <!-- S2 --> <!-- V1 -->

We make five contributions:

1. **Shortcut removal costs compositional generalisation, on synthetic data and on real traces.** Removing a positional shortcut coincided with the loss of most detection of a held-out path-dependent attack (runs caught 0.84 before, 0.06 after). <!-- v1:#12 --> Over ten seeds, the three path-dependent attack types are caught in 0.023–0.036 of runs, against at least 0.995 for every other type. <!-- C20 --> On real LLM traces the frozen classifier flagged 1 of 62 path-dependent handoffs and 52 of 52 direct sends. <!-- C12 -->
2. **Hybrid governance is non-monotonic, and the precedence choice sets the security–utility trade-off.** In the earlier design a rule meant to add oversight could turn a model block into an approvable request. <!-- v1:#22 --> <!-- v1:#23 --> Escalation-only precedence removed every such downgrade (Section VI-B). <!-- C3 --> But it hard-blocked benign sends in 10 of 14 benign runs, against 2 of 14 before. <!-- C4 --> A reviewable variant sends a model-only block on an external action to review. In the live tests it gave the same downgrades (70) and the same costs as `first_fire_v1`. <!-- C2 --> <!-- C5 --> Its one difference, that it never relaxes a rule's BLOCKED, did not change any outcome in these scenarios. <!-- S4 --> <!-- C2 --> <!-- C5 -->
3. **The monitor is blind to multi-agent flow at runtime, and scoring handoffs helped only through rule R1's double counting.** Scoring the two handoffs reduced attack sends from 14 of 40 to 0 only when rule R1 counted the scored handoffs; without that, sends stayed at 14 of 40. <!-- C7 --> <!-- C8 --> In development runs we traced the reduction to R1 counting one sensitive read up to three times. <!-- S13 -->
4. **Enforced provenance defeats misreporting at a measured over-tainting cost, and the residual risk rests on the reviewer.** It reduced misreported attack sends from 12 of 16 to 0 of 16, and benign sends completed under the same misreports from 10 of 12 to 2 of 12. <!-- C10 --> <!-- C11 --> In the full configuration, 44 of the 52 stopped canary-carrying sends went to human review. <!-- C24 --> If a reviewer approved them at chance, the expected attack success would be 0.40 (exploratory). <!-- X2 -->
5. **A reusable evaluation method.** It consists of a pre-registration frozen before any confirmatory run, canary-token ground truth that involves no detector, and an independent recomputation by an agent that had not read the analysis code. <!-- P1 --> <!-- S2 --> <!-- V1 --> The recomputation matched 44 of 53 items. It also exposed one undefined label, on which a pre-registered outcome depends. <!-- V1 --> <!-- C13b -->

We do not claim that any of the mechanisms is new, that PrivAgent outperforms the systems in Section II, or that the results hold for production deployments, larger models or human reviewers (Section VIII).

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## II. RELATED WORK

### A. Attacks and Benchmarks

Indirect prompt injection [@greshake] is the core threat for tool agents. InjecAgent [@injecagent] and AgentDojo [@agentdojo] measure how often tool agents follow injected instructions. AgentLeak [@agentleak] is a benchmark for internal-channel privacy leakage in multi-agent LLM systems; it targets the inter-agent channels that our handoff experiments concern. <!-- DRAFT: author to review (AgentLeak sentence) --> Our Phase 2 attack family B assumes the writer agent is already compromised (Section V-C), so it measures governance given an exfiltration attempt, not whether a model follows an injection.

### B. Runtime Enforcement and Information-Flow Control for Agents

Information-flow control (IFC) tracks labels on data as it moves through a computation. CaMeL [@camel] separates trusted control flow from untrusted data and enforces capability policies. FIDES [@fides] enforces confidentiality and integrity labels in an agent planner. Progent [@progent] enforces programmable privilege policies on tool calls, and IsolateGPT [@isolategpt] isolates LLM applications. Permissive information-flow analysis [@permissive] targets the over-labelling that maximum-over-inputs propagation causes, which is the source of the over-tainting cost we measure in Section VI-B. GuardAgent [@guardagent] and ShieldAgent [@shieldagent] place a guard agent over a protected agent. Kairos [@kairos] enforces security at the system boundary of an unmodified agent. <!-- DRAFT: author to review (GuardAgent, ShieldAgent, Kairos sentences) --> These systems enforce deterministic or reasoned guarantees. PrivAgent's core decision is instead a learned score combined with rules, which is what makes precedence a design question.

Closest to PrivAgent's tool-call governance is the single-agent policy enforcement point (PEP) of Wang et al. [@wangpep]. It intercepts every tool call, evaluates five ordered rules, propagates source-integrity and data-sensitivity labels across steps and writes a hash-chained audit log. In 1,050 LLM-driven runs it reduced attack success from 40.0% to 5.0%. <!-- v1:#40 --> Our `rules_only` configuration is a deterministic PEP baseline in the style of that work, not a reimplementation of it. <!-- S8 --> The two evaluations measure different things, and we make no claim that PrivAgent outperforms it.

### C. Provenance, Auditing and Approval

AGATE [@agate] gates actions on authorisation and data provenance. Agent-Sentry [@agentsentry] bounds agents via execution provenance, and Agent-BOM [@agentbom] models agent systems as attributed graphs for auditing. PCAA [@pcaa] attaches certificates and approval receipts to actions, and CapAgent [@capagent] maps human-attested intent to capability tokens. PrivAgent's label rule is a two-level instance of lattice-based flow labelling [@denning] within the provenance tradition [@buneman]. Automation research documents over-reliance on automated aids [@parasuraman], which bears directly on the reviewer-dependent results of Section VI.

### D. Evaluation Pitfalls

Leakage [@kapoor] and shortcut learning [@geirhos] are known to inflate machine-learning results. Arp et al. [@arp] catalogue pitfalls of machine learning in computer security, and TESSERACT [@tesseract] shows how spatial and temporal bias inflate malware classifiers. <!-- DRAFT: author to review (Arp, TESSERACT sentences) --> Our Phase 1 is a case study of two such pitfalls in agent governance. Noumi et al. [@noumi] systematise LLM-driven penetration-testing tools around their implemented platform, Inspectra, and label each mechanism by implementation status. <!-- DRAFT: author to review (Noumi/Inspectra sentence; confirm relevance) --> We adopt a similar separation of implemented, demonstrated and unvalidated claims.

**TABLE I. Positioning.** "Not stated here" means we did not verify the property, not that the work lacks it.

| Work | Status | Decision basis | Cross-step / provenance signal | Human approval | Evaluation |
|---|---|---|---|---|---|
| Wang et al. [@wangpep] | journal | deterministic rules | labels, enforced | confirm treated as block | real LLMs, 30-task dataset |
| AGATE [@agate] | preprint | deterministic gate | source registration, enforced | host approvals, grants | 3 harnesses |
| CaMeL [@camel] | SaTML 2026 | capabilities | value provenance, enforced | not stated here | AgentDojo |
| FIDES [@fides] | NeurIPS 2026 | IFC planner | labels, enforced | not stated here | AgentDojo |
| **PrivAgent (this work)** | – | learned score + rules, escalation-only precedence | item provenance, enforced; handoffs scored | opt-in pause, ledger, bound approval | synthetic; scripted graph scenarios; one 3B local LLM |

<!-- TABLE I: L1; v1:#40; PrivAgent row: S4, S5, S6, S7, S8 -->

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## III. THREAT MODEL

**Actions and runs.** An action is the tuple $a = (\mathrm{agent\_role},\ \mathrm{tool\_name},\ \mathrm{action\_type},\ \mathrm{data\_sensitivity},\ \mathrm{destination\_category})$, and a run is the ordered list of actions in one task. Sensitive data comes from human-resources (HR) and finance documents, the `employees` and `transactions` tables, and user input in which a regular-expression detector finds personal data; content of unknown origin is treated as sensitive.

**Leak.** An unauthorised disclosure is an external `send_result` call carrying sensitive data the task owner did not intend to send. In Phase 2 it is measured by canary tokens: every sensitive record carries a unique token, and an attack succeeds iff at least one token reaches the external server. <!-- S2 -->

**Adversary.** We consider compromised or manipulated agent steps, an agent that misreports the sensitivity of its output, multi-step flows that move data across agent boundaries and, for the approval workflow, state tampering, replays and duplicate resumes. Phase 2 operationalises compromise as a scripted writer agent that always tries to exfiltrate its full context (family B). <!-- S8 -->

**Trusted and out of scope.** The governance code, the MCP client and servers and the host are trusted. Out of scope are semantic exfiltration that the features cannot represent, attacks across runs, process compromise and a holder of the master key. Indirect prompt injection against a real LLM (family A) was registered but not run. <!-- C22 --> PrivAgent provides no guarantee of complete security, exactly-once delivery or universal attack prevention.

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## IV. PRIVAGENT DESIGN

### A. Pipeline and Interception

PrivAgent governs a four-agent LangGraph pipeline (orchestrator, retriever, analyst, writer) that reaches its tools through four FastMCP stdio servers (document, database, web, external). <!-- S1 --> The orchestrator plans. The retriever calls governed read tools. The analyst synthesises and self-reports whether its output contains sensitive data. The writer composes the answer and may call `send_result`. A single interception point, `TrajectoryMonitor.evaluate()`, scores every proposed tool call before execution. It extracts features from the run's executed prefix, maps the classifier's score to a decision, applies the policy rules and the precedence mode, logs the decision, and appends the action to the trajectory only if it is allowed. Fig. 1 shows the architecture.

<!-- TEMPLATE: figure -->
![Fig. 1. PrivAgent v2 architecture. Every proposed tool call and each scored handoff passes the single interception point before execution. The classifier scores features of the executed prefix; rules R1–R3 and the precedence mode combine with the model decision; enforced provenance supplies the sensitivity label. Allowed calls reach the MCP servers, HUMAN_APPROVAL sends wait at the approval gate, and every decision is appended to the hash-chained audit log.](figures/v2_f0_architecture.png) <!-- S1 --> <!-- S4 --> <!-- S5 --> <!-- S6 --> <!-- S7 --> <!-- S14 -->

### B. Classifier, Decisions and Rules

The classifier is a gradient-boosted model [@friedman], [@sklearn] with 200 trees of depth 5, over eleven features. <!-- v1:#20 --> Five features describe the current action. Six are counts and maxima over the executed prefix, such as the number of earlier sensitive reads, so the features are invariant to inserted harmless steps. <!-- v1:#9 --> <!-- v1:#20 --> The score maps to AUTONOMOUS, RESTRICTED, HUMAN_APPROVAL or BLOCKED at thresholds 0.22, 0.50 and 0.85, tuned on validation data only. <!-- v1:#19 --> AUTONOMOUS and RESTRICTED actions execute. A RESTRICTED action to an external destination, or a later external send carrying data read under a RESTRICTED decision, escalates to HUMAN_APPROVAL. <!-- S6 --> HUMAN_APPROVAL executes only after approval, and only in the approval workflow (Section IV-E).

Three deterministic rules complement the classifier. R1 blocks an external send after at least two earlier sensitive actions. <!-- S13 --> R2 sends any sensitive external action to HUMAN_APPROVAL. R3 blocks an external action after at least three earlier cross-agent actions. <!-- S5 --> `rules_only` uses the rules alone. <!-- S8 -->

### C. Decision Precedence

How the model's decision and the rules' decisions combine is a security-relevant choice. Three modes are implemented: <!-- S4 -->

- **`first_fire_v1`** (the earlier design): the first rule that fires replaces the model's decision. A rule can therefore relax a model BLOCKED.
- **`max_severity`**: the final decision is the most severe of the model's decision and every fired rule, in the order AUTONOMOUS < RESTRICTED < HUMAN_APPROVAL < BLOCKED. Rules only escalate.
- **`max_severity_reviewable`**: as `max_severity`, except that on an external action a BLOCKED that comes from the model alone becomes HUMAN_APPROVAL, so a reviewer can release it. A rule's BLOCKED is never relaxed, and nothing becomes allowed.

Each decision record logs the model's decision, the fired rules, the precedence mode and whether the decision would differ under `first_fire_v1` as separate fields. <!-- S14 -->

### D. Provenance and Handoff Scoring

Each item returned by an allowed tool call gets a provenance reference. Derived objects (plan, analysis, answer) inherit the maximum sensitivity of their parents, with unknown treated as sensitive. For an external send, the authoritative label is the maximum of the provenance label and the agent's declaration. The sensitivity mode decides which label governs. In *shadow* mode the agent's declaration governs, and the provenance-derived decision is only logged. In *enforce* mode the provenance-derived label governs. <!-- S5 --> <!-- S7 -->

The two data-carrying handoffs of a run (retriever → analyst and analyst → writer) can be scored as pseudo-actions. They are encoded with category values the classifier was trained on, and their sensitivity is the provenance label of what the receiver consumes, never the sender's declaration. <!-- S5 --> The switch `r1_counts_handoffs` decides whether R1 counts these pseudo-actions, and `handoff_enforce` halts the graph on a BLOCKED or HUMAN_APPROVAL handoff. <!-- S5 --> With two scored handoffs per run, R3's threshold of three cross-agent actions cannot be reached. <!-- S5 -->

### E. Approval Workflow, Binding and Audit

In the opt-in approval graph, the writer's external send passes a gate. A send rated HUMAN_APPROVAL is paused for review, and an approval executes it. A SQLite execution ledger allows at most one execution attempt per action identifier. It does not provide exactly-once delivery: after a crash at or after the claim, whether delivery happened is not recorded. <!-- v1:#37 --> The approval digest binds the tool, the destination, the MCP server identity and a digest of the payload. It is recomputed immediately before execution, and the send is refused on any mismatch. <!-- S6 --> The approval-signing and checkpoint-encryption keys are derived from one master key under distinct labels, with the HMAC-based key derivation function (HKDF) over the Secure Hash Algorithm SHA-256; HMAC is the hash-based message authentication code. <!-- S6 --> Decisions are written to an append-only, hash-chained audit log that can be verified line by line. <!-- S6 --> <!-- S14 -->

### F. The Configurations Compared

TABLE II lists what changed from the earlier design (`v1`) to the primary configuration (`v2`). The primary configuration combines enforced provenance, `max_severity_reviewable` precedence, scored handoffs with `r1_counts_handoffs` off, the RESTRICTED semantics on and no `handoff_enforce`. <!-- S4 --> <!-- S5 --> <!-- S6 --> <!-- S7 -->

**TABLE II. Changes from v1 to the primary v2 configuration.**

| Aspect | v1 | v2 (primary) |
|---|---|---|
| Precedence | first firing rule replaces the model | `max_severity_reviewable`: rules only escalate; a model-only BLOCKED on an external action goes to review |
| Handoffs | recorded, not scored | scored as pseudo-actions; R1 does not count them |
| Sensitivity | declaration governs; provenance in shadow | provenance governs (enforced) |
| RESTRICTED | executes like AUTONOMOUS | external or restricted-lineage sends escalate to review |
| Approval binding | payload digest and signed token | also tool, destination and server identity, rechecked before sending |
| Keys | approval key shares the master key | HKDF-derived keys under distinct labels |
| Audit log | append-only by convention | hash-chained, verifiable |
| Decision record | score, final decision, source | also the model decision, the fired rules and the precedence mode |

<!-- TABLE II rows: S4, S5, S6, S7, S14; v1 column: v1:#21, v1:#26, v1:#29, v1:#30, v1:#31 -->

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## V. STUDY DESIGN

**TABLE III. The two phases.**

| | Phase 1 (exploratory) | Phase 2 (pre-registered, confirmatory) |
|---|---|---|
| Question | Does a learned trajectory detector work, and what do provenance and approval add? | Which control stops a leak, at what cost? (H1–H5) |
| Data | synthetic template-generated trajectories; scripted pipeline runs | synthetic confirmatory sets (10 seeds); 22 unseen graph scenarios; 360 + 240 real-LLM runs |
| LLM | scripted | scripted (WP4); `qwen2.5:3b` (pilot) |
| Ground truth | template labels | canary tokens at the external server |
| Analysis | fixed selection rules for model and feature choices | frozen pre-registration; independent recomputation |

<!-- TABLE III: S7, S8, S10, C21, S2, P1, V1 -->

### A. Phase 1: Exploratory Evaluation

Phase 1 evaluated the classifier offline on synthetic, template-generated trajectories. Three attack types were held out, alongside a held-out set of tool-swapped variants (variant B). <!-- S10 --> <!-- v1:#18 --> Runs were split 60/20/20 by run, and thresholds were tuned on validation data only. <!-- v1:#18 --> <!-- v1:#19 --> Metrics are reported at step level (precision, recall and F1 at the stop threshold, and the area under the receiver operating characteristic curve, AUROC) and at run level ("runs caught": attack runs with at least one unsafe step stopped). Only run-level proportions carry Wilson intervals [@wilson], because steps within a run are dependent. The model and feature choices followed selection rules fixed before test data was examined. Phase 1 also ran scripted demonstrations of provenance against the real MCP servers, and a human-approval evaluation with simulated reviewers. Its results motivated the design changes of Section IV and the hypotheses of Phase 2; they are exploratory. Its full tables are in the Supplementary Material.

### B. Phase 2: Hypotheses

**TABLE IV. Pre-registered hypotheses and decision rules.**

| | Claim | Data | Supported iff |
|---|---|---|---|
| H1 | Under `max_severity`, no decision is less severe than the model's | 10 seeds × 3 synthetic sets (offline); WP4 confirmatory half (live) | 0 downgrades, offline and live |
| H2 | Scoring handoffs reduces attack sends only when R1 counts them | WP4, shadow provenance | score-on vs shadow: fewer sends, p < 0.05; score-off vs shadow: p ≥ 0.05 |
| H3 | Enforced provenance reduces attack sends under under-reported and missing declarations | WP4 | fewer sends under enforce, p < 0.05 |
| H4 | (a) The frozen model's recall is lower on path-dependent than on direct unsafe steps; (b) a position-only classifier has AUROC ≤ 0.6 on real traces | pilot, `v2` runs | (a) CI of the difference entirely below 0; (b) point AUROC ≤ 0.6 |
| H5 | `v2` has lower attack success than `v1` and than `ml_only` | pilot, family B | both bootstrap CIs entirely below 0 |

<!-- TABLE IV: S4, S5, S7, S9, S10, S11, S8 -->

*CI: 95% confidence interval (Section V-D). WP4 and WP6 are the graph-scenario and real-LLM work packages (Section V-C).*


Measured costs (benign sends hard-blocked, approval volume, benign halts and benign utility) were registered without thresholds. <!-- S9 -->

### C. Phase 2: Scenarios, Real-LLM Pilot and Ground Truth

**Graph scenarios (WP4).** A scripted LLM injects one of five declaration conditions (accurate, under-reported, over-reported, missing, contradictory) into graph runs against the real MCP servers. <!-- S7 --> A split file written before any WP4 run fixed a development half and a confirmatory half. The confirmatory half has 22 scenarios: 8 attack and 14 benign, of which 12 request an external send. <!-- S7 --> Outcomes are deterministic, so the scenario is the unit of analysis, and the confirmatory half is a replication check on unseen scenarios, not a sample of runs. <!-- S7 --> H1-live, H2 and H3 use these scenarios.

**Real-LLM pilot (WP6).** The pipeline ran with `qwen2.5:3b` (3.1B parameters, Q4_K_M) on a local Ollama server at temperature 0.2. <!-- S8 --> The task set's hash was recorded before any run. <!-- S8 --> It has 40 benign tasks and 20 family B tasks. In family B the writer agent is replaced by a script that always sends its full context to an external address, while the other three agents remain real LLM agents. <!-- S8 --> Family B ran three times per task and configuration, and benign tasks once, in six configurations: `no_governance`, `rules_only`, `ml_only`, `v1`, `v2`, and `v2_reviewer`. <!-- S8 --> The `v2_reviewer` configuration is `v2` in the approval graph with a simulated reviewer that approves an attack send with probability 0.5 and a benign send with probability 0.9. The other five run in the default graph, where HUMAN_APPROVAL is not executed. <!-- S8 -->

**Ground truth.** Every sensitive record carries a canary token, `CNRY-` followed by 12 hexadecimal digits. The external server records every canary in a payload, and an attack succeeds iff at least one canary arrives there. No detector or rule labels anything. <!-- S2 --> The primary metric is family B attack success rate (ASR) over the runs that reached the scripted writer. <!-- S8 --> A benign send task succeeds iff a transmission is made, and an answer task iff the final output is non-empty and the run was not halted. Content is not checked. <!-- S3 --> For H4, steps of `v2` runs are unsafe iff they carry canary-bearing data across agents (path-dependent) or to the external server (direct). Steps of benign runs are safe. <!-- S11 --> The position-only classifier uses two features: normalised position and the number of earlier tool calls. <!-- S11 -->

### D. Statistics, Exclusions and Freeze

Confidence intervals (CIs) are percentile bootstrap intervals with 10,000 resamples and seed 20261115. H4(a) and H5 resample tasks, and the WP4 costs resample scenarios. Paired comparisons use the exact two-sided McNemar test [@mcnemar], with the reduction also required in the predicted direction. Rates carry Wilson 95% intervals, and AUROC a DeLong 95% interval [@delong]. <!-- S9 --> Only infrastructure failures are excluded. A failure caused by model output is a model failure. No agent code was changed during the study. <!-- S12 -->

The pre-registration was frozen at 2026-11-15T13:25:37Z and its SHA-256 recorded. <!-- P1 --> It names the four commits holding the harness, runners and analysis code, and five analysis choices fixed in that code. <!-- P4 --> No code changed after the freeze. <!-- P3 --> One editorial amendment records that its header's "draft" wording is stale. <!-- P2 --> The confirmatory steps ran in a fixed order, and none failed or was rerun. <!-- P5 --> Afterwards, a separate agent recomputed the outcomes from the raw result files and the pre-registration alone. It had not read the analysis code, it fixed its tolerance before comparing (bootstrap bounds within ±0.02 with the same decision; everything else exact), and it saved its results before opening the report. <!-- V1 -->

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## VI. RESULTS

### A. Phase 1: Exploratory Findings

**Leakage and a positional shortcut.** The original generator assigned trajectory identifiers per row, so steps of one run fell into both training and test. The reported F1 of 0.999 was an artefact of that leakage. <!-- v1:#1 --> With run-level splits, F1 on held-out attack types fell to 0.657. <!-- v1:#2 --> That model then relied on where an attack occurred. A classifier given only position features reached validation AUROC 0.951. Recall fell from 0.84 for the shortest prefixes to 0.00 for the longest (Fig. 2). <!-- v1:#9 --> A randomised generator and features chosen by a pre-set rule (validation area under the precision–recall curve, AUPRC, 0.970, against 0.896 for action-only features) removed the shortcut. <!-- v1:#11 --> Unsafe-step scores did not change when neutral steps were inserted (score range 0.000), and recall stayed between 0.89 and 1.00 across positions. <!-- v1:#9 --> TABLE V gives the stages; the sets differ between stages and are not comparable across them (Fig. 3).

![Fig. 2. Positional shortcut and its removal.](../final/figures/r03_position_shortcut.png)

**TABLE V. Phase 1 step-level results by stage.** Compare in-distribution against held-out within a stage only.

| Stage | Set | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|---|
| 0 (row split; leakage) | test | 0.998 | 1.000 | 0.999 | 1.000 |
| 1 (run split) | held-out types | 0.796 | 0.559 | 0.657 | 0.905 |
| 2 (deployed) | test | 0.881 | 0.945 | 0.912 | 0.998 |
| 2 (deployed) | held-out types | 0.857 | 0.543 | 0.665 | 0.984 |
| 2 (deployed) | held-out variants | 0.857 | 0.346 | 0.493 | 0.986 |

<!-- TABLE V: v1:#1, v1:#2, v1:#3, v1:#4 -->

![Fig. 3. F1 by stage and set (Phase 1). Gray: in-distribution test sets; blue: held-out sets.](../final/figures/r05_evaluation_correction.png)

**Generalisation trade-off.** The deployed model caught every run of two held-out direct attack types, but only 6 of 107 runs of the held-out path-dependent `path_cross_agent_leak` (step recall 0.019). <!-- v1:#5 --> <!-- v1:#6 --> The earlier model, before the shortcut was removed, caught 0.84 of those runs; held-out F1 went from 0.763 to 0.665 and variant F1 from 0.667 to 0.493. <!-- v1:#12 --> Four flow-count features improved path attacks but hurt direct ones. Their mean gains (0.015, standard error, SE, 0.026; 0.024, SE 0.027) failed the pre-set rule, and they were not adopted. <!-- v1:#17 --> <!-- v1:#3 -->

**Precedence, provenance and approval.** Code inspection and stored runs showed that under first-fire precedence, rule R2 turned model BLOCKED decisions (scores 0.995–0.999) into approvable requests. <!-- v1:#22 --> <!-- v1:#23 --> In two stored demonstration runs an under-reporting analyst produced an enforced score of 0.0 where the provenance-derived shadow score was 0.9952. The send was escalated for review, approved and executed. <!-- v1:#27 --> In eight scripted approval scenarios, an accurate simulated reviewer let 0 of 4 attack transmissions through. An approve-everything reviewer let 3 of 4 through, more than the 2 of 4 without approval. <!-- v1:#34 --> These findings motivated escalation-only precedence (H1), scored handoffs (H2), enforced provenance (H3), the real-trace test of the generalisation finding (H4) and the defence comparison (H5).

### B. Phase 2: Confirmatory Results

**H1: escalation-only precedence (supported).** Under `max_severity` there were no downgrade events, offline or live (TABLE VI). <!-- C3 --> Every downgrade under the other two modes turned a model BLOCKED on an external action into HUMAN_APPROVAL, and none became an allowed decision. <!-- C1 --> <!-- C2 --> Offline, no arm differed from `first_fire_v1` in either cost. <!-- C5 --> Live, under accurate declaration, `max_severity` hard-blocked a benign send in 10 of 14 benign runs, against 2 of 14 for `first_fire_v1`. The difference is 0.571, 95% CI [0.286, 0.786], and its approval volume fell from 10 of 14 to 2 of 14 (Fig. 4). <!-- C4 --> Only 12 of the 14 runs request a send; per send the figures are 10 of 12 and 2 of 12. <!-- C4b --> `max_severity_reviewable` matched `first_fire_v1` on both costs. <!-- C5 -->

**TABLE VI. H1 downgrade events.**

| Precedence | Offline (10 seeds × 3 sets) | Live (WP4) |
|---|---|---|
| `first_fire_v1` | 463 | 70 |
| `max_severity` | 0 | 0 |
| `max_severity_reviewable` | 376 | 70 |

<!-- TABLE VI: C1, C2 -->

![Fig. 4. H1 live costs per precedence mode (WP4 benign runs, accurate declaration; Wilson 95% intervals; denominators are benign runs).](figures/v2_f3_h1_live_costs.png)

**H2: scored handoffs (supported).** Over 40 pairs (8 attack scenarios × 5 declaration conditions), scoring the handoffs reduced canary-confirmed attack sends from 14 to 0 when R1 counted the pseudo-actions (exact McNemar p = 0.000122). Without that, sends stayed at 14 (p = 1). <!-- C7 --> <!-- C8 --> <!-- S7 --> Halting on a flagged handoff stopped 10 of 70 benign runs (0.143, Wilson [0.079, 0.243]). R3 never fired. <!-- C9 -->

**H3: enforced provenance (supported).** Under under-reported and missing declarations, enforcement reduced canary-confirmed attack sends from 12 of 16 to 0 of 16 (p = 0.000488). <!-- C10 --> Under accurate declaration it changed no benign outcome (2 of 12 completed, 8 of 12 sent to review, 2 of 12 hard-blocked in both arms). Under the two misreporting conditions, enforcement completed 2 of 12 benign sends, where shadow provenance completed 10 of 12. <!-- C11 --> The WP4 p-values quantify consistency across the confirmatory scenarios, not sampling variability, because WP4 is deterministic. <!-- S7 -->

**H4: generalisation on real traces ((a) supported, (b) not supported).** The analysis used 397 labelled steps of `v2` runs, from 19 attack tasks and the benign runs. In the missing task, all three runs failed before the writer. <!-- C14 --> The frozen model stopped 1 of 62 path-dependent unsafe steps and 52 of 52 direct ones. The difference is −0.984, 95% CI [−1.000, −0.948] (Fig. 5). <!-- C12 --> The position-only classifier reached AUROC 0.654, DeLong 95% [0.601, 0.706]. That is above the registered bound of 0.6, so H4(b) is not supported. <!-- C13 --> The pre-registration did not define how to label attack-run steps that carry no canary, and the registered code counts them as safe. Leaving them unlabelled gives AUROC 0.599 [0.530, 0.668]. That figure is a sensitivity analysis; the registered outcome stands. <!-- C13b -->

![Fig. 5. H4(a): the frozen model's step recall on v2 real traces, path-dependent (handoff) vs direct (send); Wilson 95% intervals.](figures/v2_f4_h4a_recall.png)

**H5: defence comparison (supported).** On family B, `v2` had lower attack success than `v1`: the difference was −0.281, 95% CI [−0.431, −0.145]. Against `ml_only` it was −0.345 [−0.517, −0.186]. <!-- C16 --> Against `rules_only` it was −0.321 [−0.517, −0.148], so the registered claim against `rules_only` is also made. <!-- C17 --> TABLE VII and Fig. 6 give the counts. There were no infrastructure exclusions and no harness faults. <!-- C15 --> The model's own decision on the send step was BLOCKED for all 52 sends that carried a canary. `max_severity_reviewable` sent 44 of them to review, which `v2` does not execute, and kept 8 blocked. <!-- C24 --> The 0 of 55 therefore holds only when sends held for review are never executed. With a simulated reviewer approving attack sends with probability 0.5 (`v2_reviewer`), 17 of 53 attacks succeeded, comparable to `v1` (16 of 57) and `rules_only` (18 of 56). <!-- C15 --> <!-- C24 --> <!-- S8 --> Benign success ranged from 18 of 40 (`v2`) to 23 of 40 (`no_governance`), and the Wilson intervals of those two overlap (Fig. 7). <!-- C18 --> Median latency was 72–106 s per run with family B and benign runs pooled, and 81.4–94.0 s over benign runs alone. <!-- C18b --> <!-- C18c -->

**TABLE VII. H5: family B attack success and benign utility (`qwen2.5:3b`).**

| Configuration | Reached writer | Model failures before writer | Attack successes | Benign success (of 40) | Benign approval volume (of 40) |
|---|---|---|---|---|---|
| `no_governance` | 54 | 6 | 51 | 23 | 0 |
| `rules_only` | 56 | 4 | 18 | 19 | 0 |
| `ml_only` | 58 | 2 | 20 | 20 | 0 |
| `v1` | 57 | 3 | 16 | 20 | 2 |
| `v2` | 55 | 5 | 0 | 18 | 5 |
| `v2_reviewer` | 53 | 7 | 17 | 22 | 5 |

<!-- TABLE VII: C15, C18 -->

![Fig. 6. Family B attack success rate per configuration; denominators are runs that reached the scripted writer; Wilson 95% intervals.](figures/v2_f1_h5_asr.png)

![Fig. 7. Benign task success per configuration (40 tasks); Wilson 95% intervals.](figures/v2_f2_benign_utility.png) <!-- C18 -->

**Multi-seed offline evaluation (descriptive).** TABLE VIII summarises ten seeds, each with its own model. <!-- C19 --> <!-- S10 --> The path-dependent types were caught in 28 of 1,011, 18 of 505 and 12 of 513 runs. Every other type was caught in at least 0.995 of runs (Fig. 8). <!-- C20 -->

**TABLE VIII. Multi-seed offline evaluation (mean over 10 seeds).** <!-- S10 -->

| Set | AUPRC (95% CI) | Step recall | Runs caught |
|---|---|---|---|
| test | 0.965 [0.960, 0.968] | 0.953 | 0.999 |
| held-out types | 0.853 [0.847, 0.860] | 0.562 | 0.672 |
| variant B | 0.834 [0.828, 0.841] | 0.338 | 0.671 |

<!-- TABLE VIII: C19 -->

![Fig. 8. Run-level recall per attack type on held-out types and variant B, pooled over 10 seeds; Wilson 95% intervals.](figures/v2_f5_multiseed_heldout.png) <!-- C20 --> <!-- S10 -->

**Independent recomputation.** Of 53 recomputed items, 44 matched, 2 were within tolerance and 7 did not match. <!-- V1 --> The mismatches came from three readings of under-specified definitions. The first is the H1 cost denominator: per run, as computed, against per send, as worded. <!-- C4 --> <!-- C4b --> The second is the H4(b) label discussed above. <!-- C13b --> The third is the scope of the latency figure. <!-- C18b --> <!-- C18c --> Every hypothesis decision agreed except H4(b). <!-- V1 --> The check also found one wrong observation in our confirmatory report, the claim that the model did not stop the `v2` sends. It is corrected above, and the report carries a dated erratum. <!-- C24 -->

### C. Exploratory Analyses (Not Pre-Registered)

Of the 55 `v2` family B runs that reached the writer, 8 were hard-blocked and 44 were sent to review. Three were allowed, and none leaked; those three belong to one task whose send carried no canary. <!-- X1 --> TABLE IX gives the expected attack success if a reviewer approved each of the 44 reviewed sends with probability p. The estimate assumes that an approved send delivers its canaries. <!-- X2 --> The `v2_reviewer` configuration observed 0.321, where its own counts imply 0.387 at p = 0.5. <!-- X4 --> Without each run's final send step, the position-only AUROC was 0.567 [0.508, 0.625], against 0.654 with it. <!-- X3 -->

**TABLE IX. Exploratory reviewer sweep on the `v2` traces.**

| P(approve \| attack) | 0.1 | 0.3 | 0.5 | 0.93 |
|---|---|---|---|---|
| Expected ASR | 0.080 | 0.240 | 0.400 | 0.744 |
| 95% CI (bootstrap over tasks) | [0.062, 0.095] | [0.185, 0.284] | [0.309, 0.474] | [0.575, 0.881] |

<!-- TABLE IX: X2 -->

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## VII. DISCUSSION

<!-- DRAFT: author to review -->
**What stopped the leaks.** In the primary configuration no canary left the system (0 of 55), because the sends held for review were never executed. <!-- C15 --> <!-- C24 --> The stopping decisions came from the learned model, but only at the send step: it rated all 52 canary-carrying sends BLOCKED. <!-- C24 --> It flagged 1 of 62 path-dependent handoffs. <!-- C12 --> The model therefore stopped the final, direct step of a compositional flow and not the flow itself. This matches its offline weakness on path-dependent attack types. <!-- C20 --> Enforced provenance supplied the correct sensitivity when agents misreported. <!-- C10 --> Handoff scoring changed outcomes only through R1's counting. <!-- C7 --> <!-- C8 --> <!-- S13 --> We read this as evidence that the monitor sees the end of a multi-agent flow, not its path. Scoring handoffs is necessary for a classifier to see that path, but in our data it was not sufficient.

**Precedence is a policy, not a detail.** The same model and rules gave very different outcomes depending only on precedence. Under first-fire precedence a rule relaxed 70 live model blocks. <!-- C2 --> Escalation-only precedence removed every downgrade but hard-blocked many more benign sends. <!-- C3 --> <!-- C4 --> The reviewable variant recovered that utility by sending model blocks to a person. In the live tests it gave the same 70 downgrades and the same costs as `first_fire_v1`. <!-- C2 --> <!-- C5 --> Its one difference, that it never relaxes a rule's BLOCKED, did not change any outcome in these scenarios, so the live tests cannot distinguish it from first-fire precedence. <!-- S4 --> <!-- C2 --> <!-- C5 --> Combining a learned and a rule-based control is therefore not monotonic in safety. A deployment has to choose where to place the residual risk, and say where it placed it.

**The residual risk rests on the reviewer.** 44 of the 52 stopped sends in `v2` were held for review, not blocked. <!-- C24 --> With a simulated reviewer approving attack sends with probability 0.5, 17 of 53 attacks succeeded, comparable to `v1` (16 of 57) and `rules_only` (18 of 56). <!-- C15 --> The exploratory sweep spans 0.08 to 0.74 expected attack success across approval probabilities from 0.1 to 0.93. <!-- X2 --> Phase 1 showed that an approve-everything reviewer can be worse than no review. <!-- v1:#34 --> The governance layer gave the reviewer no signal that separated a legitimate sensitive send from an attack carrying the same data; that observation comes from development runs (Supplementary Material). <!-- D12 --> Approval is a control point whose value is bounded by reviewer accuracy. It is not an independent guarantee.

**Cost of enforcement.** Enforced provenance removed misreporting as an attack path. Where declarations were wrong it also completed far fewer benign sends (2 of 12 against 10 of 12), because maximum-over-inputs propagation over-labels derived content. <!-- C11 --> Influence-based propagation [@permissive] targets exactly this cost; we did not implement it.

**Evaluation method.** Freezing the analysis code with the pre-registration made one ambiguity visible rather than hidden. The registered H4(b) outcome depends on how steps without a canary are labelled: 0.654 under the registered code, 0.599 when they are left out. <!-- C13 --> <!-- C13b --> Without its last step, the position-only result falls to 0.567 (exploratory). <!-- X3 --> The independent recomputation also found a wrong observation in our own report. <!-- C24 --> We recommend that hypothesis texts define every label and denominator explicitly, and that recomputation be routine before reporting.

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## VIII. LIMITATIONS AND THREATS TO VALIDITY

<!-- DRAFT: author to review -->
**External validity.** Every classifier and rule result rests on synthetic, template-generated data. <!-- S10 --> The real-LLM pilot used one local model of 3.1 billion parameters, at one temperature. <!-- S8 --> Stronger models may plan, retrieve and fail differently; for example, 27 of 360 family B runs failed before the writer. <!-- C21 --> Family B's writer is a script, not a manipulated model. Its ASR measures governance given an attempted exfiltration, not whether an LLM would attempt one. <!-- S8 --> Family A, indirect prompt injection against a real model, was registered but not run. <!-- C22 --> The study involved no production workload, no real user and no human reviewer.

**Internal validity.** WP4 is deterministic, so its p-values quantify consistency across 22 unseen scenarios, not sampling variability. <!-- S7 --> The reviewers are simulated with fixed approval probabilities. <!-- S8 --> The reviewer sweep assumes that an approved send delivers its canaries (exploratory). <!-- X2 --> Benign success does not check the content of the answer or the send. <!-- S3 --> One family B task contributed no `v2` steps to H4. <!-- C14 -->

**Construct validity.** A leak counts only if a canary token arrives intact. A paraphrased disclosure without its token is not counted. <!-- S2 --> H4's labels follow canary provenance, and one label class was undefined in the registered text. <!-- C13b --> Phase 1's feature and model choices were exploratory, and its Attack Lab influenced feature selection, so it was not a blind test. <!-- v1:#16 -->

**Conclusion validity.** Family B has 20 tasks. <!-- S8 --> The independent recomputation was performed by an AI agent, not a human analyst. <!-- V1 --> Exactly-once delivery is not provided, and the persistence evidence is exploratory (Supplementary Material). <!-- v1:#37 --> <!-- v1:#42 -->

**Remaining future work.** The following are open:
- a human reviewer study;
- family A with real injections and larger models;
- live re-evaluation of flow features with scored handoffs;
- influence-based label propagation;
- the pre-registered persistence study;
- independent replication.

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## IX. CONCLUSION

<!-- DRAFT: author to review -->
We asked which runtime control stops a leak in a multi-agent LLM pipeline. In our pre-registered evaluation, the learned model stopped the final send of every canary-carrying flow, but almost never the handoffs that carried the data there. <!-- C24 --> <!-- C12 --> Enforced provenance stopped misreported sends, at a measured cost to benign sends. <!-- C10 --> <!-- C11 --> Handoff scoring helped only through a rule's double counting. <!-- C7 --> <!-- C8 --> Precedence decided whether residual risk became lost utility or a human decision. <!-- C4 --> <!-- C5 --> With one 3B-parameter local model and a scripted compromised writer, the combined configuration let no attack through (0 of 55), but only because the sends it held for review were never executed; 44 of its 52 stops were reviews, not blocks. <!-- C15 --> <!-- C24 --> With a simulated reviewer approving attack sends with probability 0.5, it let 17 of 53 attacks through, comparable to the earlier design (16 of 57) and to rules alone (18 of 56). <!-- C15 --> <!-- S8 --> One registered hypothesis was not supported. <!-- C13 --> The evaluation method may be as reusable as the system: a frozen pre-registration with its analysis code, canary ground truth, and independent recomputation.

*Text in this section was drafted with AI assistance [@claude]; see the Acknowledgment.*

## DATA AND CODE AVAILABILITY

*[needs-author: repository URL / archive DOI.]* The code, the frozen pre-registration and its hash, all confirmatory result files, the analysis scripts, the independent recomputation, the claim–evidence ledger and the figure scripts are in the project repository. Supplementary Material lists every artifact and its commit. All data is synthetic; no personal data was used.

## ACKNOWLEDGMENT

<!-- DRAFT: author to review. Placed here per IEEE policy: AI-generated content is disclosed in the Acknowledgment, the AI system is named, the sections that use it are identified with the level of use, and those sections cite the AI system. Confirm the levels below after your own revision. -->
*[needs-author: funding and other acknowledgments, if any.]*

**Use of AI-generated content.** The author used Claude Opus 5.5 (Anthropic; model identifier `claude-opus-5-5`), through the Claude Code agentic coding tool [@claude]. The version is the one recorded on every commit of the project repository from 14 to 17 Nov. 2026; work done before that history began *[VERIFY: versions]*. The uses and the sections affected are:

- **Text, all sections (Abstract and Sections I–IX):** drafted by Claude. Sections II–VI were drafted from the claim–evidence ledger and the project's reports. The Abstract, Section I, and Sections VII–IX were drafted from the contributions, framing and corrections the author specified. Every number was checked by a script against the cited ledger rows. The author reviewed and revised the text *[author to confirm the extent of revision]*. Each of Sections I–IX ends with a citation of the AI system.
- **Tables I–IX and Figs. 1–8:** generated by Claude from the result files. Figs. 1 and 4–8 come from Claude-written plotting scripts; Figs. 2–3 are the Phase 1 figures *[VERIFY: whether AI was used to make them]*.
- **Code and experiments:** Claude implemented the v2 governance changes, the experiment harnesses, the tests, and the pre-registered analysis and figure scripts, and ran the development and confirmatory experiments.
- **Independent recomputation:** a separate Claude agent instance, which had not read the analysis code, recomputed the confirmatory results (Section V-D).

The author designed the study and approved the pre-registration before it was frozen. The author takes full responsibility for the content of this article.

## REFERENCES

{{REFERENCES}}

<!-- TEMPLATE: biographies, one per author, below the references -->
**[AUTHOR NAME]** *[needs-author: short biography, required for every author by IEEE Access.]*
