import pandas as pd
import streamlit as st

from analytics.calculations import classify_inflation_level
from analytics.forecasting import PROPHET_AVAILABLE, add_forecast_inflation, prepare_series, split_train_test
from analytics.insights import forecast_headline
from ui import charts
from views.common import (
    cached_forecast,
    fmt_pct,
    headline,
    load_commodity_groups,
    load_cpi,
    page_header,
    stale_months,
)


def render(ctx):
    page_header("Time-Series Forecasting", ctx)

    if not PROPHET_AVAILABLE:
        st.warning("Prophet is not installed, so only ARIMA and SARIMA are compared.")

    c1, c2 = st.columns(2)
    with c1:
        commodity = st.selectbox("Commodity group", options=load_commodity_groups(ctx.region))
    with c2:
        horizon = st.slider("Forecast horizon (months)", min_value=6, max_value=12, value=12)

    flat = stale_months(ctx.region, commodity)
    if flat:
        st.warning(
            f"**{commodity}** has had the same CPI for {flat} months in this region. PSA updates this index only "
            "occasionally, so there is no month-to-month movement to learn from and a forecast would only "
            "repeat the flat line. It is not shown; pick another group."
        )
        return

    series = prepare_series(load_cpi(region_code=ctx.region, commodity_group=commodity))
    train, test = split_train_test(series)
    test_start, test_end = test.index[0], test.index[-1]
    train_start, train_end = train.index[0], train.index[-1]

    with st.spinner("Training Prophet, ARIMA and SARIMA on the held-out test period..."):
        results, best, forecast = cached_forecast(ctx.region, commodity, horizon)
    forecast = add_forecast_inflation(series, forecast)
    end = forecast.iloc[-1]

    headline(forecast_headline(best, horizon, end["date"], end["forecast_yoy_inflation"], series.index[-1]))

    k1, k2, k3 = st.columns(3)
    k1.metric(f"Forecast CPI · {end['date']:%b %Y}", f"{end['forecast_cpi']:.1f}",
              f"{end['forecast_cpi'] - series.iloc[-1]:+.1f} vs latest", delta_color="inverse", border=True)
    k2.metric("Projected YoY inflation", fmt_pct(end["forecast_yoy_inflation"]),
              f"{classify_inflation_level(end['forecast_yoy_inflation'])[0]} level", delta_color="off",
              delta_arrow="off", border=True)
    k3.metric("95% interval (CPI)", f"{end['lower_ci']:.1f} – {end['upper_ci']:.1f}", f"at {end['date']:%b %Y}",
              delta_color="off", delta_arrow="off", border=True)

    st.plotly_chart(
        charts.forecast_chart(series, forecast, best, f"{commodity} · {ctx.region}"),
        use_container_width=True, config={"displayModeBar": False})

    tab_models, tab_table = st.tabs(["Model comparison", "Forecast table"])

    with tab_models:
        st.caption(
            f"Trained on {train_start:%b %Y} – {train_end:%b %Y}; tested on the actual "
            f"{test_start:%b %Y} – {test_end:%b %Y} values. The lowest test RMSE wins."
        )
        left, right = st.columns([2, 3])
        with left:
            st.plotly_chart(charts.model_bars(results, best), use_container_width=True, config={"displayModeBar": False})
        with right:
            st.plotly_chart(charts.backtest_chart(series, results, best, len(test)),
                            use_container_width=True, config={"displayModeBar": False})
        table = pd.DataFrame(
            [{"Model": ("★ " if name == best else "") + name, "Test RMSE": m["rmse"], "Test MAE": m["mae"],
              "Test MAPE (%)": m["mape"], "Status": m["status"]} for name, m in results.items()])
        st.dataframe(
            table.style.format({"Test RMSE": "{:.3f}", "Test MAE": "{:.3f}", "Test MAPE (%)": "{:.3f}"}, na_rep="N/A"),
            use_container_width=True, hide_index=True)

    with tab_table:
        display = forecast.copy()
        display["date"] = display["date"].dt.strftime("%B %Y")
        display.columns = ["Month", "Predicted CPI", "Lower 95%", "Upper 95%", "Projected YoY (%)"]
        st.dataframe(
            display.style.format({"Predicted CPI": "{:.2f}", "Lower 95%": "{:.2f}", "Upper 95%": "{:.2f}",
                                  "Projected YoY (%)": "{:+.2f}"}),
            use_container_width=True, hide_index=True)
        st.download_button(
            "Download forecast (CSV)", data=forecast.to_csv(index=False).encode("utf-8"),
            file_name=f"presyoph_forecast_{ctx.region}_{commodity.replace(' ', '_')}.csv", mime="text/csv")
