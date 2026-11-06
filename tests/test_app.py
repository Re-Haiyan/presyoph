"""Smoke tests: every page of the Streamlit app renders without raising."""

import os

import pytest
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
PAGES = [
    "Price Change Dashboard",
    "Time-Series Forecasting",
    "Inflation Rate Viewer",
    "Purchasing Power Calculator",
    "About & Methodology",
]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESYOPH_DB", str(tmp_path / "app.db"))


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value


def test_zero_income_does_not_report_total_loss():
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("Purchasing Power Calculator").run()
    at.number_input[0].set_value(0.0).run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "-100" not in html
