# Position-shortcut ablation

Selected feature set (validation AUPRC only): **trajectory_no_position**

Metrics at each model's own validation-tuned stop threshold (t2). All models are evaluated on the randomized test split and held-out sets.

| model | val AUPRC | t2 | test F1 | test P | test R | test FPR | test AUROC | types F1 | types R | types FPR | types AUROC | variants F1 | variants R | variants AUROC | benign-run alarm | sweep caught |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy/all_current | 0.999 | 0.400 | 0.350 | 0.973 | 0.214 | 0.000 | 0.983 | 0.253 | 0.148 | 0.002 | 0.965 | 0.394 | 0.245 | 0.964 | 0.003 | 0.414 |
| legacy/no_timestamp | 1.000 | 0.400 | 0.353 | 0.941 | 0.217 | 0.001 | 0.988 | 0.338 | 0.216 | 0.005 | 0.978 | 0.351 | 0.215 | 0.984 | 0.006 | 0.394 |
| legacy/action_only | 0.942 | 0.400 | 0.816 | 0.689 | 1.000 | 0.022 | 0.995 | 0.644 | 0.605 | 0.022 | 0.977 | 0.467 | 0.345 | 0.975 | 0.176 | 0.889 |
| legacy/trajectory_no_position | 1.000 | 0.400 | 0.371 | 0.944 | 0.231 | 0.001 | 0.985 | 0.382 | 0.253 | 0.006 | 0.977 | 0.346 | 0.212 | 0.981 | 0.006 | 0.293 |
| legacy/position_only | 0.626 | 0.580 | 0.000 | 0.000 | 0.000 | 0.000 | 0.765 | 0.003 | 0.001 | 0.000 | 0.679 | 0.000 | 0.000 | 0.766 | 0.000 | 0.030 |
| randomized/all_current | 0.968 | 0.400 | 0.915 | 0.884 | 0.948 | 0.006 | 0.999 | 0.753 | 0.695 | 0.012 | 0.990 | 0.700 | 0.602 | 0.992 | 0.052 | 0.960 |
| randomized/no_timestamp | 0.950 | 0.480 | 0.872 | 0.848 | 0.897 | 0.008 | 0.998 | 0.744 | 0.641 | 0.007 | 0.989 | 0.601 | 0.467 | 0.990 | 0.064 | 0.869 |
| randomized/action_only | 0.896 | 0.400 | 0.818 | 0.700 | 0.984 | 0.021 | 0.995 | 0.645 | 0.598 | 0.021 | 0.980 | 0.468 | 0.345 | 0.979 | 0.176 | 0.889 |
| randomized/trajectory_no_position | 0.948 | 0.440 | 0.865 | 0.834 | 0.899 | 0.009 | 0.997 | 0.767 | 0.675 | 0.007 | 0.990 | 0.616 | 0.491 | 0.990 | 0.066 | 0.899 |
| randomized/position_only | 0.137 | 0.400 | 0.004 | 0.200 | 0.002 | 0.000 | 0.814 | 0.025 | 0.013 | 0.003 | 0.746 | 0.003 | 0.002 | 0.825 | 0.009 | 0.152 |
| saved current model | - | 0.400 | 0.164 | 0.979 | 0.089 | 0.000 | 0.980 | 0.269 | 0.158 | 0.002 | 0.980 | 0.153 | 0.083 | 0.973 | 0.003 | 0.162 |

## Per attack type: step recall / runs caught

| attack type (set) | saved current model | legacy/all_current | randomized/all_current | randomized/no_timestamp | randomized/action_only | randomized/trajectory_no_position |
|---|---|---|---|---|---|---|
| inter_agent_injection (test) | 0.16 / 0.31 | 0.51 / 0.98 | 1.00 / 1.00 | 0.99 / 1.00 | 1.00 / 1.00 | 0.99 / 1.00 |
| path_exfiltration (test) | 0.05 / 0.11 | 0.05 / 0.09 | 0.95 / 1.00 | 0.88 / 0.98 | 0.94 / 1.00 | 0.89 / 1.00 |
| path_privilege_escalation (test) | 0.00 / 0.00 | 0.00 / 0.00 | 0.96 / 1.00 | 0.85 / 1.00 | 1.00 / 1.00 | 0.87 / 1.00 |
| permission_laundering (test) | 0.02 / 0.05 | 0.13 / 0.40 | 0.94 / 1.00 | 0.98 / 1.00 | 1.00 / 1.00 | 0.96 / 1.00 |
| prompt_injection (test) | 0.52 / 0.52 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| tool_poisoning (test) | 0.07 / 0.14 | 0.06 / 0.11 | 0.83 / 1.00 | 0.65 / 1.00 | 0.99 / 1.00 | 0.67 / 1.00 |
| inter_agent_injection (holdout_variants) | 0.14 / 0.28 | 0.49 / 0.98 | 0.50 / 1.00 | 0.50 / 1.00 | 0.50 / 1.00 | 0.50 / 1.00 |
| path_exfiltration (holdout_variants) | 0.00 / 0.00 | 0.00 / 0.00 | 0.64 / 0.93 | 0.37 / 0.64 | 0.00 / 0.00 | 0.51 / 0.76 |
| path_privilege_escalation (holdout_variants) | 0.00 / 0.00 | 0.00 / 0.00 | 0.45 / 0.91 | 0.33 / 0.67 | 0.00 / 0.00 | 0.33 / 0.67 |
| permission_laundering (holdout_variants) | 0.01 / 0.02 | 0.14 / 0.43 | 0.45 / 1.00 | 0.34 / 1.00 | 0.33 / 1.00 | 0.35 / 1.00 |
| prompt_injection (holdout_variants) | 0.42 / 0.42 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| tool_poisoning (holdout_variants) | 0.10 / 0.16 | 0.17 / 0.33 | 0.84 / 1.00 | 0.54 / 1.00 | 0.50 / 1.00 | 0.55 / 1.00 |
| cascading_failure (holdout_types) | 0.10 / 0.19 | 0.12 / 0.33 | 0.89 / 1.00 | 0.89 / 1.00 | 0.98 / 1.00 | 0.93 / 1.00 |
| data_exfiltration (holdout_types) | 0.37 / 0.37 | 0.35 / 0.35 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| path_cross_agent_leak (holdout_types) | 0.13 / 0.27 | 0.09 / 0.21 | 0.35 / 0.85 | 0.21 / 0.58 | 0.00 / 0.00 | 0.25 / 0.61 |
