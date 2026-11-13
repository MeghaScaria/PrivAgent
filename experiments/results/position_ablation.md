# Position-shortcut ablation

Selected feature set (validation AUPRC only): **trajectory_invariant**

Metrics at each model's own validation-tuned stop threshold (t2). All models are evaluated on the randomized test split and held-out sets.

| model | val AUPRC | t2 | test F1 | test P | test R | test FPR | test AUROC | types F1 | types R | types FPR | types AUROC | variants F1 | variants R | variants AUROC | benign-run alarm | sweep caught |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy/all_current | 0.999 | 0.400 | 0.626 | 0.983 | 0.460 | 0.000 | 0.985 | 0.501 | 0.335 | 0.000 | 0.966 | 0.550 | 0.381 | 0.977 | 0.003 | 0.414 |
| legacy/no_timestamp | 1.000 | 0.400 | 0.606 | 0.974 | 0.440 | 0.001 | 0.990 | 0.470 | 0.318 | 0.004 | 0.975 | 0.530 | 0.364 | 0.984 | 0.003 | 0.394 |
| legacy/action_only | 0.942 | 0.400 | 0.826 | 0.703 | 1.000 | 0.026 | 0.994 | 0.605 | 0.540 | 0.026 | 0.971 | 0.451 | 0.331 | 0.969 | 0.153 | 0.889 |
| legacy/trajectory_no_position | 1.000 | 0.400 | 0.618 | 0.970 | 0.454 | 0.001 | 0.987 | 0.507 | 0.354 | 0.004 | 0.972 | 0.529 | 0.364 | 0.983 | 0.006 | 0.293 |
| legacy/trajectory_no_context | 1.000 | 0.400 | 0.598 | 0.969 | 0.432 | 0.001 | 0.991 | 0.493 | 0.335 | 0.003 | 0.980 | 0.477 | 0.315 | 0.989 | 0.003 | 0.364 |
| legacy/action_core | 0.931 | 0.400 | 0.826 | 0.703 | 1.000 | 0.026 | 0.994 | 0.605 | 0.540 | 0.026 | 0.971 | 0.451 | 0.331 | 0.972 | 0.153 | 0.889 |
| legacy/trajectory_invariant | 0.998 | 0.400 | 0.873 | 0.838 | 0.911 | 0.011 | 0.996 | 0.804 | 0.755 | 0.013 | 0.984 | 0.706 | 0.666 | 0.987 | 0.078 | 1.000 |
| legacy/position_only | 0.626 | 0.580 | 0.157 | 0.462 | 0.095 | 0.007 | 0.818 | 0.059 | 0.032 | 0.003 | 0.720 | 0.125 | 0.071 | 0.817 | 0.081 | 0.030 |
| randomized/all_current | 0.982 | 0.500 | 0.930 | 0.924 | 0.937 | 0.005 | 0.999 | 0.778 | 0.705 | 0.011 | 0.991 | 0.706 | 0.602 | 0.992 | 0.043 | 0.939 |
| randomized/no_timestamp | 0.968 | 0.400 | 0.915 | 0.886 | 0.947 | 0.008 | 0.998 | 0.780 | 0.709 | 0.012 | 0.988 | 0.708 | 0.632 | 0.989 | 0.055 | 0.990 |
| randomized/action_only | 0.912 | 0.400 | 0.829 | 0.716 | 0.984 | 0.024 | 0.994 | 0.597 | 0.524 | 0.025 | 0.972 | 0.452 | 0.331 | 0.973 | 0.153 | 0.889 |
| randomized/trajectory_no_position | 0.971 | 0.400 | 0.913 | 0.879 | 0.949 | 0.008 | 0.998 | 0.763 | 0.679 | 0.011 | 0.986 | 0.667 | 0.569 | 0.989 | 0.055 | 0.980 |
| randomized/trajectory_no_context | 0.971 | 0.400 | 0.917 | 0.885 | 0.953 | 0.008 | 0.999 | 0.701 | 0.596 | 0.011 | 0.985 | 0.652 | 0.542 | 0.989 | 0.058 | 0.970 |
| randomized/action_core | 0.896 | 0.400 | 0.826 | 0.703 | 1.000 | 0.026 | 0.994 | 0.605 | 0.540 | 0.026 | 0.975 | 0.451 | 0.331 | 0.977 | 0.153 | 0.889 |
| randomized/trajectory_invariant | 0.970 | 0.500 | 0.912 | 0.881 | 0.945 | 0.008 | 0.998 | 0.665 | 0.543 | 0.010 | 0.984 | 0.493 | 0.346 | 0.986 | 0.049 | 0.889 |
| randomized/position_only | 0.244 | 0.400 | 0.178 | 0.355 | 0.118 | 0.013 | 0.856 | 0.170 | 0.103 | 0.012 | 0.738 | 0.172 | 0.105 | 0.852 | 0.197 | 0.081 |
| saved current model | - | 0.400 | 0.503 | 0.988 | 0.337 | 0.000 | 0.984 | 0.495 | 0.331 | 0.001 | 0.978 | 0.428 | 0.273 | 0.976 | 0.000 | 0.162 |

## Per attack type: step recall / runs caught

| attack type (set) | saved current model | legacy/all_current | randomized/all_current | randomized/trajectory_no_position | randomized/action_core | randomized/trajectory_invariant |
|---|---|---|---|---|---|---|
| inter_agent_injection (test) | 0.50 / 0.59 | 0.69 / 1.00 | 0.99 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| path_exfiltration (test) | 0.37 / 0.39 | 0.35 / 0.37 | 0.98 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 0.99 / 1.00 |
| path_privilege_escalation (test) | 0.34 / 0.34 | 0.39 / 0.41 | 0.90 / 1.00 | 0.95 / 1.00 | 1.00 / 1.00 | 0.98 / 1.00 |
| permission_laundering (test) | 0.22 / 0.23 | 0.32 / 0.55 | 0.95 / 1.00 | 0.98 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| prompt_injection (test) | 0.60 / 0.60 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| tool_poisoning (test) | 0.23 / 0.43 | 0.39 / 0.51 | 0.85 / 1.00 | 0.80 / 1.00 | 1.00 / 1.00 | 0.74 / 1.00 |
| inter_agent_injection (holdout_variants) | 0.42 / 0.54 | 0.63 / 0.96 | 0.50 / 1.00 | 0.50 / 1.00 | 0.50 / 1.00 | 0.50 / 1.00 |
| path_exfiltration (holdout_variants) | 0.24 / 0.25 | 0.23 / 0.23 | 0.68 / 0.85 | 0.71 / 0.96 | 0.00 / 0.00 | 0.02 / 0.04 |
| path_privilege_escalation (holdout_variants) | 0.32 / 0.33 | 0.32 / 0.33 | 0.45 / 0.89 | 0.38 / 0.74 | 0.00 / 0.00 | 0.05 / 0.11 |
| permission_laundering (holdout_variants) | 0.14 / 0.22 | 0.20 / 0.39 | 0.54 / 1.00 | 0.45 / 1.00 | 0.33 / 1.00 | 0.34 / 1.00 |
| prompt_injection (holdout_variants) | 0.54 / 0.54 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| tool_poisoning (holdout_variants) | 0.10 / 0.21 | 0.22 / 0.30 | 0.67 / 1.00 | 0.66 / 1.00 | 0.50 / 1.00 | 0.50 / 1.00 |
| cascading_failure (holdout_types) | 0.34 / 0.55 | 0.38 / 0.71 | 0.89 / 1.00 | 0.94 / 1.00 | 1.00 / 1.00 | 0.99 / 1.00 |
| data_exfiltration (holdout_types) | 0.51 / 0.51 | 0.47 / 0.47 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| path_cross_agent_leak (holdout_types) | 0.26 / 0.44 | 0.26 / 0.43 | 0.45 / 0.94 | 0.36 / 0.84 | 0.00 / 0.00 | 0.02 / 0.06 |
