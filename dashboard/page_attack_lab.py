"""Page 3: Attack Laboratory. Replays a known attack pattern step by
step through the real governed pipeline and real MCP servers, with no
LLM/API key required."""
import time
import streamlit as st
from governance.trajectory_monitor import TrajectoryMonitor
from governance.attack_scenarios import SCENARIOS, run_scenario
from dashboard.components import (
    metric_card, governance_step_row, not_run_step_row, verdict_banner, page_header, export_button,
)

HELD_OUT_ATTACKS = {"path_cross_agent_leak"}


def render():
    page_header(
        "Attack Laboratory",
        "Replay a known attack pattern through the live governance pipeline. "
        "No API key required -- this page runs entirely on the trained risk "
        "models and real MCP tool calls.",
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        scenario_key = st.selectbox(
            "Attack scenario",
            options=list(SCENARIOS.keys()),
            format_func=lambda k: SCENARIOS[k]["label"],
        )
    with col2:
        st.write("")
        st.write("")
        run_clicked = st.button("Run scenario", type="primary", use_container_width=True)

    if scenario_key in HELD_OUT_ATTACKS:
        st.markdown(
            '<div class="pv-banner-warn">This attack type was held out entirely during model '
            'training and is used only to test generalisation to unseen attacks. The research '
            'paper reports imperfect (not 100%) generalisation on held-out attacks -- so this one '
            'is not guaranteed to be caught, unlike the others.</div>',
            unsafe_allow_html=True,
        )
        st.write("")

    if not run_clicked:
        st.markdown(
            '<div class="pv-caption">Select a scenario and click "Run scenario" to replay it live.</div>',
            unsafe_allow_html=True,
        )
        return

    monitor = TrajectoryMonitor(model_type="trajectory", task_type="financial_research", agent_count=3)
    scenario = SCENARIOS[scenario_key]

    # The run stops at the first step governance doesn't allow: nothing
    # after it is evaluated or executed, so the page shows exactly what ran.
    steps = run_scenario(scenario_key, monitor, halt_on_block=True)
    blocked_at = next((i + 1 for i, s in enumerate(steps) if s["blocked"]), None)
    not_run = sum(1 for s in steps if s["not_run"])

    st.markdown("#### Live trajectory")
    placeholder = st.empty()
    for shown in range(1, len(steps) + 1):
        with placeholder.container():
            for j, s in enumerate(steps[:shown]):
                if s["not_run"]:
                    not_run_step_row(j + 1, s["description"], s["planned"], blocked_at)
                else:
                    governance_step_row(j + 1, s["description"], s["decision"], s["blocked"])
        time.sleep(0.3)

    st.markdown("#### Result")
    verdict_banner(
        is_attack=scenario["is_attack"], was_blocked=blocked_at is not None,
        blocked_at_step=blocked_at, total_steps=len(steps), not_run=not_run,
    )

    st.write("")
    summary = monitor.summary()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Steps evaluated", str(summary["total_actions_proposed"]))
    with c2:
        metric_card("Executed", str(summary["autonomous"] + summary["restricted"]))
    with c3:
        metric_card("Sent for approval", str(summary["human_approval"]))
    with c4:
        metric_card("Blocked", str(summary["blocked"]))
    with c5:
        metric_card("Not run", str(not_run))

    st.write("")
    export_button(
        {
            "run_id": monitor.run_id,
            "scenario_key": scenario_key,
            "scenario_label": scenario["label"],
            "is_attack": scenario["is_attack"],
            "halted_on_block": True,
            "steps": [
                {
                    "description": s["description"],
                    "status": "not_run" if s["not_run"] else (
                        "stopped" if s["blocked"] else "executed"),
                    "decision": s["decision"],
                }
                for s in steps
            ],
            "was_blocked": blocked_at is not None,
            "blocked_at_step": blocked_at,
            "steps_not_run": not_run,
        },
        filename_prefix="privagent_attack",
    )

    st.session_state["last_run_id"] = monitor.run_id
    st.session_state["last_run_source"] = "attack_lab"
