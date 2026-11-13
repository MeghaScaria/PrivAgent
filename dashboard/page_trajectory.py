"""Page 2: Trajectory Viewer. Reads the audit log and displays any past
run (from the Research Assistant or the Attack Lab) as a step-by-step,
colour-coded governance timeline."""
import streamlit as st
from governance.audit_logger import get_audit_logger
from dashboard.components import metric_card, page_header, export_button
from dashboard.theme import decision_badge_html


def render():
    page_header(
        "Trajectory Viewer",
        "Every governed action from every run, in the order it was evaluated. "
        "Pick a run to inspect its full decision trail.",
    )

    logger = get_audit_logger()
    logger.load_from_disk(limit=2000)
    events = logger.all_events(limit=2000)

    if not events:
        st.markdown(
            '<div class="pv-caption">No runs yet. Use the Research Assistant or Attack '
            'Laboratory pages to generate a trajectory.</div>',
            unsafe_allow_html=True,
        )
        return

    run_ids = list(dict.fromkeys(e["run_id"] for e in reversed(events)))  # most recent first, deduped

    default_index = 0
    last_run_id = st.session_state.get("last_run_id")
    if last_run_id in run_ids:
        default_index = run_ids.index(last_run_id)

    selected_run = st.selectbox("Run ID", options=run_ids, index=default_index)

    run_events = [e for e in events if e["run_id"] == selected_run]

    total = len(run_events)
    autonomous = sum(1 for e in run_events if e["decision"] == "AUTONOMOUS")
    restricted = sum(1 for e in run_events if e["decision"] == "RESTRICTED")
    approval = sum(1 for e in run_events if e["decision"] == "HUMAN_APPROVAL")
    blocked = sum(1 for e in run_events if e["decision"] == "BLOCKED")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Total actions", str(total))
    with c2:
        metric_card("Autonomous", str(autonomous))
    with c3:
        metric_card("Restricted", str(restricted))
    with c4:
        metric_card("Human approval", str(approval))
    with c5:
        metric_card("Blocked", str(blocked))

    st.write("")
    st.markdown("#### Decision trail")

    for i, e in enumerate(run_events):
        badge = decision_badge_html(e["decision"])
        css_class = "blocked" if e["decision"] == "BLOCKED" else "allowed"
        st.markdown(
            f"""
            <div class="pv-step-row {css_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div><span class="pv-pill-label">STEP {i+1}</span>&nbsp;&nbsp;
                        <b>{e['agent_role']}</b> &rarr; <span class="pv-mono">{e['tool_name']}</span>
                    </div>
                    {badge}
                </div>
                <div class="pv-mono" style="margin-top:4px;">
                    risk={e['risk_score']:.3f} &middot; source={e['source']} &middot;
                    trajectory_length_at_time={e['trajectory_length']}
                </div>
                <div class="pv-caption" style="margin-top:2px;">{e['reason']}</div>
                <div class="pv-caption" style="margin-top:2px; opacity:0.6;">{e['timestamp']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    export_button(
        {
            "run_id": selected_run,
            "governance_events": run_events,
            "summary": {
                "total_actions": total,
                "autonomous": autonomous,
                "restricted": restricted,
                "human_approval": approval,
                "blocked": blocked,
            },
        },
        filename_prefix="privagent_trajectory",
    )
