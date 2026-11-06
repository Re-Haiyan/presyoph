import numpy as np
import pandas as pd
import pytest

from analytics import forecasting as fc


def synthetic(months=104, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(months)
    values = 100 + 0.4 * t + 2 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 0.2, months)
    return pd.DataFrame(
        {"date": pd.date_range("2018-01-01", periods=months, freq="MS"), "cpi_value": values}
    )


def test_split_holds_out_last_months():
    series = fc.prepare_series(synthetic())
    train, test = fc.split_train_test(series)
    assert len(test) == fc.TEST_MONTHS
    assert train.index[-1] == pd.Timestamp("2025-12-01")
    assert test.index[-1] == pd.Timestamp("2026-08-01")


def test_split_rejects_short_series():
    with pytest.raises(ValueError):
        fc.split_train_test(fc.prepare_series(synthetic(months=30)))


def test_prepare_series_fills_gaps_and_duplicates():
    df = synthetic(40)
    df = pd.concat([df.drop(index=10), df.iloc[[5]]])
    series = fc.prepare_series(df)
    assert len(series) == 40
    assert not series.isna().any()


def test_error_metrics():
    m = fc.error_metrics(np.array([100.0, 100.0]), np.array([101.0, 99.0]))
    assert m["rmse"] == pytest.approx(1.0)
    assert m["mae"] == pytest.approx(1.0)
    assert m["mape"] == pytest.approx(1.0)


def test_select_best_model_uses_lowest_rmse_and_ignores_failures():
    results = {
        "Prophet": {"rmse": np.nan, "status": "Failed: x"},
        "ARIMA": {"rmse": 2.0, "status": "Success"},
        "SARIMA": {"rmse": 1.0, "status": "Success"},
    }
    assert fc.select_best_model(results) == "SARIMA"
    assert fc.select_best_model({"ARIMA": {"rmse": np.nan, "status": "Failed"}}) == "ARIMA"


def test_pipeline_end_to_end():
    results, best, forecast = fc.run_forecasting_pipeline(synthetic(), forecast_horizon=6)
    assert set(results) == set(fc.MODEL_NAMES)
    assert best in fc.MODEL_NAMES
    assert results[best]["status"] == "Success"
    assert len(forecast) == 6
    assert forecast["date"].iloc[0] == pd.Timestamp("2026-09-01")
    assert (forecast["lower_ci"] <= forecast["forecast_cpi"]).all()
    assert (forecast["forecast_cpi"] <= forecast["upper_ci"]).all()


def test_forecast_inflation_uses_observed_then_forecast_months():
    history = fc.prepare_series(synthetic())
    forecast = fc.build_forecast(history, "ARIMA", 12)
    out = fc.add_forecast_inflation(history, forecast)
    first = out.iloc[0]
    expected = (first["forecast_cpi"] / history.iloc[-12] - 1) * 100
    assert first["forecast_yoy_inflation"] == pytest.approx(expected)
    assert out["forecast_yoy_inflation"].notna().all()
