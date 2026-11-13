"""
PrivAgent dashboard entry point. Run with: streamlit run dashboard/app.py
(or `python main.py`, which launches this for you).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="PrivAgent",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.theme import CSS
from dashboard.components import logo
from agents.mcp_client import get_mcp_manager

st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Starting MCP servers...")
def _startup():
    manager = get_mcp_manager()
    return manager.is_ready()


mcp_ready = _startup()

with st.sidebar:
    logo()
    st.markdown('<hr class="pv-divider">', unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        options=["Research Assistant", "Trajectory Viewer", "Attack Laboratory", "Human Approval"],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="pv-divider">', unsafe_allow_html=True)

    status_color = "#3fb950" if mcp_ready else "#f85149"
    status_text = "MCP servers connected" if mcp_ready else "MCP servers unavailable"
    st.markdown(
        f'<div class="pv-caption"><span class="pv-dot" style="background-color:{status_color};'
        f'display:inline-block;"></span>&nbsp;{status_text}</div>',
        unsafe_allow_html=True,
    )

    key_present = bool(os.environ.get("GOOGLE_API_KEY"))
    key_color = "#3fb950" if key_present else "#d29922"
    key_text = "Gemini API key loaded" if key_present else "No Gemini API key (Attack Lab still works)"
    st.markdown(
        f'<div class="pv-caption" style="margin-top:6px;"><span class="pv-dot" '
        f'style="background-color:{key_color}; display:inline-block;"></span>&nbsp;{key_text}</div>',
        unsafe_allow_html=True,
    )

if page == "Research Assistant":
    from dashboard.page_research import render
    render()
elif page == "Trajectory Viewer":
    from dashboard.page_trajectory import render
    render()
elif page == "Human Approval":
    from dashboard.page_approval import render
    render()
else:
    from dashboard.page_attack_lab import render
    render()
