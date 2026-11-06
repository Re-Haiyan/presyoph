import numpy as np
import pandas as pd
import pytest

from analytics.calculations import (
    annual_to_monthly,
    calculate_inflation_frame,
    calculate_inflation_series,
    calculate_purchasing_power,
    classify_inflation_level,
    compare_to_benchmark,
    future_real_value,
    income_needed_for_same_power,
    income_needed_to_match_2018,
    purchasing_power_change_pct,
    real_value_series,
    whatif_path,
)


def make_series(values, start="2020-01-01"):
    return pd.DataFrame(
        {"date": pd.date_range(start, periods=len(values), freq="MS"), "cpi_value": values}
    )


def test_inflation_series_mom_and_yoy():
    df = make_series([100.0 + i for i in range(14)])
    out = calculate_inflation_series(df)
    assert out.loc[1, "mom_inflation"] == pytest.approx(1.0)
    assert np.isnan(out.loc[11, "yoy_inflation"])
    assert out.loc[12, "yoy_inflation"] == pytest.approx(12.0)


def test_inflation_series_sorts_by_date():
    df = make_series([100.0, 110.0, 121.0]).iloc[::-1]
    out = calculate_inflation_series(df)
    assert out["mom_inflation"].iloc[1] == pytest.approx(10.0)


def test_inflation_frame_does_not_mix_series():
    a = make_series([100.0] * 13).assign(region_code="A", commodity_group="x")
    b = make_series([200.0] * 12 + [400.0]).assign(region_code="B", commodity_group="x")
    out = calculate_inflation_frame(pd.concat([a, b]))
    last = out[out["date"] == out["date"].max()].set_index("region_code")
    assert last.loc["A", "yoy_inflation"] == pytest.approx(0.0)
    assert last.loc["B", "yoy_inflation"] == pytest.approx(100.0)


@pytest.mark.parametrize(
    "value, label",
    [(-1.0, "Normal"), (3.0, "Normal"), (3.01, "Increasing"), (5.0, "Increasing"),
     (5.01, "High"), (np.nan, "N/A"), (None, "N/A")],
)
def test_classification_thresholds(value, label):
    assert classify_inflation_level(value)[0] == label


def test_purchasing_power_basic():
    real, peso = calculate_purchasing_power(30000, 125.0)
    assert real == pytest.approx(24000.0)
    assert peso == pytest.approx(0.8)


def test_purchasing_power_zero_income_keeps_peso_value():
    real, peso = calculate_purchasing_power(0, 125.0)
    assert real == 0.0
    assert peso == pytest.approx(0.8)


@pytest.mark.parametrize("cpi", [0, -5, None, np.nan])
def test_purchasing_power_invalid_cpi(cpi):
    assert calculate_purchasing_power(1000, cpi) == (0.0, 0.0)


def test_purchasing_power_large_income():
    real, _ = calculate_purchasing_power(1_000_000, 100.0)
    assert real == pytest.approx(1_000_000)


def test_change_pct_is_signed():
    assert purchasing_power_change_pct(125.0) == pytest.approx(-20.0)
    assert purchasing_power_change_pct(80.0) == pytest.approx(25.0)
    assert purchasing_power_change_pct(0) == 0.0


def test_income_needed_to_match_2018():
    assert income_needed_to_match_2018(20000, 125.0) == pytest.approx(25000.0)
    assert income_needed_to_match_2018(0, 125.0) == 0.0


def test_real_value_series():
    out = real_value_series(1000, make_series([100.0, 200.0]))
    assert out["real_income"].tolist() == pytest.approx([1000.0, 500.0])


def test_future_real_value_and_income_needed():
    assert income_needed_for_same_power(30000, 5.0, 2) == pytest.approx(33075.0)
    assert future_real_value(30000, 5.0, 2) == pytest.approx(30000 / 1.1025)
    assert future_real_value(30000, 5.0, 0) == pytest.approx(30000.0)          # no time, no change
    assert future_real_value(30000, 0.0, 10) == pytest.approx(30000.0)         # no inflation, no change
    assert future_real_value(30000, 5.0, 3, raise_pct=5.0) == pytest.approx(30000.0)  # raise = inflation
    assert future_real_value(30000, 5.0, 3, raise_pct=8.0) > 30000                    # raise beats inflation
    assert future_real_value(30000, -2.0, 1) > 30000                                  # deflation helps


def test_whatif_guards_invalid_input():
    assert future_real_value(0, 5.0, 3) == 0.0
    assert future_real_value(None, 5.0, 3) == 0.0
    assert income_needed_for_same_power(-5, 5.0, 3) == 0.0
    with pytest.raises(ValueError):
        future_real_value(1000, -100.0, 1)


def test_whatif_path_shape_and_endpoints():
    path = whatif_path(1000, 6.0, 2, raise_pct=0.0)
    assert len(path) == 25 and path["month"].iloc[0] == 0 and path["years"].iloc[-1] == pytest.approx(2.0)
    assert path["real"].iloc[0] == pytest.approx(1000.0)
    assert path["real"].iloc[-1] == pytest.approx(future_real_value(1000, 6.0, 2))
    assert path["needed"].iloc[-1] == pytest.approx(income_needed_for_same_power(1000, 6.0, 2))
    assert path["real"].is_monotonic_decreasing


def test_benchmark_helpers():
    assert annual_to_monthly(120.0) == pytest.approx(10000.0)
    assert compare_to_benchmark(15000, 10000) == pytest.approx(50.0)
    assert compare_to_benchmark(5000, 10000) == pytest.approx(-50.0)
    assert compare_to_benchmark(5000, 0) == 0.0
