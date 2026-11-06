import importlib
import os

import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="PresyoPH | Inflation & Purchasing Power Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from views.common import PAGES, build_context  # noqa: E402  (after set_page_config)

css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

logo_path = os.path.join(BASE_DIR, "assets", "logo.svg")
logo_html = ""
if os.path.exists(logo_path):
    with open(logo_path, "r", encoding="utf-8") as f:
        logo_html = f.read()

ctx = None  # filled in below, after the sidebar is drawn


def _make_page(module_name):
    module = importlib.import_module(f"views.{module_name}")

    def run_page():
        module.render(ctx)

    return run_page


pages = [
    st.Page(_make_page(module), title=title, icon=icon, url_path=url_path, default=(i == 0))
    for i, (module, title, icon, url_path) in enumerate(PAGES)
]
navigation = st.navigation(pages, position="hidden")

st.sidebar.markdown(
    f"""
    <div class='brand'>
        <div class='brand-logo'>{logo_html}</div>
        <div><div class='brand-title'>PresyoPH</div><div class='brand-sub'>Price &amp; inflation analytics</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)
for page in pages:
    st.sidebar.page_link(page)
st.sidebar.divider()

ctx = build_context()
navigation.run()
