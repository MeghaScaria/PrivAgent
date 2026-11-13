# Decision-precedence ablation (DEVELOPMENT)

**Development run: train/val splits and variant C only.** No test, held-out-type or variant-B data was scored. Not a confirmatory result.

Frozen v1 model and thresholds {'autonomous_max': 0.22, 'restricted_max': 0.5, 'approval_max': 0.85}; seeds [42, 7, 1234]; offline convention (each step scored against its full generated prefix). Means over seeds; downgrade counts are totals. Seed 42 train is the model's own training data.

| Set | Config | Step recall | Run recall | Step FPR | Benign false alarm | Approval volume | Benign block rate | Unsafe steps to approval | Downgrades (all / ML BLOCKED / unsafe) |
|---|---|---|---|---|---|---|---|---|---|
| train | ml_only | 0.951 | 1.000 | 0.006 | 0.032 | 0.015 | 0.018 | 0.242 | 0 / 0 / 0 |
| train | rules_only | 0.337 | 0.665 | 0.012 | 0.160 | 0.000 | 0.160 | 0.050 | 3758 / 1851 / 2931 |
| train | first_fire_v1 | 0.951 | 1.000 | 0.019 | 0.183 | 0.015 | 0.173 | 0.292 | 206 / 206 / 206 |
| train | max_severity | 0.951 | 1.000 | 0.019 | 0.183 | 0.015 | 0.173 | 0.242 | 0 / 0 / 0 |
| val | ml_only | 0.943 | 1.000 | 0.007 | 0.025 | 0.011 | 0.015 | 0.227 | 0 / 0 / 0 |
| val | rules_only | 0.336 | 0.667 | 0.014 | 0.176 | 0.000 | 0.176 | 0.036 | 1320 / 652 / 1030 |
| val | first_fire_v1 | 0.943 | 1.000 | 0.021 | 0.190 | 0.011 | 0.185 | 0.263 | 53 / 53 / 53 |
| val | max_severity | 0.943 | 1.000 | 0.021 | 0.190 | 0.011 | 0.185 | 0.227 | 0 / 0 / 0 |
| variant_c | ml_only | 0.339 | 0.680 | 0.003 | 0.032 | 0.010 | 0.022 | 0.002 | 0 / 0 / 0 |
| variant_c | rules_only | 0.337 | 0.676 | 0.014 | 0.176 | 0.000 | 0.176 | 0.044 | 203 / 125 / 111 |
| variant_c | first_fire_v1 | 0.339 | 0.680 | 0.017 | 0.200 | 0.010 | 0.196 | 0.046 | 80 / 80 / 80 |
| variant_c | max_severity | 0.339 | 0.680 | 0.017 | 0.200 | 0.010 | 0.196 | 0.002 | 0 / 0 / 0 |

## max_severity minus first_fire_v1, benign runs (pooled over seeds; 95% bootstrap CI)

| Set | Approval volume | Block rate | Any stop |
|---|---|---|---|
| train | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| val | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| variant_c | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
