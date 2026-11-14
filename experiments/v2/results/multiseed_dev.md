# Multi-seed offline evaluation (DEVELOPMENT, validation split only)

Seeds [42, 1, 2, 3, 4, 5, 6, 7, 8, 9] (data = split = model seed). Thresholds tuned on each seed's val split and metrics computed on the same split, so threshold-dependent metrics are optimistic; AUPRC is threshold-free. No test, held-out-type or variant-B data was scored.

Seed-42 reference check: thresholds reproduce `models/thresholds.json`: **True**; max |frozen − retrained| val score: 0.00e+00.

| Metric | Mean over seeds | 95% CI (run bootstrap, 1000×) | Seed min–max |
|---|---|---|---|
| f1 | 0.924 | [0.919, 0.929] | 0.911–0.937 |
| auprc | 0.968 | [0.965, 0.971] | 0.959–0.977 |
| step_recall | 0.957 | [0.952, 0.963] | 0.943–0.964 |
| runs_caught | 0.999 | [0.998, 1.000] | 0.992–1.000 |
| benign_run_false_alarm | 0.031 | [0.026, 0.037] | 0.019–0.045 |

## Run-level catch per attack type (val, pooled over seeds; Wilson 95%)

| Attack type | Runs caught / runs | Rate | Wilson 95% |
|---|---|---|---|
| inter_agent_injection | 394/394 | 1.000 | [0.990, 1.000] |
| path_exfiltration | 424/424 | 1.000 | [0.991, 1.000] |
| path_privilege_escalation | 399/401 | 0.995 | [0.982, 0.999] |
| permission_laundering | 395/395 | 1.000 | [0.990, 1.000] |
| prompt_injection | 383/383 | 1.000 | [0.990, 1.000] |
| tool_poisoning | 405/405 | 1.000 | [0.991, 1.000] |

Held-out attack types (including `path_cross_agent_leak`) do not appear in train/val; whether 6/107 is typical needs the confirmatory held-out sets after freezing.
