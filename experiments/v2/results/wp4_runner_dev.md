# WP4 runner: dev half (DEVELOPMENT)

24 scenarios × 5 declaration conditions × 8 conditions = 960 runs, 336.7 s. Split file SHA-256 `a8828ab34c508ec3adffb6bae0d17bbd205e803ce642dddddbc21512074baed8`. Raw counts only; the pre-registered tests are computed by `experiments/v2/analysis/h1.py`–`h3.py`.

| Condition | Attack sends executed | Benign sends completed / review / hard-blocked | Benign runs halted at a handoff |
|---|---|---|---|
| primary|first_fire_v1 | 0/40 | 10 / 45 / 10 of 65 | 0/80 |
| primary|max_severity | 0/40 | 10 / 5 / 50 of 65 | 0/80 |
| primary|max_severity_reviewable | 0/40 | 10 / 45 / 10 of 65 | 0/80 |
| h2_shadow | 15/40 | 30 / 25 / 10 of 65 | 0/80 |
| h2_score_r1on | 0/40 | 10 / 5 / 50 of 65 | 0/80 |
| h2_score_r1off | 15/40 | 30 / 25 / 10 of 65 | 0/80 |
| h2_score_r1off_enforce | 15/40 | 30 / 25 / 10 of 65 | 15/80 |
| v1 | 15/40 | 30 / 25 / 10 of 65 | 0/80 |
