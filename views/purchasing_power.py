import streamlit as st

from analytics.calculations import (
    annual_to_monthly,
    calculate_purchasing_power,
    compare_to_benchmark,
    income_needed_to_match_2018,
    purchasing_power_change_pct,
    real_value_series,
)
from analytics.insights import purchasing_headline
from ui import charts
from views.common import headline, load_cpi, load_fies, page_header


def render(ctx):
    page_header("Purchasing Power", ctx, subtitle="What your income is worth after inflation. Your income is never stored.")

    income = st.number_input(
        "Monthly household income (PHP)", min_value=0.0, max_value=10_000_000.0, value=30000.0, step=1000.0)

    cpi_df = load_cpi(region_code=ctx.region, commodity_group="All Items")
    latest = cpi_df.iloc[-1]
    fies = load_fies(region_code=ctx.region).iloc[0]
    survey_year = int(fies["survey_year"])
    income_bench = annual_to_monthly(fies["avg_annual_income_php_thousands"])
    expend_bench = annual_to_monthly(fies["avg_annual_expenditure_php_thousands"])

    real_income, peso = calculate_purchasing_power(income, latest["cpi_value"])
    change = purchasing_power_change_pct(latest["cpi_value"])
    vs_income = compare_to_benchmark(income, income_bench)
    vs_expend = compare_to_benchmark(income, expend_bench)

    headline(purchasing_headline(peso, ctx.region_name, income, vs_income))

    left, right = st.columns([1, 2], gap="large")
    with left:
        st.plotly_chart(charts.peso_waffle(peso), use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Each square is one centavo. Filled squares show what ₱1.00 still buys compared with 2018 "
                   f"(CPI {latest['cpi_value']:.1f}, {latest['date']:%B %Y}).")
    with right:
        a, b = st.columns(2)
        a.metric("₱1.00 today equals", f"₱{peso:.2f}", f"{change:+.1f}% vs 2018", border=True)
        b.metric("Your income in 2018 pesos", f"₱{real_income:,.0f}", border=True)
        c, d = st.columns(2)
        c.metric("Income needed to match 2018", f"₱{income_needed_to_match_2018(income, latest['cpi_value']):,.0f}",
                 "same buying power as your income in 2018", delta_color="off", delta_arrow="off", border=True)
        d.metric("CPI", f"{latest['cpi_value']:.1f}", "2018 = 100", delta_color="off", delta_arrow="off", border=True)

    if income == 0:
        st.info("Enter an income above ₱0 to compare it with regional benchmarks.")
        return

    tab_time, tab_bench = st.tabs(["Value over time", "Regional benchmark"])
    with tab_time:
        st.caption("If your income had stayed the same since 2018, this is what it would be worth each month, in 2018 pesos.")
        st.plotly_chart(charts.real_value_line(real_value_series(income, cpi_df), income),
                        use_container_width=True, config={"displayModeBar": False})
    with tab_bench:
        st.caption(f"Monthly figures from the PSA {survey_year} Family Income and Expenditure Survey. "
                   "They do not reflect income changes since then.")
        st.plotly_chart(charts.benchmark_bars(income, income_bench, expend_bench, survey_year),
                        use_container_width=True, config={"displayModeBar": False})
        st.info(
            f"Your income is **{abs(vs_income):.1f}% {'above' if vs_income >= 0 else 'below'}** the average family "
            f"income and **{abs(vs_expend):.1f}% {'above' if vs_expend >= 0 else 'below'}** the average family "
            f"expenditure in {ctx.region_name}.")
