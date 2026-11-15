# Multi-seed offline evaluation (CONFIRMATORY)

Seeds [42, 1, 2, 3, 4, 5, 6, 7, 8, 9] (data = split = model seed). Each seed's model is trained on its train split, its thresholds are tuned on its val split, and it is scored on the sets below. 95% CI: run bootstrap within seed (1000×), averaged over seeds. Descriptive (WP5); no hypothesis test.

## test

| Metric | Mean over seeds | 95% CI | Seed min–max |
|---|---|---|---|
| f1 | 0.916 | [0.910, 0.921] | 0.904–0.927 |
| auprc | 0.965 | [0.960, 0.968] | 0.955–0.972 |
| step_recall | 0.953 | [0.947, 0.959] | 0.937–0.971 |
| runs_caught | 0.999 | [0.998, 1.000] | 0.996–1.000 |
| benign_run_false_alarm | 0.036 | [0.030, 0.043] | 0.017–0.053 |

| Attack type | Runs caught / runs | Rate | Wilson 95% |
|---|---|---|---|
| inter_agent_injection | 375/375 | 1.000 | [0.990, 1.000] |
| path_exfiltration | 403/403 | 1.000 | [0.991, 1.000] |
| path_privilege_escalation | 409/411 | 0.995 | [0.982, 0.999] |
| permission_laundering | 377/377 | 1.000 | [0.990, 1.000] |
| prompt_injection | 412/412 | 1.000 | [0.991, 1.000] |
| tool_poisoning | 403/403 | 1.000 | [0.991, 1.000] |

## holdout_types

| Metric | Mean over seeds | 95% CI | Seed min–max |
|---|---|---|---|
| f1 | 0.673 | [0.658, 0.687] | 0.654–0.711 |
| auprc | 0.853 | [0.847, 0.860] | 0.842–0.865 |
| step_recall | 0.562 | [0.544, 0.581] | 0.538–0.613 |
| runs_caught | 0.672 | [0.656, 0.689] | 0.640–0.733 |
| benign_run_false_alarm | 0.030 | [0.024, 0.036] | 0.010–0.043 |

| Attack type | Runs caught / runs | Rate | Wilson 95% |
|---|---|---|---|
| cascading_failure | 987/987 | 1.000 | [0.996, 1.000] |
| data_exfiltration | 1002/1002 | 1.000 | [0.996, 1.000] |
| path_cross_agent_leak | 28/1011 | 0.028 | [0.019, 0.040] |

## holdout_variants

| Metric | Mean over seeds | 95% CI | Seed min–max |
|---|---|---|---|
| f1 | 0.492 | [0.482, 0.502] | 0.463–0.522 |
| auprc | 0.834 | [0.828, 0.841] | 0.815–0.865 |
| step_recall | 0.338 | [0.330, 0.348] | 0.313–0.366 |
| runs_caught | 0.671 | [0.654, 0.687] | 0.643–0.720 |
| benign_run_false_alarm | 0.033 | [0.027, 0.040] | 0.017–0.053 |

| Attack type | Runs caught / runs | Rate | Wilson 95% |
|---|---|---|---|
| inter_agent_injection | 493/493 | 1.000 | [0.992, 1.000] |
| path_exfiltration | 18/505 | 0.036 | [0.023, 0.056] |
| path_privilege_escalation | 12/513 | 0.023 | [0.013, 0.040] |
| permission_laundering | 489/489 | 1.000 | [0.992, 1.000] |
| prompt_injection | 499/499 | 1.000 | [0.992, 1.000] |
| tool_poisoning | 501/501 | 1.000 | [0.992, 1.000] |

