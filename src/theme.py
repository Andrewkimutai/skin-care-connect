"""
theme.py
Custom CSS and small reusable UI components for Skin Care Connect.
Keeps styling out of the page logic in app.py.
"""
import streamlit as st

PRIMARY = "#0F766E"       # teal
PRIMARY_DARK = "#0B5A54"
DANGER = "#DC2626"
WARNING = "#D97706"
SUCCESS = "#15803D"
MUTED = "#5B6B6A"

CUSTOM_CSS = f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    .stApp {{
        background: linear-gradient(180deg, #F0FBF9 0%, #FFFFFF 260px);
    }}

    .scc-hero {{
        padding: 1.6rem 1.8rem;
        border-radius: 16px;
        background: linear-gradient(120deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%);
        color: white;
        margin-bottom: 1.4rem;
        box-shadow: 0 8px 24px rgba(15, 118, 110, 0.18);
    }}
    .scc-hero h1 {{
        margin: 0 0 0.2rem 0;
        font-size: 1.9rem;
        color: white;
    }}
    .scc-hero p {{
        margin: 0;
        opacity: 0.92;
        font-size: 0.98rem;
    }}

    .scc-card {{
        background: white;
        border: 1px solid #E4EFEE;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 10px rgba(15, 42, 42, 0.04);
    }}

    .scc-badge {{
        display: inline-block;
        padding: 0.18rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .scc-badge-role {{ background: #E4EFEE; color: {PRIMARY_DARK}; }}
    .scc-badge-danger {{ background: #FDE8E8; color: {DANGER}; }}
    .scc-badge-warning {{ background: #FEF3E2; color: {WARNING}; }}
    .scc-badge-success {{ background: #E7F6EC; color: {SUCCESS}; }}

    .scc-disclaimer {{
        border-left: 4px solid {WARNING};
        background: #FFFBEB;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 0.87rem;
        color: #7C4A03;
        margin-bottom: 1rem;
    }}

    .scc-result-hero {{
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1rem;
    }}
    .scc-result-danger {{ background: #FEF2F2; border: 1px solid #FCA5A5; }}
    .scc-result-warning {{ background: #FFFBEB; border: 1px solid #FCD34D; }}
    .scc-result-success {{ background: #F0FDF4; border: 1px solid #86EFAC; }}

    section[data-testid="stSidebar"] {{
        background: #FBFEFD;
        border-right: 1px solid #E4EFEE;
    }}

    div.stButton > button {{
        border-radius: 10px;
        font-weight: 600;
    }}
    div.stButton > button[kind="primary"] {{
        background: {PRIMARY};
        border-color: {PRIMARY};
    }}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, icon: str = "🩺"):
    st.markdown(
        f"""
        <div class="scc-hero">
            <h1>{icon} {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def disclaimer(text: str | None = None):
    text = text or (
        "This tool is an academic research prototype (HAM10000-trained classifier). "
        "It is <strong>not a medical device</strong> and does not provide a diagnosis. "
        "Model performance varies significantly by class — always consult a qualified "
        "dermatologist for any concerning skin lesion."
    )
    st.markdown(f'<div class="scc-disclaimer">⚠️ {text}</div>', unsafe_allow_html=True)


def badge(text: str, kind: str = "role"):
    st.markdown(f'<span class="scc-badge scc-badge-{kind}">{text}</span>', unsafe_allow_html=True)


def card_start():
    st.markdown('<div class="scc-card">', unsafe_allow_html=True)


def card_end():
    st.markdown('</div>', unsafe_allow_html=True)
