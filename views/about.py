import streamlit as st

from analytics.forecasting import TEST_MONTHS
from views.common import load_stale_series, page_header


def render(ctx):
    first, last, rows = ctx.coverage
    page_header("About & Methodology", ctx, subtitle="Data sources, formulas and limitations")
    st.markdown(
        f"""
**PresyoPH** turns published Philippine Statistics Authority (PSA) price and income data into an
interactive tool for households, students and researchers, and local planners.

### Data
- **Consumer Price Index (CPI)**: PSA OpenSTAT, monthly, {first:%B %Y} – {last:%B %Y}, 2018 = 100.
  Covers the Philippines and 17 regions across 13 major commodity groups plus *All Items* ({rows:,} records).
- **Family Income and Expenditure Survey (FIES) 2023**: average annual family income and expenditure for the
  Philippines and each region, used only as a benchmark.

### Methods
- **Inflation**: year-over-year = CPI(t) / CPI(t−12) − 1; month-over-month = CPI(t) / CPI(t−1) − 1.
- **Inflation levels**: *Normal* ≤ 3%, *Increasing* > 3% to 5%, *High* > 5% (year-over-year).
- **Forecasting**: Prophet, ARIMA(1,1,1) and SARIMA(1,1,1)(1,1,1)₁₂ are trained on all months except the last
  {TEST_MONTHS}, and scored on those months with RMSE, MAE and MAPE. The model with the lowest RMSE is refit on the
  full history and used for the 6–12 month forecast with a 95% interval.
- **Purchasing power**: income × 100 / latest regional CPI, expressed in 2018 pesos.

### Limitations
- The FIES benchmark reflects 2023 incomes and ages as prices change.
- Forecasts extrapolate historical patterns. They cannot anticipate shocks such as supply disruptions or policy
  changes, so read the interval, not just the central line.
- The regional map is schematic, and the data excludes city-, barangay- and store-level prices.
"""
    )
    stale = load_stale_series()
    if not stale.empty:
        groups = ", ".join(sorted(stale["commodity_group"].unique()))
        st.markdown("### Data quality")
        st.warning(
            f"**{len(stale)} series have an unchanged CPI for 6 or more months** ({groups}). This looks like a "
            "stale or carried-forward value in the source data. These series are left out of rankings, maps and "
            "forecasts."
        )
        with st.expander("Show affected series"):
            st.dataframe(stale.rename(columns={"region_code": "Region", "commodity_group": "Commodity group",
                                               "flat_months": "Months unchanged"}),
                         use_container_width=True, hide_index=True)
    st.caption("Developed for Elective 4 (Data Analytics 2), Pangasinan State University – Urdaneta City Campus.")
