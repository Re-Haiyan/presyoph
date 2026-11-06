import streamlit as st

from analytics.forecasting import TRAIN_END
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
  Covers the Philippines and {len(ctx.region_map) - 1} regions, including the Negros Island Region, across 13 major
  commodity groups plus *All Items* ({rows:,} records). The file was checked against PSA's official table and
  can be refreshed with `scripts/update_cpi_from_psa.py`.
- **Family Income and Expenditure Survey (FIES) 2023**: average annual family income and expenditure for the
  Philippines and each region, used only as a benchmark.

### Methods
- **Inflation**: year-over-year = CPI(t) / CPI(t−12) − 1; month-over-month = CPI(t) / CPI(t−1) − 1.
- **Inflation levels**: *Normal* ≤ 3%, *Increasing* > 3% to 5%, *High* > 5% (year-over-year).
- **Forecasting**: Prophet, ARIMA(1,1,1) and SARIMA(1,1,1)(1,1,1)₁₂ are trained on the months up to
  {TRAIN_END:%B %Y} and scored on every later month with RMSE, MAE and MAPE. The model with the lowest RMSE is
  refit on the full history and used for the 6–12 month forecast with a 95% interval.
- **Purchasing power**: income × 100 / latest regional CPI, expressed in 2018 pesos. The *what-if* tool applies a
  chosen yearly inflation rate to that income and shows its future value in today's pesos.

### Limitations
- The FIES benchmark reflects 2023 incomes and ages as prices change. The 2023 survey predates the Negros Island
  Region, so that region has no income benchmark, and the benchmarks for Regions VI and VII still include Negros.
- Forecasts extrapolate historical patterns. They cannot anticipate shocks such as supply disruptions or policy
  changes, so read the interval, not just the central line.
- Map boundaries are simplified for speed. The data excludes city-, barangay- and store-level prices.
"""
    )
    stale = load_stale_series()
    if not stale.empty:
        groups = ", ".join(sorted(stale["commodity_group"].unique()))
        st.markdown("### Data quality")
        st.info(
            f"**{len(stale)} series have had an unchanged CPI for 6 or more months** ({groups}). This matches "
            "PSA's own table: its national Financial Services index has had only three values since 2018 "
            "(100.0, then 143.3 from April 2021, then 142.4 from January 2024), so it is updated only "
            "occasionally. With no month-to-month movement there is nothing to rank or forecast, so these series "
            "are left out of rankings, maps and forecasts."
        )
        with st.expander("Show affected series"):
            st.dataframe(stale.rename(columns={"region_code": "Region", "commodity_group": "Commodity group",
                                               "flat_months": "Months unchanged"}),
                         use_container_width=True, hide_index=True)
    st.caption("Developed for Elective 4 (Data Analytics 2), Pangasinan State University – Urdaneta City Campus.")
