# Decision-precedence ablation (CONFIRMATORY)

Frozen v1 model and thresholds {'autonomous_max': 0.22, 'restricted_max': 0.5, 'approval_max': 0.85}; seeds [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]; offline convention (each step scored against its full generated prefix). Means over seeds; downgrade counts are totals. Seed 42 train is the model's own training data.

| Set | Config | Step recall | Run recall | Step FPR | Benign false alarm | Approval volume | Benign ext. send hard-blocked | Benign block rate | Unsafe steps to approval | Downgrades (all / ML BLOCKED / unsafe / to allowed) |
|---|---|---|---|---|---|---|---|---|---|---|
| test | ml_only | 0.946 | 0.999 | 0.007 | 0.033 | 0.014 | 0.000 | 0.019 | 0.242 | 0 / 0 / 0 / 0 |
| test | rules_only | 0.339 | 0.678 | 0.013 | 0.175 | 0.000 | 0.175 | 0.175 | 0.044 | 4547 / 2219 / 3551 / 4325 |
| test | first_fire_v1 | 0.946 | 0.999 | 0.020 | 0.197 | 0.014 | 0.175 | 0.190 | 0.286 | 222 / 222 / 222 / 0 |
| test | max_severity | 0.946 | 0.999 | 0.020 | 0.197 | 0.014 | 0.175 | 0.190 | 0.242 | 0 / 0 / 0 / 0 |
| test | max_severity_reviewable | 0.946 | 0.999 | 0.020 | 0.197 | 0.014 | 0.175 | 0.190 | 0.277 | 181 / 181 / 181 / 0 |
| holdout_types | ml_only | 0.569 | 0.689 | 0.011 | 0.028 | 0.014 | 0.000 | 0.014 | 0.236 | 0 / 0 / 0 / 0 |
| holdout_types | rules_only | 0.284 | 0.663 | 0.013 | 0.120 | 0.000 | 0.120 | 0.120 | 0.000 | 3812 / 867 / 2588 / 3812 |
| holdout_types | first_fire_v1 | 0.569 | 0.689 | 0.024 | 0.141 | 0.014 | 0.120 | 0.132 | 0.236 | 0 / 0 / 0 / 0 |
| holdout_types | max_severity | 0.569 | 0.689 | 0.024 | 0.141 | 0.014 | 0.120 | 0.132 | 0.236 | 0 / 0 / 0 / 0 |
| holdout_types | max_severity_reviewable | 0.569 | 0.689 | 0.024 | 0.141 | 0.014 | 0.120 | 0.132 | 0.236 | 0 / 0 / 0 / 0 |
| holdout_variants | ml_only | 0.350 | 0.698 | 0.003 | 0.031 | 0.016 | 0.000 | 0.016 | 0.016 | 0 / 0 / 0 / 0 |
| holdout_variants | rules_only | 0.331 | 0.661 | 0.013 | 0.174 | 0.000 | 0.174 | 0.174 | 0.040 | 1340 / 369 / 851 / 1099 |
| holdout_variants | first_fire_v1 | 0.350 | 0.698 | 0.016 | 0.197 | 0.016 | 0.174 | 0.186 | 0.057 | 241 / 241 / 241 / 0 |
| holdout_variants | max_severity | 0.350 | 0.698 | 0.016 | 0.197 | 0.016 | 0.174 | 0.186 | 0.016 | 0 / 0 / 0 / 0 |
| holdout_variants | max_severity_reviewable | 0.350 | 0.698 | 0.016 | 0.197 | 0.016 | 0.174 | 0.186 | 0.049 | 195 / 195 / 195 / 0 |

## max_severity minus first_fire_v1, benign runs (pooled over seeds; 95% bootstrap CI)

| Set | Approval volume | Ext. send hard-blocked | Block rate | Any stop |
|---|---|---|---|---|
| test | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| holdout_types | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| holdout_variants | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |

## max_severity_reviewable minus first_fire_v1, benign runs (pooled over seeds; 95% bootstrap CI)

| Set | Approval volume | Ext. send hard-blocked | Block rate | Any stop |
|---|---|---|---|---|
| test | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| holdout_types | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
| holdout_variants | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] |
