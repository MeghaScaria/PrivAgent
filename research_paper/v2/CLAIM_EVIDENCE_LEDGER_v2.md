# Claim–evidence ledger: PrivAgent v2 (17 Nov 2026)

One row per number in `experiments/v2/CONFIRMATORY_REPORT.md`, plus the exploratory analyses and the WP1–WP6
development findings. Paths are relative to the repository root. **Commit** is the commit that last wrote the
supporting artifact.

**Verification status** (v1's codes, from `research_paper/final/CLAIM_EVIDENCE_LEDGER.md`):

| Status | Meaning |
|---|---|
| VERIFIED-RECOMP | recomputed from the raw files and matching the stored values. For v2 confirmatory rows: by the independent subagent check (`experiments/v2/INDEPENDENT_CHECK.md`, 17 Nov 2026), which did not read the analysis code; the item numbers refer to its table |
| VERIFIED-FILE | matches a stored result, log or evidence file (checked against the file) |
| VERIFIED-CODE | confirmed by reading the source code (or, here, the git history) |
| DEVLOG-ONLY | recorded only in the development log; labelled as such in the manuscript |
| NOT-RECOMPUTABLE | stored evidence only; the historical generator was not preserved |
| PROPOSAL | stated as future work, not implemented |
| LIT | from a verified publication |
| TEST-15NOV | v1's TEST-<date> code: the full gate passed on 15 Nov 2026 (129/129 tests, v1 Attack Lab replay byte-identical) |

A status followed by **RECOMP MISMATCH Mn** means the stored value matches its file, but the independent
recomputation read a definition differently and got another value (Mn as in `INDEPENDENT_CHECK.md`). Rows marked
**EXPLORATORY** are not pre-registered.

## P: pre-registration and process

| # | Claim | Planned location | Supporting artifact | Commit | Status |
|---|---|---|---|---|---|
| P1 | Pre-registration frozen 2026-11-15T13:25:37Z at commit `7727046`, SHA-256 `846374a7…c705ac`, before any confirmatory run | §6.1 | `experiments/v2/PREREGISTRATION_HASHES.md`; `experiments/v2/PREREGISTRATION_v2.md` | `6a59e1a` | VERIFIED-RECOMP (hash recomputed from the committed file; prefix hash rechecked 16 Nov at amendment 1) |
| P2 | Amendment 1 (editorial, stale DRAFT header); append-only, frozen prefix byte-identical; no hypothesis or rule changed | §6.1 | `experiments/v2/PREREGISTRATION_v2.md` (Amendments); `PREREGISTRATION_HASHES.md` | `9846df9` | VERIFIED-FILE |
| P3 | No code changed after the freeze; the only `.py` files added since are the exploratory and figure scripts | §6.1 | `git diff --stat 6a59e1a HEAD -- '*.py'` | `6a59e1a`.. | VERIFIED-CODE (git history, 17 Nov) |
| P4 | Code the registration refers to: `adc18b0`, `29b979c`, `984caf9`, `843d157`; analysis choices fixed in code (§6 of the pre-registration) | §6.1 | `experiments/v2/PREREGISTRATION_v2.md` §6 | `7727046` | VERIFIED-FILE |

## C: confirmatory results (`experiments/v2/CONFIRMATORY_REPORT.md`, commit `2ed41c7`)

Analysis outputs: `experiments/v2/results/confirmatory/analysis/h1..h5.{md,json}` (commit `7eec408`), produced by the
scripts of `843d157` unchanged.

| # | Claim | Planned location | Supporting artifact | Commit | Status |
|---|---|---|---|---|---|
| C1 | H1 offline downgrades (10 seeds × test, held-out types, variant B): `first_fire_v1` 463, `max_severity` 0, `max_severity_reviewable` 376; all ML BLOCKED → HUMAN_APPROVAL, 0 to an allowed decision | §7.5.1 | `results/confirmatory/precedence_ablation_confirmatory_runs.json`; `analysis/h1.json` | `c7bd602`, `7eec408` | VERIFIED-RECOMP (items 2, 4) |
| C2 | H1 live downgrades (WP4 confirmatory half): `first_fire_v1` 70, `max_severity` 0, `max_severity_reviewable` 70, 0 to allowed | §7.5.1 | `results/confirmatory/wp4_confirmatory.json`; `analysis/h1.json` | `8316825`, `7eec408` | VERIFIED-RECOMP (items 3, 5) |
| C3 | H1 SUPPORTED (0 downgrades under `max_severity`, offline and live) | §7.5.1 | `analysis/h1.md` | `7eec408` | VERIFIED-RECOMP (item 1) |
| C4 | H1 live cost, accurate declaration: `max_severity` hard-blocks 10/14 vs `first_fire_v1` 2/14, difference 0.571 [0.286, 0.786]; approval volume 2/14 vs 10/14 | §7.5.1; Fig. `v2_f3` | `analysis/h1.json` (`live.costs.accurate`) | `7eec408` | VERIFIED-FILE; **RECOMP MISMATCH M1**: numerators match, but 2 of the 14 benign runs request no send; per send (the pre-registration's wording) 10/12 vs 2/12, difference 0.667 (items 7–10) |
| C5 | H1 costs of `max_severity_reviewable` equal `first_fire_v1` (live 2/14, 10/14); every offline arm-minus-v1 cost difference 0.000 | §7.5.1 | `analysis/h1.json` | `7eec408` | VERIFIED-RECOMP (items 6, 11; denominator note M1) |
| C6 | H1 secondary: unsafe steps ending at HUMAN_APPROVAL; live 30/40, 0/40, 30/40; offline per set (`analysis/h1.md`) | §7.5.1 | `analysis/h1.md` | `7eec408` | VERIFIED-FILE (not in the independent check) |
| C7 | H2: shadow vs score R1-on, attack sends 14/40 → 0/40, exact McNemar p = 0.000122 | §7.5.2 | `analysis/h2.json`; `wp4_confirmatory.json` | `7eec408` | VERIFIED-RECOMP (items 13, 14) |
| C8 | H2: shadow vs score R1-off 14 → 14, p = 1; H2 SUPPORTED | §7.5.2 | `analysis/h2.json` | `7eec408` | VERIFIED-RECOMP (items 12, 15) |
| C9 | H2 cost: `handoff_enforce` halts 10/70 benign runs, 0.143 [0.079, 0.243]; R3 fired 0 times | §7.5.2 | `analysis/h2.json` | `7eec408` | VERIFIED-RECOMP (items 16, 17) |
| C10 | H3: under-reported + missing, shadow 12/16 vs enforce 0/16, p = 0.000488; SUPPORTED | §7.5.3 | `analysis/h3.json` | `7eec408` | VERIFIED-RECOMP (items 18–20) |
| C11 | H3 costs: accurate declaration, enforce = shadow (2/12 completed, 8/12 review, 2/12 hard-blocked); under-reported and missing, enforce completes 2/12 vs shadow 10/12 | §7.5.3 | `analysis/h3.json` | `7eec408` | VERIFIED-RECOMP (items 21, 22) |
| C12 | H4(a): frozen-model step recall path 1/62 vs direct 52/52; path − direct −0.984 [−1.000, −0.948]; SUPPORTED | §7.5.4; Fig. `v2_f4` | `analysis/h4.json` | `7eec408` | VERIFIED-RECOMP (items 23–25; CI item 26 within tolerance: −0.949) |
| C13 | H4(b): position-only AUROC 0.654, DeLong [0.601, 0.706] (114 unsafe, 283 safe steps); NOT SUPPORTED | §7.5.4 | `analysis/h4.json` | `7eec408` | VERIFIED-FILE; **RECOMP MISMATCH M2**: the pre-registration does not label attack-run steps without a canary. `h4.py` (the registered code, `843d157`) counts them as safe; leaving them unlabelled gives 142 safe steps, AUROC 0.599 [0.530, 0.668], which would be supported by the point rule. The independent check reproduced 0.654 exactly under `h4.py`'s reading (items 27–31) |
| C14 | H4 coverage: 397 labelled steps from 19 attack tasks and the benign runs; `atk_b_hr_depts` all v2 runs failed before the writer; `atk_b_ai_infra_hr` carried no canary | §7.5.4; §9.x | `analysis/h4.json`; family B trace | `7eec408`, `6362436` | VERIFIED-RECOMP (item 53) |
| C15 | H5 family B ASR per configuration (denominator: runs reaching the writer): no_governance 51/54, rules_only 18/56, ml_only 20/58, v1 16/57, v2 0/55, v2_reviewer 17/53; model failures before the writer 6/4/2/3/5/7; 0 exclusions; 0 harness faults | §7.5.5; Fig. `v2_f1` | `analysis/h5.json` | `7eec408` | VERIFIED-RECOMP (items 36–42) |
| C16 | H5: v2 − v1 −0.281 [−0.431, −0.145]; v2 − ml_only −0.345 [−0.517, −0.186]; SUPPORTED | §7.5.5 | `analysis/h5.json` | `7eec408` | VERIFIED-RECOMP (items 32–34; bootstrap bounds identical to 3 dp) |
| C17 | H5: v2 − rules_only −0.321 [−0.517, −0.148]; the claim that v2 beats rules_only is made | §7.5.5 | `analysis/h5.json` | `7eec408` | VERIFIED-RECOMP (item 35) |
| C18 | H5 benign utility: no_governance 23/40 = 0.575 [0.422, 0.715], rules_only 19/40, ml_only 20/40, v1 20/40, v2 18/40 = 0.450 [0.307, 0.602], v2_reviewer 22/40; approval volume v1 2, v2 5, v2_reviewer 5, others 0 (of 40) | §7.5.5; Fig. `v2_f2` | `analysis/h5.json` | `7eec408` | VERIFIED-RECOMP (items 43–47) |
| C18b | H5 latency: median 72–106 s per run | §7.5.5 | `analysis/h5.json` | `7eec408` | VERIFIED-FILE; **RECOMP MISMATCH M3**: the report pools family B and benign per configuration (71.6–105.5); benign only gives 81.4–94.0; the scope is not defined in the pre-registration (item 48) |
| C19 | Multiseed (descriptive): AUPRC test 0.965 [0.960, 0.968], held-out types 0.853 [0.847, 0.860], variant B 0.834 [0.828, 0.841]; step recall 0.953 / 0.562 / 0.338; runs caught 0.999 / 0.672 / 0.671 | §7.5.6 | `results/confirmatory/multiseed_confirmatory.{json,md}` | `c7bd602` | VERIFIED-FILE (item 51; copied, not recomputed) |
| C20 | Multiseed per type, runs caught: `path_cross_agent_leak` 28/1011 (0.028), `path_exfiltration` 18/505 (0.036), `path_privilege_escalation` 12/513 (0.023); every other type ≥ 0.995 | §7.5.6; Fig. `v2_f5` | `multiseed_confirmatory.json` | `c7bd602` | VERIFIED-FILE (item 52) |
| C21 | Pilot: qwen2.5:3b (digest `357c53fb…`), 360 family B + 240 benign runs, 0 infrastructure exclusions, 27 + 9 model failures; WP4 confirmatory 880 runs, 22 scenarios | §6.1; §9.x | `results/confirmatory/pilot_*.jsonl`; `wp4_confirmatory.json` | `6362436`, `c4d0b66`, `8316825` | VERIFIED-RECOMP (items 49, 50) |
| C22 | Family A dropped (no paid Gemini quota; free tier 20 requests/day); no Gemini calls | §6.1; §9.x | `PREREGISTRATION_v2.md` H5; `analysis/h5.json` | `7727046` | VERIFIED-FILE |
| C23 | Report observation: "the frozen model's own step decisions are not what stopped these sends" | (not to be used) | `CONFIRMATORY_REPORT.md` | `2ed41c7` | **WRONG** (M4, confirmed 17 Nov): in v2 the model's decision on all 52 canary-carrying sends is BLOCKED (44 relaxed to HUMAN_APPROVAL by `max_severity_reviewable`, 8 kept BLOCKED); it missed the handoffs (1/62), not the sends |

## X: exploratory analyses (`experiments/v2/exploratory/EXPLORATORY_v2_familyB_and_H4b.{md,json}`, commit `6b750b6`)

| # | Claim | Planned location | Supporting artifact | Commit | Status |
|---|---|---|---|---|---|
| X1 | EXPLORATORY. v2 family B, 55 runs reaching the writer: 8 hard-blocked, 44 sent to review, 3 allowed carrying no canary (all `atk_b_ai_infra_hr`), 0 leaked; per-task table | §7.6 | `EXPLORATORY_v2_familyB_and_H4b.md` §1 | `6b750b6` | VERIFIED-FILE (EXPLORATORY); consistent with independent check item 54 (44 + 8 canary sends) |
| X2 | EXPLORATORY. Expected ASR if review were approved with p: 0.080 [0.062, 0.095], 0.240 [0.185, 0.284], 0.400 [0.309, 0.474], 0.744 [0.575, 0.881] for p = 0.1, 0.3, 0.5, 0.93 (assumes an approved send delivers its canaries) | §7.6; §9.x | same, §2 | `6b750b6` | VERIFIED-FILE (EXPLORATORY) |
| X3 | EXPLORATORY. Position-only AUROC without the writer's send step: 0.567 [0.508, 0.625] (62 unsafe, 278 safe), vs 0.654 with it | §7.6; §9.x | same, §3 | `6b750b6` | VERIFIED-FILE (EXPLORATORY); uses `h4.py`'s labelling (see C13, M2) |
| X4 | EXPLORATORY. `v2_reviewer` observed 17/53 = 0.321; 41 of its sends reached review, so 0.387 expected at p = 0.5 | §7.6 | same, §2 | `6b750b6` | VERIFIED-FILE (EXPLORATORY) |

## D: development findings (WP1–WP6; development data only, not confirmatory)

| # | Claim | Planned location | Supporting artifact | Commit | Status |
|---|---|---|---|---|---|
| D1 | WP1 (dev: train, val, variant C; seeds 42, 7, 1234): `max_severity` 0 downgrades in every set; `first_fire_v1` 206 / 53 / 80; `max_severity_reviewable` 168 / 43 / 66, none to allowed | §4.13 | `experiments/v2/results/precedence_ablation_dev.md` | `bb9d53a` | VERIFIED-FILE |
| D2 | WP1 (dev): benign cost differences `max_severity` − `first_fire_v1` and `max_severity_reviewable` − `first_fire_v1` are +0.0000 [+0.0000, +0.0000] in every set (approval volume, ext. send hard-blocked, block rate, any stop) | §4.13 | same | `bb9d53a` | VERIFIED-FILE |
| D3 | WP2 (dev, live replay scenarios): scoring handoffs turns `hr_exfil_misreported` and `finance_exfil_misreported` from AUTONOMOUS/transmitted to BLOCKED/not transmitted; Attack Lab outcomes identical across v2 modes; `path_cross_agent_leak` missed in every mode | §4.14 | `experiments/v2/results/handoff_scoring_dev.md` | `a6f7fcc` | VERIFIED-FILE |
| D4 | WP2 (dev): every live handoff pseudo-action tuple appears in the seed-42 training data (25,841 rows) | §4.14 | same, coverage table | `a6f7fcc` | VERIFIED-FILE |
| D5 | WP3 (dev): the RESTRICTED semantics escalate 0 of 1,059 benign validation runs (3 seeds) | §4.15 | `experiments/v2/results/restricted_semantics_dev.md` | `468aec4` | VERIFIED-FILE |
| D6 | WP3: hash-chained logs, HKDF key separation, send binding implemented and tested | §4.15 | WP3 code and tests (`experiments/v2/WP3_DIFF.patch`) | `468aec4` | TEST-15NOV (code not re-read for this ledger) |
| D7 | WP4 (dev half, 24 scenarios × 5 declarations): H3 shadow 15/40 attack sends vs enforce (primary v2) 0/40; benign completed 30/65 vs 10/65; accurate declaration identical (3 completed / 8 review / 2 hard-blocked of 13) | §4.16 | `experiments/v2/results/wp4_dev.md`; `experiments/v2/MORNING_REPORT.md` §3 | `c453674` | VERIFIED-FILE |
| D8 | WP4 (dev): score with R1 on stops 40/40 attacks but completes 10/65 benign sends (50 hard-blocked) | §4.16 | `wp4_dev.md` per-condition table | `c453674` | VERIFIED-FILE |
| D9 | WP5 (dev, validation split, 10 seeds): AUPRC 0.968 [0.965, 0.971], step recall 0.957; seed-42 thresholds reproduce `models/thresholds.json` | §7.7 | `experiments/v2/results/multiseed_dev.md` | `89bbe1b` | VERIFIED-FILE |
| D10 | WP6 (dev smoke, qwen2.5:3b, 6 tasks, family A): 0 of 18 attack runs attempted a send | §7.7; §9.x | `experiments/v2/results/real_llm/smoke_ollama_qwen2.5-3b_20261115T035239.md` | `c453674` | VERIFIED-FILE |
| D11 | WP6 (dev, family B smoke, 36 runs): 2 runs failed before the writer from an empty `search_queries` list (`IndexError`), originally recorded as exclusions; reclassified as model failures (`adc18b0`) | §7.7 | `experiments/v2/results/real_llm/smoke_ollama_qwen2.5-3b_ts2-B_20261115T132601.md`; pre-registration third revision | `adc18b0` | VERIFIED-FILE |

## V: verification

| # | Claim | Planned location | Supporting artifact | Commit | Status |
|---|---|---|---|---|---|
| V1 | Independent recomputation: 53 items; 44 match, 2 within tolerance, 7 mismatch (M1–M3), plus M4 | §7.5.7 | `experiments/v2/INDEPENDENT_CHECK.md` | `b39b664` | VERIFIED-FILE |

## Unresolved items

1. **M2 (H4(b))**: the outcome depends on how attack-run steps without a canary are labelled. The registered code
   (`h4.py`, `843d157`) counts them as safe, and the confirmatory outcome stands as computed (NOT SUPPORTED). The paper
   must report that the pre-registration text left this undefined, and give 0.599 [0.530, 0.668] under the other reading.
2. **M1 (H1 live cost)**: `h1.py` divides by benign runs (14) where the pre-registration says benign sends (12). The
   paper must state the denominator; no decision depends on it.
3. **M3 (latency)**: the scope of "median seconds per run" must be stated (family B + benign pooled).
4. **C23 / M4**: one observation in `CONFIRMATORY_REPORT.md` is wrong. Whether to add a dated erratum to that report is
   the owner's decision; it has not been changed.
5. **LIT**: all v2 related-work entries are `[VERIFY]` in `research_paper/v2/PrivAgent_v2_DRAFT.md`.
