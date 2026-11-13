"""Reusable Streamlit UI fragments shared across dashboard pages."""
import html

import streamlit as st
from dashboard.theme import decision_badge_html, DECISION_COLORS, TEXT_SECONDARY


def metric_card(label: str, value: str):
    st.markdown(
        f'<div class="pv-card"><div class="pv-metric-label">{label}</div>'
        f'<div class="pv-metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def governance_step_row(step_number: int, description: str, decision: dict, blocked: bool):
    css_class = "blocked" if blocked else "allowed"
    action = decision.get("action", {})
    badge = decision_badge_html(decision["decision"])
    risk = decision["risk_score"]
    source_label = "policy rule" if decision["source"] == "policy_engine" else "risk model"

    st.markdown(
        f"""
        <div class="pv-step-row {css_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="pv-pill-label">STEP {step_number}</span>
                    &nbsp;&nbsp;<b>{description}</b>
                </div>
                {badge}
            </div>
            <div class="pv-mono" style="margin-top: 4px;">
                agent={action.get('agent_role','?')} &middot; tool={action.get('tool_name','?')}
                &middot; risk={risk:.3f} &middot; source={source_label}
            </div>
            <div class="pv-caption" style="margin-top: 2px;">{decision['reason']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def not_run_step_row(step_number: int, description: str, planned: dict, halted_at: int):
    st.markdown(
        f"""
        <div class="pv-step-row" style="opacity:0.5;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="pv-pill-label">STEP {step_number}</span>
                    &nbsp;&nbsp;<b>{html.escape(description)}</b>
                </div>
                <span class="pv-pill-label">NOT RUN</span>
            </div>
            <div class="pv-mono" style="margin-top: 4px;">
                agent={html.escape(planned['agent_role'])} &middot; tool={html.escape(planned['tool_name'])}
            </div>
            <div class="pv-caption" style="margin-top: 2px;">Not evaluated or executed: the run stopped at step {halted_at}.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def verdict_banner(is_attack: bool, was_blocked: bool, blocked_at_step=None, total_steps=0, not_run=0):
    if not is_attack:
        if was_blocked:
            st.markdown(
                f'<div class="pv-banner-warn">Benign task was stopped at step {blocked_at_step} of '
                f'{total_steps} (a false positive). {not_run} later step(s) did not run.</div>',
                unsafe_allow_html=True,
            )
            return
        st.markdown(
            '<div class="pv-banner-safe">Benign task completed with no governance intervention.</div>',
            unsafe_allow_html=True,
        )
        return

    if was_blocked:
        if not_run == 1:
            later = f"Step {total_steps} was not evaluated or executed."
        elif not_run:
            later = f"Steps {blocked_at_step + 1} to {total_steps} were not evaluated or executed."
        else:
            later = "It was the last step of the sequence."
        st.markdown(
            f'<div class="pv-banner-safe">Attack stopped at step {blocked_at_step} of {total_steps}: '
            f'governance did not allow it, so it did not execute. {later}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="pv-banner-danger">All steps were allowed to execute. Governance did not '
            'intervene on this run.</div>',
            unsafe_allow_html=True,
        )


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="pv-header-row"><h2 style="margin-bottom:0;">{title}</h2></div>',
                unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="pv-caption" style="margin-bottom:20px;">{subtitle}</div>',
                    unsafe_allow_html=True)


def export_button(data: dict, filename_prefix: str):
    import json
    from datetime import datetime, timezone
    data["exported_at"] = datetime.now(timezone.utc).isoformat()
    json_str = json.dumps(data, indent=2, default=str)
    st.download_button(
        label="Export results",
        data=json_str,
        file_name=f"{filename_prefix}_{data.get('run_id', 'run')}.json",
        mime="application/json",
    )


def logo():
    st.markdown(
        '<div class="pv-logo">Priv<span class="pv-logo-accent">Agent</span></div>'
        '<div class="pv-caption" style="margin-bottom:18px;">Runtime governance for multi-agent AI</div>',
        unsafe_allow_html=True,
    )
