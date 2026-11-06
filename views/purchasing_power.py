import streamlit as st

from analytics.calculations import (
    annual_to_monthly,
    calculate_purchasing_power,
    compare_to_benchmark,
    future_real_value,
    income_needed_for_same_power,
    income_needed_to_match_2018,
    purchasing_power_change_pct,
    real_value_series,
    whatif_path,
)
from analytics.insights import purchasing_headline, whatif_headline
from ui import charts
from views.common import headline, load_cpi, load_fies, page_header

RATE_MIN, RATE_MAX = -2.0, 20.0


def latest_yoy(cpi_df):
    """Year-over-year inflation (%) in the most recent month of an All Items series."""
    series = cpi_df.sort_values("date").set_index("date")["cpi_value"]
    if len(series) < 13:
        return 0.0
    return float((series.iloc[-1] / series.iloc[-13] - 1.0) * 100.0)


def render(ctx):
    page_header("Purchasing Power", ctx, subtitle="What your income is worth after inflation. Your income is never stored.")

    income = st.number_input(
        "Monthly household income (PHP)", min_value=0.0, max_value=10_000_000.0, value=30000.0, step=1000.0)

    cpi_df = load_cpi(region_code=ctx.region, commodity_group="All Items")
    latest = cpi_df.iloc[-1]
    fies_rows = load_fies(region_code=ctx.region)
    has_benchmark = not fies_rows.empty
    if has_benchmark:
        fies = fies_rows.iloc[0]
        survey_year = int(fies["survey_year"])
        income_bench = annual_to_monthly(fies["avg_annual_income_php_thousands"])
        expend_bench = annual_to_monthly(fies["avg_annual_expenditure_php_thousands"])
        vs_income = compare_to_benchmark(income, income_bench)
        vs_expend = compare_to_benchmark(income, expend_bench)
    else:
        vs_income = None

    real_income, peso = calculate_purchasing_power(income, latest["cpi_value"])
    change = purchasing_power_change_pct(latest["cpi_value"])

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
        st.info("Enter an income above ₱0 to see how it changes over time and compare it with regional benchmarks.")
        return

    tab_time, tab_whatif, tab_bench = st.tabs(["Value over time", "What if?", "Regional benchmark"])

    with tab_time:
        st.caption("If your income had stayed the same since 2018, this is what it would be worth each month, in 2018 pesos.")
        st.plotly_chart(charts.real_value_line(real_value_series(income, cpi_df), income),
                        use_container_width=True, config={"displayModeBar": False})

    with tab_whatif:
        current = latest_yoy(cpi_df)
        default_rate = round(min(max(current, RATE_MIN), RATE_MAX), 1)
        st.caption(f"Pick a yearly inflation rate and a time span. The latest reading for {ctx.region} is "
                   f"**{current:.1f}%**; the Normal ceiling is 3% and the High threshold is 5%.")
        c1, c2, c3 = st.columns(3)
        with c1:
            rate = st.slider("Yearly inflation (%)", RATE_MIN, RATE_MAX, default_rate, 0.1,
                             key=f"whatif_rate_{ctx.region}")
        with c2:
            years = st.slider("Years ahead", 1, 10, 3, key="whatif_years")
        with c3:
            raise_pct = st.slider("Your yearly raise (%)", 0.0, 15.0, 0.0, 0.5, key="whatif_raise",
                                  help="Set above 0 to see whether salary increases keep up with prices.")
        future_real = future_real_value(income, rate, years, raise_pct)
        needed = income_needed_for_same_power(income, rate, years)
        headline(whatif_headline(income, rate, years, raise_pct, future_real, needed))

        m1, m2, m3 = st.columns(3)
        m1.metric("Worth in today's pesos", f"₱{future_real:,.0f}",
                  f"{(future_real / income - 1) * 100:+.1f}% vs today", border=True)
        m2.metric("Needed to stay even", f"₱{needed:,.0f}",
                  f"{(needed / income - 1) * 100:+.1f}% vs today", delta_color="off", border=True)
        m3.metric("Prices after that time", f"×{needed / income:.2f}", f"₱100 becomes ₱{needed / income * 100:,.0f}",
                  delta_color="off", delta_arrow="off", border=True)
        st.plotly_chart(charts.whatif_chart(whatif_path(income, rate, years, raise_pct), income, raise_pct),
                        use_container_width=True, config={"displayModeBar": False})
        st.caption("This is a simple scenario with a steady rate, not a forecast. For a model-based projection of "
                   "prices, see the Time-Series Forecasting page.")

    with tab_bench:
        if not has_benchmark:
            st.info(
                f"No income benchmark is available for {ctx.region_name}: the 2023 Family Income and Expenditure "
                "Survey was taken before this region was created. Choose another region to see the comparison."
            )
        else:
            st.caption(f"Monthly figures from the PSA {survey_year} Family Income and Expenditure Survey. "
                       "They do not reflect income changes since then.")
            st.plotly_chart(charts.benchmark_bars(income, income_bench, expend_bench, survey_year),
                            use_container_width=True, config={"displayModeBar": False})
            st.info(
                f"Your income is **{abs(vs_income):.1f}% {'above' if vs_income >= 0 else 'below'}** the average family "
                f"income and **{abs(vs_expend):.1f}% {'above' if vs_expend >= 0 else 'below'}** the average family "
                f"expenditure in {ctx.region_name}.")
