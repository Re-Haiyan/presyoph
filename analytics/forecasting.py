"""Prophet / ARIMA / SARIMA forecasting with held-out evaluation.

Evaluation protocol (see the project proposal): every model is trained on the months up to
``TRAIN_END`` (December 2025) and scored on every later month in the data, so the held-out
period grows as PSA publishes new months. The model with the lowest test RMSE is refit on the
full history and used for the forecast.
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the environment
    PROPHET_AVAILABLE = False

TRAIN_END = pd.Timestamp("2025-12-01")  # last month used for training; later months are the test set
MIN_TRAIN_MONTHS = 24
MODEL_NAMES = ("Prophet", "ARIMA", "SARIMA")
ARIMA_ORDER = (1, 1, 1)
SARIMA_SEASONAL_ORDER = (1, 1, 1, 12)
INTERVAL_WIDTH = 0.95


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
def prepare_series(cpi_series_df):
    """Sort, de-duplicate and gap-fill a CPI series on a month-start index."""
    df = cpi_series_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last")
    series = df.set_index("date")["cpi_value"].astype(float).asfreq("MS")
    # Gaps would break the seasonal model, so bridge them linearly.
    return series.interpolate(limit_direction="both")


def split_train_test(series, train_end=TRAIN_END):
    """Train on months up to ``train_end``; hold out every later month."""
    train = series[series.index <= train_end]
    test = series[series.index > train_end]
    if len(train) < MIN_TRAIN_MONTHS or len(test) < 1:
        raise ValueError(
            f"Need at least {MIN_TRAIN_MONTHS} months up to {train_end:%b %Y} and at least one later month; "
            f"got {len(train)} training and {len(test)} test months."
        )
    return train, test


# ---------------------------------------------------------------------------
# Model fitting. Each function returns (forecast, lower, upper) as numpy arrays.
# ---------------------------------------------------------------------------
def _prophet_forecast(series, steps):
    frame = series.reset_index()
    frame.columns = ["ds", "y"]
    model = Prophet(interval_width=INTERVAL_WIDTH, yearly_seasonality=True)
    model.fit(frame)
    future = model.make_future_dataframe(periods=steps, freq="MS")
    out = model.predict(future).tail(steps)
    return out["yhat"].values, out["yhat_lower"].values, out["yhat_upper"].values


def _statsmodels_forecast(result, steps):
    forecast = result.get_forecast(steps=steps)
    ci = forecast.conf_int(alpha=1 - INTERVAL_WIDTH)
    return forecast.predicted_mean.values, ci.iloc[:, 0].values, ci.iloc[:, 1].values


def _arima_forecast(series, steps):
    return _statsmodels_forecast(ARIMA(series, order=ARIMA_ORDER).fit(), steps)


def _sarima_forecast(series, steps):
    model = SARIMAX(series, order=ARIMA_ORDER, seasonal_order=SARIMA_SEASONAL_ORDER)
    return _statsmodels_forecast(model.fit(disp=False), steps)


_FORECASTERS = {
    "Prophet": _prophet_forecast,
    "ARIMA": _arima_forecast,
    "SARIMA": _sarima_forecast,
}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def error_metrics(actual, predicted):
    """RMSE, MAE (index points) and MAPE (%) of a forecast."""
    return {
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "mape": float(mean_absolute_percentage_error(actual, predicted) * 100.0),
    }


def evaluate_models(train, test):
    """Fit every model on ``train`` and score it on ``test``."""
    results = {}
    for name in MODEL_NAMES:
        if name == "Prophet" and not PROPHET_AVAILABLE:
            results[name] = _failed("Library Not Available")
            continue
        try:
            predicted, _, _ = _FORECASTERS[name](train, len(test))
            results[name] = {
                **error_metrics(test.values, predicted),
                "status": "Success",
                "predictions": np.asarray(predicted, dtype=float),
            }
        except Exception as exc:  # a failing model must not break the others
            results[name] = _failed(f"Failed: {exc}")
    return results


def _failed(status):
    return {"rmse": np.nan, "mae": np.nan, "mape": np.nan, "status": status, "predictions": None}


def select_best_model(eval_results):
    """Name of the successful model with the lowest RMSE (ARIMA if none succeeded)."""
    valid = {k: v for k, v in eval_results.items() if v["status"] == "Success"}
    if not valid:
        return "ARIMA"
    return min(valid, key=lambda k: valid[k]["rmse"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_forecast(series, model_name, horizon):
    """Refit ``model_name`` on the full ``series`` and project ``horizon`` months."""
    if model_name == "Prophet" and not PROPHET_AVAILABLE:
        model_name = "ARIMA"
    predicted, lower, upper = _FORECASTERS[model_name](series, horizon)
    dates = pd.date_range(series.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
    return pd.DataFrame(
        {"date": dates, "forecast_cpi": predicted, "lower_ci": lower, "upper_ci": upper}
    )


def add_forecast_inflation(history, forecast_df):
    """Append the year-over-year inflation implied by the forecast.

    ``history`` is the observed monthly CPI series; the first twelve forecast months
    are compared against the matching observed months, later ones against earlier
    forecast months.
    """
    combined = pd.concat([history, forecast_df.set_index("date")["forecast_cpi"]])
    yoy = (combined / combined.shift(12) - 1.0) * 100.0
    out = forecast_df.copy()
    out["forecast_yoy_inflation"] = yoy.reindex(out["date"]).values
    return out


def run_forecasting_pipeline(cpi_series_df, forecast_horizon=12, train_end=TRAIN_END):
    """Evaluate Prophet, ARIMA and SARIMA, then forecast with the best one.

    Returns ``(eval_results, best_model_name, forecast_df)``.
    """
    series = prepare_series(cpi_series_df)
    train, test = split_train_test(series, train_end)
    eval_results = evaluate_models(train, test)
    best = select_best_model(eval_results)
    forecast_df = build_forecast(series, best, forecast_horizon)
    return eval_results, best, forecast_df
