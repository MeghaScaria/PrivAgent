# RESTRICTED semantics on benign validation runs (DEVELOPMENT)

**Development run: validation splits only (seeds 42, 7, 1234).** Not confirmatory.

Decision: frozen model + rules under max_severity, then the WP3 semantics. The lineage count is an offline upper bound (no item-level provenance offline).

| Seed | Benign runs | Escalated (any) | via RESTRICTED+external | via lineage (upper bound) | Benign steps escalated | Unsafe steps newly escalated |
|---|---|---|---|---|---|---|
| 42 | 353 | 0 (0.0%) | 0 | 0 | 0 | 0 |
| 7 | 353 | 0 (0.0%) | 0 | 0 | 0 | 0 |
| 1234 | 353 | 0 (0.0%) | 0 | 0 | 0 | 0 |
| **pooled** | 1059 | 0 (0.0%) | 0 | 0 | 0 | 0 |

## Where RESTRICTED occurs (steps per seed)

Context for the counts above: the semantics can only fire where the v2 decision is RESTRICTED. External steps are never RESTRICTED here, and the few benign RESTRICTED steps are cross_agent steps with no later allowed external send.

| Seed | attack_cross_agent | attack_external | attack_internal | benign_cross_agent | benign_external | benign_internal |
|---|---|---|---|---|---|---|
| 42 | 59 | 0 | 0 | 5 | 0 | 0 |
| 7 | 70 | 0 | 0 | 6 | 0 | 0 |
| 1234 | 71 | 0 | 0 | 4 | 0 | 0 |
