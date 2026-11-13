"""Page 1: Live Research Assistant. Runs the full LangGraph pipeline
(orchestrator -> retriever -> analyst -> writer) against real MCP
servers with live governance interception. Requires GOOGLE_API_KEY."""
import os
import streamlit as st
from agents.graph import build_graph
from agents.state import new_state
from governance.trajectory_monitor import TrajectoryMonitor
from dashboard.components import metric_card, governance_step_row, page_header, export_button
from dashboard.theme import decision_badge_html

EXAMPLE_TASKS = [
    "Summarize recent trends in AI infrastructure spending",
    "What pending vendor payments do we have?",
    "Compile a short report on employee headcount by department",
    "Give me a comparative overview of recent industry research",
]


def render():
    page_header(
        "Research Assistant",
        "Ask a question. Watch the orchestrator, retriever, analyst, and writer "
        "agents collaborate through real MCP tool calls, with every call "
        "governed live.",
    )

    if not os.environ.get("GOOGLE_API_KEY"):
        st.markdown(
            '<div class="pv-banner-warn">GOOGLE_API_KEY is not set. This page needs a free '
            'Gemini key from aistudio.google.com/apikey -- copy .env.example to .env and add it, '
            'then restart. The Attack Laboratory page works without one.</div>',
            unsafe_allow_html=True,
        )
        return

    task = st.text_area("Your question", placeholder=EXAMPLE_TASKS[0], height=80)
    cols = st.columns(4)
    for i, example in enumerate(EXAMPLE_TASKS):
        if cols[i].button(example, key=f"example_{i}", use_container_width=True):
            task = example
            st.session_state["_prefill_task"] = example

    if st.session_state.get("_prefill_task") and not task:
        task = st.session_state["_prefill_task"]

    run_clicked = st.button("Run", type="primary")
    if not run_clicked or not task:
        return

    run_id_prefix = "research"
    import uuid
    run_id = f"{run_id_prefix}_{str(uuid.uuid4())[:8]}"
    monitor = TrajectoryMonitor(model_type="trajectory", run_id=run_id)
    app = build_graph(monitor)
    state = new_state(task=task, run_id=run_id)

    agent_log = st.container()
    governance_log = st.container()

    with st.spinner("Agents working..."):
        with agent_log:
            st.markdown("#### Agent activity")
            agent_placeholder = st.empty()

        with governance_log:
            st.markdown("#### Governance decisions")
            gov_placeholder = st.empty()

        rendered_messages = []
        rendered_events = []
        final_state = None

        try:
            for partial in app.stream(state):
                for node_name, node_state in partial.items():
                    final_state = node_state
                    new_messages = node_state.get("messages", [])[len(rendered_messages):]
                    for m in new_messages:
                        rendered_messages.append(m)
                    with agent_placeholder.container():
                        for m in rendered_messages:
                            st.markdown(
                                f'<div class="pv-card"><span class="pv-pill-label">{m["role"].upper()}</span>'
                                f'<div style="margin-top:4px;">{m["content"]}</div></div>',
                                unsafe_allow_html=True,
                            )

                    new_events = node_state.get("governance_events", [])[len(rendered_events):]
                    for e in new_events:
                        rendered_events.append(e)
                    with gov_placeholder.container():
                        for i, e in enumerate(rendered_events):
                            badge = decision_badge_html(e["decision"])
                            css_class = "blocked" if e["blocked"] else "allowed"
                            st.markdown(
                                f"""
                                <div class="pv-step-row {css_class}">
                                    <div style="display:flex; justify-content:space-between;">
                                        <div><b>{e['agent_role']}</b> &rarr;
                                            <span class="pv-mono">{e['tool_name']}</span></div>
                                        {badge}
                                    </div>
                                    <div class="pv-caption" style="margin-top:2px;">{e['reason']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
        except Exception as exc:
            st.error(f"The pipeline hit an error: {exc}")
            return

    st.write("")
    if final_state and final_state.get("task_halted"):
        st.markdown(
            f'<div class="pv-banner-warn">Task halted by governance: '
            f'{final_state.get("halt_reason", "")}</div>',
            unsafe_allow_html=True,
        )
    elif final_state and final_state.get("final_output"):
        st.markdown("#### Final answer")
        st.markdown(
            f'<div class="pv-card-raised">{final_state["final_output"]}</div>',
            unsafe_allow_html=True,
        )

    if final_state:
        st.write("")
        summary = monitor.summary()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Documents", str(len(final_state.get("retrieved_documents", []))))
        with c2:
            metric_card("Records", str(len(final_state.get("retrieved_records", []))))
        with c3:
            metric_card("Governed actions", str(summary["total_actions_proposed"]))
        with c4:
            metric_card("Blocked", str(summary["blocked"]))

        st.write("")
        export_button(
            {
                "run_id": run_id,
                "task": task,
                "task_type": final_state.get("task_type"),
                "messages": final_state.get("messages", []),
                "governance_events": final_state.get("governance_events", []),
                "final_output": final_state.get("final_output"),
                "document_count": len(final_state.get("retrieved_documents", [])),
                "record_count": len(final_state.get("retrieved_records", [])),
                "web_result_count": len(final_state.get("web_results", [])),
            },
            filename_prefix="privagent_research",
        )

    st.session_state["last_run_id"] = run_id
    st.session_state["last_run_source"] = "research"
