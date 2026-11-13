"""
Visual design system for the PrivAgent dashboard. One dark base, one
accent color, and four reserved semantic colors for governance
decisions only -- nothing else in the UI is allowed to use color, which
is what keeps a monitoring dashboard like this from looking noisy.
"""

# --- Palette -----------------------------------------------------------
BG = "#0d1117"
SURFACE = "#161b22"
SURFACE_RAISED = "#1c2128"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#6e7681"
ACCENT = "#58a6ff"
ACCENT_DIM = "#1f6feb"

# Reserved for governance decisions only.
COLOR_AUTONOMOUS = "#3fb950"
COLOR_RESTRICTED = "#d29922"
COLOR_HUMAN_APPROVAL = "#db6d28"
COLOR_BLOCKED = "#f85149"

DECISION_COLORS = {
    "AUTONOMOUS": COLOR_AUTONOMOUS,
    "RESTRICTED": COLOR_RESTRICTED,
    "HUMAN_APPROVAL": COLOR_HUMAN_APPROVAL,
    "BLOCKED": COLOR_BLOCKED,
}

FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "'Helvetica Neue', Arial, sans-serif"
)
MONO_STACK = (
    "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
)

CSS = f"""
<style>
    .stApp {{
        background-color: {BG};
        color: {TEXT_PRIMARY};
        font-family: {FONT_STACK};
    }}

    /* Hide default Streamlit chrome for a cleaner, product-like feel */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent;}}

    section[data-testid="stSidebar"] {{
        background-color: {SURFACE};
        border-right: 1px solid {BORDER};
    }}

    h1, h2, h3, h4 {{
        color: {TEXT_PRIMARY};
        font-weight: 600;
        letter-spacing: -0.01em;
    }}

    p, li, span, label {{
        color: {TEXT_PRIMARY};
    }}

    .pv-caption {{
        color: {TEXT_SECONDARY};
        font-size: 0.85rem;
    }}

    .pv-card {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 12px;
    }}

    .pv-card-raised {{
        background-color: {SURFACE_RAISED};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 20px 22px;
        margin-bottom: 12px;
    }}

    .pv-metric-label {{
        color: {TEXT_SECONDARY};
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }}

    .pv-metric-value {{
        color: {TEXT_PRIMARY};
        font-size: 1.7rem;
        font-weight: 600;
        font-family: {MONO_STACK};
    }}

    .pv-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: {MONO_STACK};
        letter-spacing: 0.02em;
    }}

    .pv-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }}

    .pv-step-row {{
        border-left: 2px solid {BORDER};
        padding: 10px 0 10px 16px;
        margin-left: 4px;
    }}

    .pv-step-row.blocked {{
        border-left: 2px solid {COLOR_BLOCKED};
    }}

    .pv-step-row.allowed {{
        border-left: 2px solid {COLOR_AUTONOMOUS};
    }}

    .pv-mono {{
        font-family: {MONO_STACK};
        font-size: 0.82rem;
        color: {TEXT_SECONDARY};
    }}

    .pv-divider {{
        border: none;
        border-top: 1px solid {BORDER};
        margin: 18px 0;
    }}

    .pv-banner-safe {{
        background-color: rgba(63, 185, 80, 0.1);
        border: 1px solid {COLOR_AUTONOMOUS};
        border-radius: 8px;
        padding: 16px 20px;
        color: {COLOR_AUTONOMOUS};
        font-weight: 600;
    }}

    .pv-banner-danger {{
        background-color: rgba(248, 81, 73, 0.1);
        border: 1px solid {COLOR_BLOCKED};
        border-radius: 8px;
        padding: 16px 20px;
        color: {COLOR_BLOCKED};
        font-weight: 600;
    }}

    .pv-banner-warn {{
        background-color: rgba(210, 153, 34, 0.1);
        border: 1px solid {COLOR_RESTRICTED};
        border-radius: 8px;
        padding: 16px 20px;
        color: {COLOR_RESTRICTED};
        font-weight: 600;
    }}

    .stButton > button {{
        background-color: {ACCENT_DIM};
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
    }}
    .stButton > button:hover {{
        background-color: {ACCENT};
        color: white;
    }}

    .pv-pill-label {{
        color: {TEXT_MUTED};
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }}

    div[data-testid="stMetric"] {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 12px 16px;
    }}

    .pv-header-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }}

    .pv-logo {{
        font-family: {MONO_STACK};
        font-weight: 700;
        font-size: 1.1rem;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.02em;
    }}

    .pv-logo-accent {{
        color: {ACCENT};
    }}
</style>
"""


def decision_badge_html(decision: str) -> str:
    color = DECISION_COLORS.get(decision, TEXT_SECONDARY)
    return (
        f'<span class="pv-badge" style="background-color: rgba(0,0,0,0.2); '
        f'color: {color}; border: 1px solid {color};">'
        f'<span class="pv-dot" style="background-color: {color};"></span>{decision}</span>'
    )
