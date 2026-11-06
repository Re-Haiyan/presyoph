import streamlit as st

from analytics.calculations import calculate_inflation_series
from analytics.insights import inflation_headline
from ui import charts
from views.common import fmt_pct, headline, load_commodity_groups, load_cpi, page_header, stale_months


def render(ctx):
    page_header("Inflation Rate Viewer", ctx)

    commodity = st.selectbox("Commodity group", options=load_commodity_groups(ctx.region))
    df = calculate_inflation_series(load_cpi(region_code=ctx.region, commodity_group=commodity))
    valid = df.dropna(subset=["yoy_inflation"])
    latest, previous = df.iloc[-1], df.iloc[-2]
    peak = valid.loc[valid["yoy_inflation"].idxmax()]

    flat = stale_months(ctx.region, commodity)
    if flat:
        st.info(f"The CPI for **{commodity}** has not changed for {flat} months in this region. PSA updates this "
                "index only occasionally, so recent inflation readings of 0% mean no published change, not "
                "necessarily stable prices.")

    headline(inflation_headline(latest["yoy_inflation"], previous["yoy_inflation"], commodity,
                                ctx.region_name, latest["date"]))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"YoY inflation · {latest['date']:%b %Y}", fmt_pct(latest["yoy_inflation"]),
              f"{latest['yoy_inflation'] - previous['yoy_inflation']:+.2f} pts MoM",
              delta_color="inverse", border=True)
    k2.metric("Month-over-month", fmt_pct(latest["mom_inflation"]), border=True)
    k3.metric("Highest YoY on record", fmt_pct(peak["yoy_inflation"]), f"{peak['date']:%b %Y}", delta_color="off",
              delta_arrow="off", border=True)
    k4.metric("Latest CPI", f"{latest['cpi_value']:.1f}", "2018 = 100", delta_color="off", delta_arrow="off",
              border=True)

    tab_trend, tab_season = st.tabs(["Trend", "Seasonality"])
    with tab_trend:
        view = st.radio("Rate", ["Year-over-year", "Month-over-month"], horizontal=True, label_visibility="collapsed")
        column = "yoy_inflation" if view.startswith("Year") else "mom_inflation"
        st.plotly_chart(
            charts.inflation_line(df, column, f"{view} inflation · {commodity} · {ctx.region}",
                                  show_bands=column == "yoy_inflation"),
            use_container_width=True, config={"displayModeBar": False})
    with tab_season:
        st.caption("Each cell is that month's price change from the month before. Recurring warm columns show seasonal patterns.")
        st.plotly_chart(charts.month_year_calendar(df), use_container_width=True, config={"displayModeBar": False})

    st.download_button(
        "Download series (CSV)", data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"presyoph_inflation_{ctx.region}_{commodity.replace(' ', '_')}.csv", mime="text/csv")
