"""Custom Streamlit CSS overrides."""
import streamlit as st

_CSS = """
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.82rem !important; }
.stTabs [data-baseweb="tab"] { font-size: 0.92rem; font-weight: 500; }
div[data-testid="stSidebarContent"] h2 { font-size: 1.1rem; }
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)
