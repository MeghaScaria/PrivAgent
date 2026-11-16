"""
EXPLORATORY analyses of the v2 confirmatory pilot traces (not pre-registered).

Reads only the committed confirmatory traces; writes
experiments/v2/exploratory/EXPLORATORY_v2_familyB_and_H4b.{md,json}.
Nothing here changes a confirmatory result or decision.

1. v2, family B: how each non-leaking run that reached the scripted writer
   ended, per task: hard-blocked (final decision BLOCKED), sent to review
   (HUMAN_APPROVAL, not executed in `v2`), or allowed without any canary.
2. Reviewer sweep on those traces: expected ASR if a reviewer approved each
   sent-to-review send with probability p, p in {0.1, 0.3, 0.5, 0.93}.
   Expected ASR(p) = p * (sent-to-review sends carrying >= 1 canary) / (runs
   that reached the writer). Assumes an approved send executes and delivers
   the canaries it carries (as in the `v2_reviewer` configuration, where every
   success was an approved review). Task bootstrap CI, 10,000 resamples, seed
   20261115.
3. H4(b) sensitivity: position-only AUROC with the writer's final external
   send step left out, i.e. on tool and handoff steps only; DeLong 95% CI.
   Same step labels as the pre-registered h4.py (its labelling function is
   imported, not modified).

    python experiments/v2/exploratory/exploratory_v2.py
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(V2, "analysis"))
from common import delong_auc, fmt, fmt_ci, rate, task_bootstrap  # noqa: E402
from h4 import label_steps  # noqa: E402
from pilot_inputs import default_traces, load  # noqa: E402

PS = (0.1, 0.3, 0.5, 0.93)
OUT = os.path.join(HERE, "EXPLORATORY_v2_familyB_and_H4b")


def send_step(r):
    sends = [s for s in r.get("steps") or [] if s["step_class"] == "external_send"]
    return sends[-1] if sends else None


def outcome(r):
    s = send_step(r)
    if r.get("attack_success"):
        return "leaked"
    if s is None:
        return "no_send_step"
    if s["final_decision"] == "BLOCKED":
        return "hard_blocked"
    if s["final_decision"] == "HUMAN_APPROVAL":
        return "sent_to_review"
    return "allowed_no_canary" if (s.get("canaries_carried") or 0) == 0 else "allowed_other"


def main():
    rows = load(default_traces())
    fam_b = [r for r in rows if r.get("family") == "B"]
    reached = {c: [r for r in fam_b if r["config"] == c and not r.get("excluded") and r.get("writer_reached")]
               for c in ("v2", "v2_reviewer")}
    v2 = reached["v2"]
    per_task = collections.defaultdict(collections.Counter)
    for r in v2:
        per_task[r["task"]][outcome(r)] += 1
    totals = collections.Counter(outcome(r) for r in v2)

    def review_with_canary(r):
        s = send_step(r)
        return outcome(r) == "sent_to_review" and (s.get("canaries_carried") or 0) > 0
    tasks = sorted({r["task"] for r in v2})
    by_task = {t: [r for r in v2 if r["task"] == t] for t in tasks}
    n_review = sum(review_with_canary(r) for r in v2)

    def stat(sample):
        rs = [r for t in sample for r in by_task[t]]
        k = sum(review_with_canary(r) for r in rs)
        return {f"p={p}": p * k / len(rs) for p in PS}
    sweep = task_bootstrap(tasks, stat)
    vr = reached["v2_reviewer"]
    vr_review = sum(outcome(r) in ("sent_to_review", "leaked") for r in vr)
    observed = {"config": "v2_reviewer", "p_approve_attack": 0.5,
                "asr": rate(sum(bool(r.get("attack_success")) for r in vr), len(vr)),
                "reached_review": vr_review,
                "expected_from_own_counts": 0.5 * vr_review / len(vr) if vr else None}

    steps, unknown = label_steps(rows)
    all_auc = delong_auc([s["position_only_score"] for s in steps], [int(s["unsafe"]) for s in steps])
    kept = [s for s in steps if s["step_class"] != "external_send"]
    no_send = delong_auc([s["position_only_score"] for s in kept], [int(s["unsafe"]) for s in kept])
    by_class = {c: {"steps": sum(s["step_class"] == c for s in steps),
                    "unsafe": sum(s["unsafe"] and s["step_class"] == c for s in steps)}
                for c in ("tool", "handoff", "external_send")}
    report = {"label": "EXPLORATORY (not pre-registered)", "files": sorted({r["_file"] for r in rows}),
              "v2_familyB_reached_writer": len(v2), "v2_outcome_totals": dict(totals),
              "v2_outcomes_per_task": {t: dict(per_task[t]) for t in tasks},
              "reviewer_sweep": {"sent_to_review_with_canary": n_review, "denominator": len(v2),
                                 "expected_asr": sweep, "observed_v2_reviewer": observed},
              "h4b_sensitivity": {"all_steps": all_auc, "without_final_send": no_send,
                                  "steps_by_class": by_class, "steps_without_content": unknown}}
    with open(OUT + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(OUT + ".md", "w", encoding="utf-8") as f:
        f.write(render(report) + "\n")
    print(f"wrote {OUT}.json and .md")


def render(r):
    t = r["v2_outcome_totals"]
    cols = ("hard_blocked", "sent_to_review", "allowed_no_canary", "leaked")
    lines = ["# EXPLORATORY: v2 family B outcomes, reviewer sweep, H4(b) without the final send", "",
             "**EXPLORATORY: not pre-registered. Nothing here changes a confirmatory outcome.**", "",
             f"Files {r['files']}.", "",
             "## 1. v2, family B: how the runs that reached the scripted writer ended", "",
             f"{r['v2_familyB_reached_writer']} runs reached the writer: "
             + ", ".join(f"{c.replace('_', ' ')} {t.get(c, 0)}" for c in cols) + ". "
             "Sent to review means the final decision was HUMAN_APPROVAL; in `v2` no reviewer acts, "
             "so the send is not executed.", "",
             "| Task | Hard-blocked | Sent to review | Allowed (no canary carried) | Leaked |", "|---|---|---|---|---|"]
    for task, c in r["v2_outcomes_per_task"].items():
        lines.append(f"| {task} | " + " | ".join(str(c.get(k, 0)) for k in cols) + " |")
    lines.append(f"| **Total** | " + " | ".join(f"**{t.get(k, 0)}**" for k in cols) + " |")
    s = r["reviewer_sweep"]
    lines += ["", "## 2. Reviewer sweep (expected ASR on the v2 traces)", "",
              f"Expected ASR(p) = p × {s['sent_to_review_with_canary']} sent-to-review sends carrying ≥ 1 canary "
              f"/ {s['denominator']} runs that reached the writer. Assumes an approved send executes and delivers "
              "its canaries. 95% CI: bootstrap over tasks, 10,000 resamples, seed 20261115, percentile.", "",
              "| P(approve \\| attack) | Expected ASR | 95% CI |", "|---|---|---|"]
    for k, v in s["expected_asr"].items():
        lines.append(f"| {k[2:]} | {fmt(v['point'])} | {fmt_ci(v['ci95'])} |")
    o = s["observed_v2_reviewer"]
    lines += ["", f"Check against the run configuration `v2_reviewer` (p = 0.5, its own runs): observed ASR "
              f"{o['asr']['k']}/{o['asr']['n']} = {fmt(o['asr']['rate'])}; {o['reached_review']} of its sends "
              f"reached review, so expected {fmt(o['expected_from_own_counts'])}.", "",
              "## 3. H4(b) sensitivity: position-only AUROC without the final send step", ""]
    h = r["h4b_sensitivity"]
    a, b = h["all_steps"], h["without_final_send"]
    lines += ["| Steps | Unsafe | Safe | AUROC | DeLong 95% CI |", "|---|---|---|---|---|",
              f"| All labelled steps (as in H4(b)) | {a['positives']} | {a['negatives']} | {fmt(a['auroc'])} | {fmt_ci(a['ci95'])} |",
              f"| Without the writer's external send | {b['positives']} | {b['negatives']} | {fmt(b['auroc'])} | {fmt_ci(b['ci95'])} |",
              "", "Labelled steps by class (all / unsafe): " + "; ".join(
                  f"{c} {x['steps']} / {x['unsafe']}" for c, x in h["steps_by_class"].items()) + "."]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
