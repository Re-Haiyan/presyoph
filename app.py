import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics.calculations import (
    STATUS_COLORS,
    annual_to_monthly,
    calculate_inflation_frame,
    calculate_inflation_series,
    calculate_purchasing_power,
    classify_inflation_level,
    compare_to_benchmark,
    income_needed_to_match_2018,
    purchasing_power_change_pct,
    real_value_series,
)
from analytics.forecasting import (
    PROPHET_AVAILABLE,
    TEST_MONTHS,
    add_forecast_inflation,
    prepare_series,
    run_forecasting_pipeline,
)
from database.db_manager import (
    get_commodity_groups,
    get_cpi_data,
    get_data_coverage,
    get_fies_data,
    initialize_db,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLOT_TEMPLATE = "plotly_dark"

st.set_page_config(
    page_title="PresyoPH | Inflation & Purchasing Power Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# Data access (cached so widget interactions do not re-query or re-train)
# ------------------------------------------------------------------------------
@st.cache_resource
def setup_database():
    return initialize_db()


@st.cache_data(show_spinner=False)
def load_cpi(region_code=None, commodity_group=None):
    return get_cpi_data(region_code=region_code, commodity_group=commodity_group)


@st.cache_data(show_spinner=False)
def load_fies(region_code=None):
    return get_fies_data(region_code=region_code)


@st.cache_data(show_spinner=False)
def load_inflation_frame():
    return calculate_inflation_frame(get_cpi_data())


@st.cache_data(show_spinner=False)
def load_commodity_groups(region_code):
    return get_commodity_groups(region_code)


@st.cache_data(show_spinner=False)
def cached_forecast(region_code, commodity_group, horizon):
    series_df = get_cpi_data(region_code=region_code, commodity_group=commodity_group)
    return run_forecasting_pipeline(series_df, horizon)


def metric_card(label, value, sub=None):
    sub_html = f"<div class='metric-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )


def fmt_pct(value, signed=False):
    if pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


setup_database()
fies_all = load_fies()
region_map = dict(zip(fies_all["region_code"], fies_all["region_name"]))
data_first, data_last, data_rows = get_data_coverage()

# ------------------------------------------------------------------------------
# Sidebar: branding, navigation, region selector
# ------------------------------------------------------------------------------
logo_path = os.path.join(BASE_DIR, "assets", "logo.svg")
logo_html = ""
if os.path.exists(logo_path):
    with open(logo_path, "r", encoding="utf-8") as f:
        logo_html = f.read()

st.sidebar.markdown(
    f"""
    <div class='sidebar-brand-container'>
        <div>{logo_html}</div>
        <div class='sidebar-brand-text'>
            <span class='sidebar-brand-title'>PresyoPH</span>
            <span class='sidebar-brand-subtitle'>Price & Inflation Analytics</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("<div class='sidebar-section-label'>WORKSPACE</div>", unsafe_allow_html=True)
PAGES = [
    "Price Change Dashboard",
    "Time-Series Forecasting",
    "Inflation Rate Viewer",
    "Purchasing Power Calculator",
    "About & Methodology",
]
page = st.sidebar.radio("WORKSPACE", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("<div class='sidebar-section-label'>SELECT REGION</div>", unsafe_allow_html=True)
selected_region = st.sidebar.selectbox(
    "Select Region:",
    options=list(region_map.keys()),
    format_func=lambda x: f"{x} - {region_map[x]}",
    label_visibility="collapsed",
)
st.sidebar.caption(
    f"Data: PSA CPI {data_first:%b %Y} – {data_last:%b %Y} · {data_rows:,} records"
)


# ------------------------------------------------------------------------------
# FEATURE 1: PRICE CHANGE DASHBOARD
# ------------------------------------------------------------------------------
def page_dashboard():
    st.title("Price Change Dashboard")
    st.caption(f"Region Scope: {region_map[selected_region]} ({selected_region})")

    df_reg = load_cpi(region_code=selected_region)
    df_ph = load_cpi(region_code="PH")

    # Year-over-year needs 12 prior months, so the first year has no rates.
    first_year = df_reg["date"].dt.year.min()
    available_years = sorted(
        (y for y in df_reg["date"].dt.year.unique() if y > first_year), reverse=True
    )
    selected_year = st.selectbox("Select Benchmark / Ranking Year:", options=available_years, index=0)

    df_reg_all = calculate_inflation_series(df_reg[df_reg["commodity_group"] == "All Items"])
    df_ph_all = calculate_inflation_series(df_ph[df_ph["commodity_group"] == "All Items"])
    latest_reg = df_reg_all.iloc[-1]
    latest_ph = df_ph_all.iloc[-1]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card(f"Latest Regional CPI ({latest_reg['date']:%b %Y})", f"{latest_reg['cpi_value']:.1f}")
    with m2:
        metric_card("Regional Headline Inflation", fmt_pct(latest_reg["yoy_inflation"]))
    with m3:
        metric_card("National Headline Inflation", fmt_pct(latest_ph["yoy_inflation"]))
    with m4:
        gap = latest_reg["yoy_inflation"] - latest_ph["yoy_inflation"]
        metric_card("Regional vs National Gap", f"{gap:+.2f}% pts")

    st.subheader(f"Commodity Group Price Changes in {selected_year}")

    inflation = load_inflation_frame()
    reg_inf = inflation[(inflation["region_code"] == selected_region) & (inflation["commodity_group"] != "All Items")]
    period = reg_inf[reg_inf["date"].dt.year == selected_year]["date"].max()
    snapshot = reg_inf[reg_inf["date"] == period].dropna(subset=["yoy_inflation"]).copy()
    snapshot["Status"] = snapshot["yoy_inflation"].apply(lambda v: classify_inflation_level(v)[0])

    national = inflation[
        (inflation["region_code"] == "PH") & (inflation["date"] == period)
    ].set_index("commodity_group")["yoy_inflation"]
    snapshot["National YoY (%)"] = snapshot["commodity_group"].map(national)
    snapshot["vs National (pts)"] = snapshot["yoy_inflation"] - snapshot["National YoY (%)"]
    rank_df = snapshot.rename(
        columns={"commodity_group": "Commodity Group", "yoy_inflation": "YoY Inflation (%)"}
    ).sort_values("YoY Inflation (%)", ascending=False)

    fig_bar = px.bar(
        rank_df,
        x="YoY Inflation (%)",
        y="Commodity Group",
        orientation="h",
        color="Status",
        color_discrete_map={k: STATUS_COLORS[k] for k in ("Normal", "Increasing", "High")},
        title=f"{len(rank_df)} Commodity Groups YoY Price Change ({period:%B %Y})",
        text_auto=".2f",
    )
    fig_bar.update_layout(yaxis={"categoryorder": "total ascending"}, height=480, template=PLOT_TEMPLATE)
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("Compare each group with the national figure"):
        st.dataframe(
            rank_df[["Commodity Group", "YoY Inflation (%)", "National YoY (%)", "vs National (pts)", "Status"]]
            .style.format({"YoY Inflation (%)": "{:.2f}", "National YoY (%)": "{:.2f}", "vs National (pts)": "{:+.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Historical Headline Inflation Trend (Region vs National)")
    trend_df = (
        df_reg_all[["date", "yoy_inflation"]]
        .merge(df_ph_all[["date", "yoy_inflation"]], on="date", suffixes=("_reg", "_ph"))
        .rename(columns={"yoy_inflation_reg": f"{selected_region} Inflation", "yoy_inflation_ph": "National Inflation"})
        .dropna()
    )
    fig_line = px.line(
        trend_df,
        x="date",
        y=[f"{selected_region} Inflation", "National Inflation"],
        labels={"value": "YoY Inflation Rate (%)", "date": "Date", "variable": "Scope"},
        title=f"Headline Inflation Comparison ({trend_df['date'].min():%Y} – {trend_df['date'].max():%Y})",
    )
    fig_line.update_layout(template=PLOT_TEMPLATE, height=380)
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader(f"Regional Heatmap: Where Prices Are Rising Fastest ({period:%B %Y})")
    st.caption("Year-over-year inflation (%) for every region and commodity group.")
    heat = inflation[(inflation["date"] == period) & (inflation["commodity_group"] != "All Items")]
    pivot = heat.pivot(index="commodity_group", columns="region_code", values="yoy_inflation")
    pivot = pivot[[c for c in region_map if c in pivot.columns]]
    limit = max(abs(pivot.min().min()), abs(pivot.max().max()), 1.0)
    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn_r",
        zmin=-limit,
        zmax=limit,
        aspect="auto",
        text_auto=".1f",
        labels={"color": "YoY %", "x": "Region", "y": "Commodity Group"},
    )
    fig_heat.update_layout(template=PLOT_TEMPLATE, height=520)
    st.plotly_chart(fig_heat, use_container_width=True)


# ------------------------------------------------------------------------------
# FEATURE 2: TIME-SERIES FORECASTING MODULE
# ------------------------------------------------------------------------------
def page_forecasting():
    st.title("Time-Series Forecasting Module")
    st.caption(f"Region Scope: {region_map[selected_region]} ({selected_region})")

    if not PROPHET_AVAILABLE:
        st.warning("Prophet is not installed, so only ARIMA and SARIMA are compared.")

    c1, c2 = st.columns(2)
    with c1:
        selected_commodity = st.selectbox(
            "Select Commodity Group:", options=load_commodity_groups(selected_region)
        )
    with c2:
        horizon = st.slider("Select Forecast Horizon (Months):", min_value=6, max_value=12, value=12)

    cpi_series = load_cpi(region_code=selected_region, commodity_group=selected_commodity)
    series = prepare_series(cpi_series)
    test_start, test_end = series.index[-TEST_MONTHS], series.index[-1]
    train_start, train_end = series.index[0], series.index[-TEST_MONTHS - 1]

    with st.spinner("Training Prophet, ARIMA, and SARIMA models on the held-out test period..."):
        eval_results, best_model, forecast_df = cached_forecast(selected_region, selected_commodity, horizon)

    st.subheader(f"Held-Out Evaluation Results (Test Period: {test_start:%b %Y} – {test_end:%b %Y})")
    st.caption(
        f"Models trained strictly on {train_start:%b %Y} – {train_end:%b %Y} "
        f"and evaluated on the actual {test_start:%b %Y} – {test_end:%b %Y} values."
    )

    eval_table = pd.DataFrame(
        [
            {
                "Model": ("★ " if name == best_model else "") + name,
                "Test RMSE": metrics["rmse"],
                "Test MAE": metrics["mae"],
                "Test MAPE (%)": metrics["mape"],
                "Status": metrics["status"],
            }
            for name, metrics in eval_results.items()
        ]
    )
    st.dataframe(
        eval_table.style.format(
            {"Test RMSE": "{:.4f}", "Test MAE": "{:.4f}", "Test MAPE (%)": "{:.4f}"}, na_rep="N/A"
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.success(f"Selected Best Model: {best_model} (lowest test RMSE on the held-out period)")

    forecast_df = add_forecast_inflation(series, forecast_df)
    end_row = forecast_df.iloc[-1]
    k1, k2, k3 = st.columns(3)
    with k1:
        metric_card(f"Forecast CPI ({end_row['date']:%b %Y})", f"{end_row['forecast_cpi']:.1f}")
    with k2:
        metric_card(
            "Projected YoY Inflation",
            fmt_pct(end_row["forecast_yoy_inflation"]),
            f"{classify_inflation_level(end_row['forecast_yoy_inflation'])[0]} level",
        )
    with k3:
        metric_card(
            "95% Interval (CPI)", f"{end_row['lower_ci']:.1f} – {end_row['upper_ci']:.1f}", f"at {end_row['date']:%b %Y}"
        )

    st.subheader(f"{horizon}-Month Future CPI Forecast ({best_model})")
    fig_fc = go.Figure()
    fig_fc.add_trace(
        go.Scatter(x=series.index, y=series.values, mode="lines+markers", name="Historical CPI",
                   line=dict(color="#0D9488", width=2))
    )
    fig_fc.add_trace(
        go.Scatter(x=forecast_df["date"], y=forecast_df["forecast_cpi"], mode="lines+markers",
                   name=f"Forecast ({best_model})", line=dict(color="#F59E0B", width=2, dash="dash"))
    )
    fig_fc.add_trace(
        go.Scatter(
            x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
            y=pd.concat([forecast_df["upper_ci"], forecast_df["lower_ci"][::-1]]),
            fill="toself", fillcolor="rgba(245, 158, 11, 0.2)",
            line=dict(color="rgba(255,255,255,0)"), name="95% Uncertainty Interval",
        )
    )
    fig_fc.add_vline(
        x=series.index[-1], line_dash="dot", line_color="#94A3B8",
        annotation_text=f"Forecast Cutoff ({series.index[-1]:%b %Y})",
    )
    fig_fc.update_layout(
        title=f"CPI Forecast for {selected_commodity} ({selected_region})", template=PLOT_TEMPLATE, height=420
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    st.subheader("Forecast Data Table")
    display = forecast_df.copy()
    display["date"] = display["date"].dt.strftime("%B %Y")
    display.columns = ["Forecast Month", "Predicted CPI", "Lower 95% Bound", "Upper 95% Bound", "Projected YoY (%)"]
    st.dataframe(
        display.style.format(
            {"Predicted CPI": "{:.2f}", "Lower 95% Bound": "{:.2f}", "Upper 95% Bound": "{:.2f}", "Projected YoY (%)": "{:+.2f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download forecast (CSV)",
        data=forecast_df.to_csv(index=False).encode("utf-8"),
        file_name=f"presyoph_forecast_{selected_region}_{selected_commodity.replace(' ', '_')}.csv",
        mime="text/csv",
    )


# ------------------------------------------------------------------------------
# FEATURE 3: INFLATION RATE VIEWER
# ------------------------------------------------------------------------------
def page_inflation_viewer():
    st.title("Inflation Rate Viewer")
    st.caption(f"Region Scope: {region_map[selected_region]} ({selected_region})")

    selected_commodity = st.selectbox("Select Commodity Group:", options=load_commodity_groups(selected_region))
    df_inf = calculate_inflation_series(load_cpi(region_code=selected_region, commodity_group=selected_commodity))
    valid = df_inf.dropna(subset=["yoy_inflation"])

    latest = df_inf.iloc[-1]
    previous = df_inf.iloc[-2]
    peak = valid.loc[valid["yoy_inflation"].idxmax()]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card(f"Latest YoY Inflation ({latest['date']:%b %Y})", fmt_pct(latest["yoy_inflation"]))
    with m2:
        metric_card("Change in YoY Rate vs Prior Month", f"{latest['yoy_inflation'] - previous['yoy_inflation']:+.2f}% pts")
    with m3:
        metric_card("Highest Recorded YoY", fmt_pct(peak["yoy_inflation"]), f"Peak: {peak['date']:%b %Y}")
    with m4:
        metric_card("Latest MoM Inflation", fmt_pct(latest["mom_inflation"]))

    rate_type = st.radio("Select Inflation Calculation View:", ["Year-over-Year (YoY)", "Month-over-Month (MoM)"], horizontal=True)
    column = "yoy_inflation" if rate_type.startswith("Year") else "mom_inflation"

    fig = px.line(
        df_inf,
        x="date",
        y=column,
        title=f"Historical {rate_type} Inflation Trend — {selected_commodity} ({selected_region})",
        labels={"date": "Date", column: "Inflation Rate (%)"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#94A3B8")
    if column == "yoy_inflation":
        fig.add_hline(y=3.0, line_dash="dot", line_color=STATUS_COLORS["Increasing"], annotation_text="3% (Normal ceiling)")
        fig.add_hline(y=5.0, line_dash="dot", line_color=STATUS_COLORS["High"], annotation_text="5% (High threshold)")
    fig.update_layout(template=PLOT_TEMPLATE, height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "Download series (CSV)",
        data=df_inf.to_csv(index=False).encode("utf-8"),
        file_name=f"presyoph_inflation_{selected_region}_{selected_commodity.replace(' ', '_')}.csv",
        mime="text/csv",
    )


# ------------------------------------------------------------------------------
# FEATURE 4: PURCHASING POWER CALCULATOR
# ------------------------------------------------------------------------------
def page_purchasing_power():
    st.title("Household Purchasing Power Calculator")
    st.caption("Understand how inflation affects your household income and compare it with regional benchmarks.")
    st.caption("Your income is used only for the calculations on this page. It is never stored.")

    income = st.number_input(
        "Enter Monthly Household Income (PHP):", min_value=0.0, max_value=10_000_000.0, value=30000.0, step=1000.0
    )

    cpi_df = load_cpi(region_code=selected_region, commodity_group="All Items")
    latest_row = cpi_df.iloc[-1]
    latest_cpi = latest_row["cpi_value"]

    fies_row = load_fies(region_code=selected_region).iloc[0]
    survey_year = int(fies_row["survey_year"])
    monthly_income_bench = annual_to_monthly(fies_row["avg_annual_income_php_thousands"])
    monthly_expend_bench = annual_to_monthly(fies_row["avg_annual_expenditure_php_thousands"])

    real_income, peso_val = calculate_purchasing_power(income, latest_cpi)
    change_pct = purchasing_power_change_pct(latest_cpi)

    st.markdown("---")
    st.subheader("Purchasing Power Analysis")
    st.caption(
        f"Adjusted using the {region_map[selected_region]} CPI for {latest_row['date']:%B %Y} "
        f"({latest_cpi:.1f}) relative to the 2018 base year."
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Income Equivalent (2018 Pesos)", f"₱{real_income:,.2f}", "CPI-adjusted equivalent value")
    with m2:
        metric_card("Purchasing Power per ₱1.00", f"₱{peso_val:.2f}", "Real value vs 2018 baseline")
    with m3:
        metric_card("Change from 2018 Baseline", f"{change_pct:+.1f}%", "Change in what one peso buys")
    with m4:
        metric_card(
            "Income Needed to Match 2018",
            f"₱{income_needed_to_match_2018(income, latest_cpi):,.0f}",
            "Same buying power as today's income in 2018",
        )

    if income == 0:
        st.info("Enter an income above ₱0 to see the income comparison below.")
        return

    st.subheader("What Your Income Is Worth Over Time")
    st.caption("If your income had stayed the same since 2018, this is its value in 2018 pesos each month.")
    worth = real_value_series(income, cpi_df)
    fig_real = px.line(worth, x="date", y="real_income", labels={"date": "Date", "real_income": "Value in 2018 Pesos (PHP)"})
    fig_real.add_hline(y=income, line_dash="dash", line_color="#94A3B8", annotation_text="Nominal income")
    fig_real.update_layout(template=PLOT_TEMPLATE, height=320)
    st.plotly_chart(fig_real, use_container_width=True)

    st.markdown("---")
    st.subheader("Income & Expenditure Benchmark Comparison")
    st.caption(
        f"Monthly figures compared with the PSA {survey_year} Family Income and Expenditure Survey (FIES) "
        "regional averages. The survey does not reflect income changes since then."
    )

    benchmark = pd.DataFrame(
        [
            {"Category": "Entered Monthly Income", "Amount (PHP)": income, "Type": "User Input"},
            {"Category": "Regional Avg Family Income", "Amount (PHP)": monthly_income_bench, "Type": f"{survey_year} FIES Benchmark"},
            {"Category": "Regional Avg Family Expenditure", "Amount (PHP)": monthly_expend_bench, "Type": f"{survey_year} FIES Benchmark"},
        ]
    )
    fig_bench = px.bar(
        benchmark, x="Amount (PHP)", y="Category", orientation="h", color="Type",
        color_discrete_map={"User Input": "#0D9488", f"{survey_year} FIES Benchmark": "#D97706"},
        text_auto=",.0f",
    )
    fig_bench.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": ["Regional Avg Family Expenditure", "Regional Avg Family Income", "Entered Monthly Income"]},
        xaxis_title="Monthly Amount (PHP)", yaxis_title="", height=280, template=PLOT_TEMPLATE,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig_bench, use_container_width=True)

    vs_income = compare_to_benchmark(income, monthly_income_bench)
    vs_expend = compare_to_benchmark(income, monthly_expend_bench)
    st.info(
        f"**Key Insight:** Your income is **{abs(vs_income):.1f}% {'above' if vs_income >= 0 else 'below'}** "
        f"the {survey_year} average family income and **{abs(vs_expend):.1f}% "
        f"{'above' if vs_expend >= 0 else 'below'}** the average family expenditure for "
        f"**{region_map[selected_region]}**. After inflation since 2018, today's income buys what "
        f"**₱{real_income:,.2f}** bought in 2018."
    )


# ------------------------------------------------------------------------------
# ABOUT & METHODOLOGY
# ------------------------------------------------------------------------------
def page_about():
    st.title("About & Methodology")
    st.markdown(
        f"""
**PresyoPH** turns published Philippine Statistics Authority (PSA) price and income data into an
interactive tool for households, students and researchers, and local planners.

### Data
- **Consumer Price Index (CPI)**: PSA OpenSTAT, monthly, {data_first:%B %Y} – {data_last:%B %Y}, 2018 = 100.
  Covers the Philippines and 17 regions across 13 major commodity groups plus *All Items*
  ({data_rows:,} records).
- **Family Income and Expenditure Survey (FIES) 2023**: average annual family income and expenditure
  for the Philippines and each region, used only as a benchmark.

### Methods
- **Inflation**: year-over-year = CPI(t) / CPI(t−12) − 1; month-over-month = CPI(t) / CPI(t−1) − 1.
- **Inflation levels**: *Normal* ≤ 3%, *Increasing* > 3% to 5%, *High* > 5% (year-over-year).
- **Forecasting**: Prophet, ARIMA(1,1,1) and SARIMA(1,1,1)(1,1,1)₁₂ are trained on all months except the
  last {TEST_MONTHS}, and scored on those months with RMSE, MAE and MAPE. The model with the lowest RMSE is
  refit on the full history and used for the 6–12 month forecast with a 95% interval.
- **Purchasing power**: income × 100 / latest regional CPI, expressed in 2018 pesos.

### Limitations
- The FIES benchmark reflects 2023 incomes and ages as prices change.
- Forecasts extrapolate historical patterns. They cannot anticipate shocks such as supply disruptions
  or policy changes, so treat the interval, not just the central line, as the result.
- Region-level data excludes city-, barangay- and store-level prices.
"""
    )
    st.caption("Developed for Elective 4 (Data Analytics 2), Pangasinan State University – Urdaneta City Campus.")


ROUTES = {
    "Price Change Dashboard": page_dashboard,
    "Time-Series Forecasting": page_forecasting,
    "Inflation Rate Viewer": page_inflation_viewer,
    "Purchasing Power Calculator": page_purchasing_power,
    "About & Methodology": page_about,
}
ROUTES[page]()
