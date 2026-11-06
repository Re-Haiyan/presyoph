"""Shared setup, cached data loaders and small UI helpers for every page."""

import json
import os
import re
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from analytics.calculations import calculate_inflation_frame
from analytics.forecasting import run_forecasting_pipeline
from analytics.quality import find_stale_series
from database.db_manager import (
    get_commodity_groups,
    get_cpi_data,
    get_data_coverage,
    get_fies_data,
    get_region_names,
    initialize_db,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGES = [
    # (module, title, icon, url_path)
    ("dashboard", "Price Change Dashboard", ":material/dashboard:", "dashboard"),
    ("forecasting", "Time-Series Forecasting", ":material/trending_up:", "forecasting"),
    ("inflation", "Inflation Rate Viewer", ":material/show_chart:", "inflation"),
    ("purchasing_power", "Purchasing Power", ":material/payments:", "purchasing-power"),
    ("about", "About & Methodology", ":material/info:", "about"),
]


@dataclass
class Context:
    region: str
    region_map: dict
    coverage: tuple

    @property
    def region_name(self):
        return self.region_map[self.region]

    @property
    def is_national(self):
        return self.region == "PH"


# ---------------------------------------------------------------- cached data
@st.cache_resource
def setup_database():
    return initialize_db()


@st.cache_data(show_spinner=False)
def load_cpi(region_code=None, commodity_group=None):
    return get_cpi_data(region_code=region_code, commodity_group=commodity_group)


@st.cache_data(show_spinner=False)
def load_fies(region_code=None):
    return get_fies_data(region_code=region_code)


@st.cache_data(show_spinner=False)
def load_region_names():
    return get_region_names()


@st.cache_data(show_spinner=False)
def load_inflation_frame():
    return calculate_inflation_frame(get_cpi_data())


@st.cache_data(show_spinner=False)
def load_commodity_groups(region_code):
    return get_commodity_groups(region_code)


@st.cache_data(show_spinner=False)
def load_region_geojson():
    """Region boundaries for the map, or None if the file is missing."""
    path = os.path.join(BASE_DIR, "data", "ph_regions.geojson")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_stale_series():
    return find_stale_series(get_cpi_data())


@st.cache_data(show_spinner=False)
def cached_forecast(region_code, commodity_group, horizon):
    series_df = get_cpi_data(region_code=region_code, commodity_group=commodity_group)
    return run_forecasting_pipeline(series_df, horizon)


def stale_months(region_code, commodity_group):
    """Months a series has been unchanged, or 0 if it is moving."""
    stale = load_stale_series()
    hit = stale[(stale["region_code"] == region_code) & (stale["commodity_group"] == commodity_group)]
    return int(hit["flat_months"].iloc[0]) if not hit.empty else 0


def stale_groups(region_code):
    stale = load_stale_series()
    return set(stale.loc[stale["region_code"] == region_code, "commodity_group"])


# -------------------------------------------------------------------- helpers
def fmt_pct(value, signed=False):
    if pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def headline(text):
    """One-sentence takeaway shown under the page title."""
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    st.markdown(f"<div class='headline'>{html}</div>", unsafe_allow_html=True)


def page_header(title, ctx, subtitle=None):
    st.title(title)
    name = ctx.region_name
    st.caption(subtitle or (name if name.endswith(f"({ctx.region})") else f"{name} ({ctx.region})"))


def build_context():
    """Initialise the database, draw the sidebar and return the page context."""
    setup_database()
    region_map = load_region_names()
    coverage = get_data_coverage()

    st.sidebar.markdown("<div class='sidebar-label'>Region</div>", unsafe_allow_html=True)
    region = st.sidebar.selectbox(
        "Region",
        options=list(region_map.keys()),
        format_func=lambda code: f"{code} · {region_map[code]}",
        label_visibility="collapsed",
    )
    first, last, rows = coverage
    st.sidebar.caption(f"PSA CPI {first:%b %Y} – {last:%b %Y} · {rows:,} records")
    return Context(region=region, region_map=region_map, coverage=coverage)
