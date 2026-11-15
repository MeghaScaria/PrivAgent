# WP4 runner: confirmatory half (CONFIRMATORY)

22 scenarios × 5 declaration conditions × 8 conditions = 880 runs, 49.1 s. Split file SHA-256 `a8828ab34c508ec3adffb6bae0d17bbd205e803ce642dddddbc21512074baed8`. Raw counts only; the pre-registered tests are computed by `experiments/v2/analysis/h1.py`–`h3.py`.

| Condition | Attack sends executed | Benign sends completed / review / hard-blocked | Benign runs halted at a handoff |
|---|---|---|---|
| primary|first_fire_v1 | 0/40 | 7 / 43 / 10 of 60 | 0/70 |
| primary|max_severity | 0/40 | 7 / 3 / 50 of 60 | 0/70 |
| primary|max_severity_reviewable | 0/40 | 7 / 43 / 10 of 60 | 0/70 |
| h2_shadow | 14/40 | 27 / 23 / 10 of 60 | 0/70 |
| h2_score_r1on | 0/40 | 7 / 3 / 50 of 60 | 0/70 |
| h2_score_r1off | 14/40 | 27 / 23 / 10 of 60 | 0/70 |
| h2_score_r1off_enforce | 14/40 | 27 / 23 / 10 of 60 | 10/70 |
| v1 | 14/40 | 27 / 23 / 10 of 60 | 0/70 |
