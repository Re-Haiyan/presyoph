import pandas as pd
import pytest

from analytics.insights import (
    dashboard_headline,
    forecast_headline,
    inflation_headline,
    purchasing_headline,
    whatif_headline,
)
from analytics.quality import find_stale_series, trailing_flat_months


def test_trailing_flat_months():
    assert trailing_flat_months([]) == 0
    assert trailing_flat_months([1, 2, 3]) == 1
    assert trailing_flat_months([1, 2, 3, 3, 3]) == 3
    assert trailing_flat_months([5, 5, 5]) == 3
    assert trailing_flat_months([5, 5, 5, 6]) == 1


def make_cpi():
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    moving = pd.DataFrame({"date": dates, "region_code": "A", "commodity_group": "Food",
                           "cpi_value": [100 + i for i in range(12)]})
    stuck = pd.DataFrame({"date": dates, "region_code": "A", "commodity_group": "Finance",
                          "cpi_value": [100, 101, 102, 103, 104, 105] + [106] * 6})
    brief = pd.DataFrame({"date": dates, "region_code": "B", "commodity_group": "Finance",
                          "cpi_value": [100 + i for i in range(9)] + [109] * 3})
    return pd.concat([moving, stuck, brief])


def test_find_stale_series_flags_only_long_flat_runs():
    stale = find_stale_series(make_cpi(), min_months=6)
    assert stale[["region_code", "commodity_group"]].values.tolist() == [["A", "Finance"]]
    assert stale["flat_months"].iloc[0] == 6


def test_find_stale_series_empty_result_keeps_columns():
    stale = find_stale_series(make_cpi(), min_months=50)
    assert stale.empty
    assert list(stale.columns) == ["region_code", "commodity_group", "flat_months"]


def rank():
    return pd.DataFrame({
        "Commodity Group": ["Transport", "Food"],
        "YoY Inflation (%)": [13.5, 4.0],
        "National YoY (%)": [10.0, 4.0],
    })


def test_dashboard_headline_mentions_leader_gap_and_high_count():
    text = dashboard_headline(rank(), "NCR", pd.Timestamp("2026-08-01"))
    assert "Transport" in text and "13.5%" in text
    assert "3.5 points above the national rate" in text
    assert "1 of 2 groups" in text


def test_dashboard_headline_national_has_no_gap_and_handles_empty():
    assert "national rate" not in dashboard_headline(rank(), "Philippines", pd.Timestamp("2026-08-01"), True)
    assert "No year-over-year" in dashboard_headline(rank().iloc[0:0], "X", pd.Timestamp("2026-08-01"))


def test_whatif_headline_covers_loss_gain_and_raise():
    no_raise = whatif_headline(30000, 5.0, 2, 0.0, 27210.7, 33075.0)
    assert "5% a year for 2 years" in no_raise and "9.3% loss" in no_raise and "₱33,075" in no_raise
    assert "gain" in whatif_headline(30000, -2.0, 1, 0.0, 30612.0, 29400.0)
    with_raise = whatif_headline(30000, 5.0, 1, 8.0, 30857.0, 31500.0)
    assert "8% yearly raise" in with_raise and "a gain of 2.9%" in with_raise
    assert "1 year:" in with_raise


def test_purchasing_headline_without_benchmark():
    assert "average family income" not in purchasing_headline(0.72, "NIR", 30000, None)


def test_other_headlines():
    date = pd.Timestamp("2026-08-01")
    assert "down from" in inflation_headline(6.1, 6.2, "All Items", "PH", date)
    assert "Not enough history" in inflation_headline(float("nan"), 1.0, "All Items", "PH", date)
    assert "SARIMA" in forecast_headline("SARIMA", 12, date, 3.4, date)
    assert "₱0.73" in purchasing_headline(0.73, "PH", 0, 0.0)
    assert "above" in purchasing_headline(0.73, "PH", 30000, 5.0)
