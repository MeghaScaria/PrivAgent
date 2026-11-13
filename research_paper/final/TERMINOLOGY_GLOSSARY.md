# Terminology glossary: PrivAgent Research Paper (final)

Definitions follow how the manuscript and the code use each term. Where a term has a precise code-level meaning, the source is given.

| Term | Definition in this paper | Source / note |
|---|---|---|
| **Trajectory** | The ordered sequence of actions in one run, as seen by the classifier. Offline, it is a synthetic generated sequence. Live, it contains only *executed (allowed) tool actions*. Handoff events are not part of it | `TrajectoryMonitor.trajectory`; `data/generate_trajectories.py` |
| **Run** | One task execution (live) or one generated trajectory (offline), identified by a single trajectory or run ID. The run is the independent unit for splitting and for Wilson intervals | `train_models.py` split by run; Table 4 |
| **Step** | One action within a run. Steps of a run share a prefix and are not independent | §6 metric levels |
| **Attack scenario** | One concrete scripted test case: an Attack Lab scenario (e.g. `prompt_injection`) or an E5 scenario (e.g. `hr_exfil_misreported`). A scenario is an instance, not a class | `governance/attack_scenarios.py`; `experiments/approval_evaluation.py` |
| **Attack type** | A generator template (nine in total), such as `path_cross_agent_leak`. Many runs are generated per type | `data/generate_trajectories.py` |
| **Held-out attack type** | One of the three types never used in training or threshold tuning (`data_exfiltration`, `cascading_failure`, `path_cross_agent_leak`), scored only on the held-out-types set | §5; Table 4 |
| **Held-out variant (B)** | Training-type templates with swapped tools, held out from training. Variant C is used for development only | §5 |
| **Step-level detection** | A step is *detected* when its score r ≥ 0.50 (the stop threshold, RESTRICTED upper bound). Step-level precision, recall, F1, AUROC and FPR are computed over steps | `evaluate_set`; §6 |
| **Run-level detection** | A run is *caught* when at least one of its unsafe steps is detected. A benign run is a *false alarm* when any of its steps is stopped. "6/107" is a run-level figure | `evaluate_set` (`runs_caught`); §7.1.2 |
| **Detects / catches** | In prose, "catches N runs" is run level; "recall" without qualification is step level. Attack Lab "caught" means at least one step of the scenario was not executed (final decision HUMAN_APPROVAL or BLOCKED); "stopped by ML / policy / both" records which layer's decision was non-executable | `experiments/attack_lab_replay.py` (`caught_by`, `outcome`); §7.1.3 |
| **Cross-agent handoff** | A transfer of state between pipeline agents (orchestrator → retriever → analyst → writer), recorded by `HandoffTracker`. It is distinct from a `cross_agent` *destination category*, which appears only in offline synthetic trajectories | `agents/handoffs.py`; §4.9 |
| **Provenance** | The record of where an item came from (a ref per tool-returned item, inherited by derived objects with maximum sensitivity). It is used to *identify* origin and to *detect* declared-vs-derived mismatches. It does not by itself *prevent* transmission | `governance/provenance.py`; §4.8 table |
| **Shadow mode** | Computed and logged but not used for the enforced decision. Provenance-authoritative sensitivity and handoff instrumentation run in shadow mode by default | `sensitivity_mode="shadow"` |
| **Enforcement** | Using a decision to allow or stop an action. Enforced: the ML decision, the policy decision, and in the approval graph the reviewer's decision. Not enforced: provenance (`enforce` mode exists, tested only) | §4.3, §4.8 |
| **ML decision** | The autonomy level obtained by mapping the classifier score r through thresholds 0.22 / 0.50 / 0.85. Not logged as a separate field; recomputable from the logged score | `AutonomyController`; §4.10 |
| **Policy decision** | The decision of the first firing rule (R1, R2, R3), if any. When a rule fires it *replaces* the ML decision | `policy_engine.py`; `_decide` |
| **Final decision** | The decision that is enforced and logged, with source `ml_model` or `policy_engine` | audit log |
| **Human approval** | (1) HUMAN_APPROVAL, an autonomy level, not executed in the default graph; (2) the opt-in approval workflow, in which a HUMAN_APPROVAL action is paused (`interrupt()`) and executed only if a reviewer approves. Reviewers in this paper are simulated | §4.11, §7.3 |
| **Generalisation** | Performance on data unlike the training data: held-out attack types and held-out tool-swapped variants. In-distribution test performance is not evidence of generalisation | §7.1 |
| **Stage 0 / 1 / 2** | Evaluation stages: 0, original row-level split (historical); 1, run-level split on the legacy generator; 2, deployed model on the randomized generator with position-invariant features. Sets differ between stages, so values are not comparable across stages | Table 5 |
| **Real MCP tool servers under scripted workloads** | The four local FastMCP stdio servers with synthetic data, called through governed wrappers, driven by a scripted LLM or a hand-specified action sequence. Not a real-world deployment | §6 |

**Spelling convention.** The manuscript uses British spelling (generalisation, organisation, behaviour). "Randomized" is kept where it names the generator, as in the code and result files.
