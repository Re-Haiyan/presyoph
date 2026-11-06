"""Smoke tests: every page renders without raising, and key behaviours hold."""

import os

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")
MODULES = ["dashboard", "forecasting", "inflation", "purchasing_power", "about"]


def page_script(module_name):
    import importlib

    from views.common import build_context

    ctx = build_context()
    importlib.import_module(f"views.{module_name}").render(ctx)


def run_page(module_name, region=None):
    at = AppTest.from_function(page_script, args=(module_name,), default_timeout=180).run()
    if region:
        at.sidebar.selectbox[0].set_value(region).run()
    return at


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESYOPH_DB", str(tmp_path / "app.db"))


def test_full_app_loads_default_page():
    at = AppTest.from_file(APP, default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "Price Change Dashboard"


@pytest.mark.parametrize("module", MODULES)
def test_page_renders(module):
    at = run_page(module)
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value


@pytest.mark.parametrize("region", ["NCR", "BARMM", "R4A"])
def test_dashboard_for_other_regions(region):
    at = run_page("dashboard", region)
    assert not at.exception, [e.value for e in at.exception]


def test_dashboard_excludes_stale_series_with_notice():
    at = run_page("dashboard")
    text = " ".join(i.value for i in at.info)
    assert "Financial Services" in text


def test_forecast_refused_for_stale_series():
    at = run_page("forecasting")
    at.selectbox[0].set_value("Financial Services").run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("stale" in w.value for w in at.warning)
    assert len(at.metric) == 0  # no forecast metrics were drawn


def test_zero_income_does_not_report_total_loss():
    at = run_page("purchasing_power")
    at.number_input[0].set_value(0.0).run()
    assert not at.exception, [e.value for e in at.exception]
    values = " ".join(m.value + (m.delta or "") for m in at.metric)
    assert "-100" not in values
    assert "₱0.73" in values or "₱0.7" in values
