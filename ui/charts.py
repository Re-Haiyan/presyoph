"""Plotly figures for PresyoPH.

Every figure is theme-neutral: transparent backgrounds, soft grid lines and a small,
consistent palette, so the charts read well in both Streamlit's light and dark themes.
"""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics.calculations import STATUS_COLORS

ACCENT = "#0D9488"
NEUTRAL = "#94A3B8"
AMBER = "#D97706"
RED = "#DC2626"
GRID = "rgba(128, 128, 128, 0.18)"
MODEL_COLORS = {"Prophet": "#8B5CF6", "ARIMA": "#3B82F6", "SARIMA": ACCENT}

# Diverging scale with a neutral midpoint that works on light and dark backgrounds.
DIVERGING = [[0.0, "#0F766E"], [0.5, "#E2E8F0"], [1.0, "#B91C1C"]]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Schematic tile map: (column, row) of each region, roughly following geography.
TILE_POSITIONS = {
    "R2": (2, 0),
    "R1": (0, 1), "CAR": (1, 1),
    "R3": (1, 2), "NCR": (2, 2),
    "R4A": (2, 3), "R5": (3, 3),
    "MIMAROPA": (1, 4),
    "R6": (1, 5), "R7": (2, 5), "R8": (3, 5),
    "R9": (0, 7), "R10": (1, 7), "R13": (2, 7),
    "BARMM": (0, 8), "R12": (1, 8), "R11": (2, 8),
}


def short_label(text, limit=34):
    return text if len(text) <= limit else text[: limit - 1].rstrip(" ,") + "…"


def style(fig, height=None, legend=True):
    """Apply the shared minimal look."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=36, b=8),
        font=dict(size=13),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, showline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False)
    if height:
        fig.update_layout(height=height)
    return fig


def _band_shapes(fig, top, **kw):
    """Shade the Increasing (3-5%) and High (>5%) inflation bands."""
    fig.add_hrect(y0=3, y1=5, fillcolor=AMBER, opacity=0.08, line_width=0, layer="below", **kw)
    fig.add_hrect(y0=5, y1=max(top, 5.5), fillcolor=RED, opacity=0.07, line_width=0, layer="below", **kw)


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
def dumbbell(rank_df, region_label, show_national=True):
    """Region vs national YoY inflation for each commodity group."""
    df = rank_df.sort_values("YoY Inflation (%)", ascending=True).reset_index(drop=True)
    labels = [
        f"<span style='color:{STATUS_COLORS[s]}'>●</span> {short_label(g)}"
        for g, s in zip(df["Commodity Group"], df["Status"])
    ]
    fig = go.Figure()
    if show_national:
        xs, ys = [], []
        for i, row in df.iterrows():
            xs += [row["YoY Inflation (%)"], row["National YoY (%)"], None]
            ys += [labels[i], labels[i], None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=NEUTRAL, width=2),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=df["National YoY (%)"], y=labels, mode="markers", name="Philippines",
            marker=dict(color="rgba(0,0,0,0)", size=11, line=dict(color=NEUTRAL, width=2)),
            customdata=df["Commodity Group"],
            hovertemplate="%{customdata}<br>National: %{x:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=df["YoY Inflation (%)"], y=labels, mode="markers+text", name=region_label,
        marker=dict(color=ACCENT, size=11), text=[f"{v:.1f}%" for v in df["YoY Inflation (%)"]],
        textposition="top center", textfont=dict(size=11), cliponaxis=False,
        customdata=df["Commodity Group"],
        hovertemplate="%{customdata}<br>" + region_label + ": %{x:.2f}%<extra></extra>"))
    for x in (3, 5):
        fig.add_vline(x=x, line_dash="dot", line_color=GRID, line_width=1)
    style(fig, height=max(320, 36 * len(df) + 90), legend=show_national)
    fig.update_xaxes(title="Year-over-year inflation (%)")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    return fig


def heatmap(pivot, title=None):
    """Region × commodity heatmap with a zero-centred diverging scale."""
    z = pivot.values.astype(float)
    limit = max(np.nanmax(np.abs(z)) if np.isfinite(z).any() else 1.0, 1.0)
    text = np.where(np.isnan(z), "", np.char.mod("%.1f", np.nan_to_num(z)))
    fig = go.Figure(go.Heatmap(
        z=z, x=list(pivot.columns), y=[short_label(g, 30) for g in pivot.index],
        colorscale=DIVERGING, zmid=0, zmin=-limit, zmax=limit, xgap=2, ygap=2,
        text=text, texttemplate="%{text}", textfont=dict(size=11),
        hoverongaps=False, hovertemplate="%{y}<br>%{x}: %{z:.2f}%<extra></extra>",
        colorbar=dict(title="YoY %", thickness=10, len=0.8)))
    style(fig, height=max(360, 30 * len(pivot) + 90), legend=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(side="top", gridcolor="rgba(0,0,0,0)")
    if title:
        fig.update_layout(title_text=title)
    return fig


def tile_map(values, names, title=None):
    """Schematic tile map of regions coloured by inflation."""
    cols = max(c for c, _ in TILE_POSITIONS.values()) + 1
    rows = max(r for _, r in TILE_POSITIONS.values()) + 1
    z = np.full((rows, cols), np.nan)
    text = np.full((rows, cols), "", dtype=object)
    hover = np.full((rows, cols), "", dtype=object)
    for code, (c, r) in TILE_POSITIONS.items():
        value = values.get(code)
        if value is None or pd.isna(value):
            continue
        z[r, c] = value
        text[r, c] = f"{code}<br>{value:.1f}%"
        hover[r, c] = f"{names.get(code, code)}<br>{value:.2f}% YoY"
    limit = max(np.nanmax(np.abs(z)) if np.isfinite(z).any() else 1.0, 1.0)
    fig = go.Figure(go.Heatmap(
        z=z, text=text, texttemplate="%{text}", customdata=hover, hovertemplate="%{customdata}<extra></extra>",
        colorscale=DIVERGING, zmid=0, zmin=-limit, zmax=limit, xgap=4, ygap=4, hoverongaps=False,
        textfont=dict(size=12), colorbar=dict(title="YoY %", thickness=10, len=0.7)))
    style(fig, height=560, legend=False)
    fig.update_yaxes(autorange="reversed", visible=False)
    fig.update_xaxes(visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=36 if title else 8, b=0))
    if title:
        fig.update_layout(title_text=title)
    return fig


def trend_lines(df, region_label):
    """Headline YoY inflation, region vs national, with threshold bands."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["national"], name="Philippines",
                             line=dict(color=NEUTRAL, width=2)))
    if region_label != "Philippines":
        fig.add_trace(go.Scatter(x=df["date"], y=df["region"], name=region_label,
                                 line=dict(color=ACCENT, width=3)))
    _band_shapes(fig, top=float(np.nanmax(df[["region", "national"]].values)) + 1)
    style(fig, height=340)
    fig.update_yaxes(title="YoY inflation (%)")
    fig.update_layout(hovermode="x unified")
    return fig


def small_multiples(frame, groups, columns=4):
    """One mini YoY chart per commodity group, each on its own scale."""
    rows = math.ceil(len(groups) / columns)
    fig = make_subplots(rows=rows, cols=columns, subplot_titles=[short_label(g, 26) for g in groups],
                        horizontal_spacing=0.05, vertical_spacing=0.12)
    for i, group in enumerate(groups):
        r, c = i // columns + 1, i % columns + 1
        sub = frame[frame["commodity_group"] == group].dropna(subset=["yoy_inflation"])
        if sub.empty:
            continue
        lo, hi = float(sub["yoy_inflation"].min()), float(sub["yoy_inflation"].max())
        pad = max((hi - lo) * 0.1, 0.5)
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["yoy_inflation"], mode="lines",
                                 line=dict(color=ACCENT, width=1.8), showlegend=False,
                                 hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>"), row=r, col=c)
        fig.add_hrect(y0=3, y1=5, fillcolor=AMBER, opacity=0.10, line_width=0, row=r, col=c)
        fig.add_hrect(y0=5, y1=max(hi + pad, 5.5) + 50, fillcolor=RED, opacity=0.08, line_width=0, row=r, col=c)
        fig.update_yaxes(range=[lo - pad, hi + pad], row=r, col=c, tickfont=dict(size=10))
        fig.update_xaxes(tickfont=dict(size=10), row=r, col=c)
    style(fig, height=230 * rows, legend=False)
    fig.update_annotations(font_size=12)
    return fig


# ----------------------------------------------------------------------------
# Forecasting
# ----------------------------------------------------------------------------
def forecast_chart(series, forecast_df, best_model, title, years=5):
    """History, forecast and 95% interval."""
    recent = series[series.index >= series.index[-1] - pd.DateOffset(years=years)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
        y=pd.concat([forecast_df["upper_ci"], forecast_df["lower_ci"][::-1]]),
        fill="toself", fillcolor="rgba(217, 119, 6, 0.18)", line=dict(color="rgba(0,0,0,0)"),
        name="95% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=recent.index, y=recent.values, name="Observed CPI",
                             line=dict(color=ACCENT, width=2.5)))
    fig.add_trace(go.Scatter(x=forecast_df["date"], y=forecast_df["forecast_cpi"], name=f"Forecast ({best_model})",
                             line=dict(color=AMBER, width=2.5, dash="dash"), mode="lines+markers",
                             marker=dict(size=5)))
    fig.add_vline(x=series.index[-1], line_dash="dot", line_color=NEUTRAL)
    fig.add_annotation(x=series.index[-1], y=1, yref="paper", text=f"Last reading: {series.index[-1]:%b %Y}",
                       showarrow=False, xanchor="right", yanchor="top", font=dict(size=11, color=NEUTRAL))
    style(fig, height=400)
    fig.update_layout(title_text=title, hovermode="x unified")
    return fig


def backtest_chart(series, eval_results, best_model, test_months):
    """Actual CPI against each model's held-out predictions."""
    test = series.iloc[-test_months:]
    context = series.iloc[-(test_months + 18):]
    fig = go.Figure()
    fig.add_vrect(x0=test.index[0], x1=test.index[-1], fillcolor=NEUTRAL, opacity=0.12, line_width=0,
                  annotation_text="Test period", annotation_position="top left")
    fig.add_trace(go.Scatter(x=context.index, y=context.values, name="Actual",
                             line=dict(color=NEUTRAL, width=3)))
    for name, res in eval_results.items():
        if res.get("predictions") is None:
            continue
        is_best = name == best_model
        fig.add_trace(go.Scatter(
            x=test.index, y=res["predictions"], name=f"{name}{' ★' if is_best else ''}",
            line=dict(color=MODEL_COLORS[name], width=3 if is_best else 1.8, dash="solid" if is_best else "dot")))
    style(fig, height=340)
    fig.update_layout(
        title_text="Predictions on months the models had not seen",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, title_text=""),
        margin=dict(l=8, r=8, t=36, b=40),
    )
    return fig


def model_bars(eval_results, best_model):
    """Test RMSE per model."""
    items = [(k, v["rmse"]) for k, v in eval_results.items() if v["status"] == "Success"]
    items.sort(key=lambda kv: kv[1], reverse=True)
    fig = go.Figure(go.Bar(
        x=[v for _, v in items], y=[k for k, _ in items], orientation="h",
        marker_color=[ACCENT if k == best_model else NEUTRAL for k, _ in items],
        text=[f"{v:.2f}" for _, v in items], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: RMSE %{x:.3f}<extra></extra>"))
    style(fig, height=max(150, 56 * len(items) + 60), legend=False)
    fig.update_layout(title_text="Test RMSE (lower is better)")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(range=[0, max(v for _, v in items) * 1.25] if items else None)
    return fig


# ----------------------------------------------------------------------------
# Inflation viewer
# ----------------------------------------------------------------------------
def inflation_line(df, column, title, show_bands):
    fig = go.Figure(go.Scatter(x=df["date"], y=df[column], line=dict(color=ACCENT, width=2.5), name="Inflation",
                               hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>"))
    valid = df[column].dropna()
    if show_bands and not valid.empty:
        _band_shapes(fig, top=float(valid.max()) + 1)
        fig.add_annotation(x=1, xref="paper", y=4, text="Increasing", showarrow=False, xanchor="right",
                           font=dict(size=10, color=AMBER))
        fig.add_annotation(x=1, xref="paper", y=5.4, text="High", showarrow=False, xanchor="right",
                           font=dict(size=10, color=RED))
    fig.add_hline(y=0, line_color=NEUTRAL, line_width=1)
    style(fig, height=380, legend=False)
    fig.update_layout(title_text=title)
    fig.update_yaxes(title="Inflation rate (%)")
    return fig


def month_year_calendar(df, column="mom_inflation"):
    """Year × month grid of month-over-month inflation, to show seasonality."""
    frame = df.dropna(subset=[column]).copy()
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    pivot = frame.pivot(index="year", columns="month", values=column).reindex(columns=range(1, 13))
    z = pivot.values.astype(float)
    limit = max(np.nanmax(np.abs(z)) if np.isfinite(z).any() else 1.0, 0.5)
    text = np.where(np.isnan(z), "", np.char.mod("%.1f", np.nan_to_num(z)))
    fig = go.Figure(go.Heatmap(
        z=z, x=MONTHS, y=[str(y) for y in pivot.index], colorscale=DIVERGING, zmid=0, zmin=-limit, zmax=limit,
        xgap=3, ygap=3, text=text, texttemplate="%{text}", textfont=dict(size=11),
        hoverongaps=False, hovertemplate="%{y} %{x}: %{z:.2f}%<extra></extra>",
        colorbar=dict(title="MoM %", thickness=10, len=0.8)))
    style(fig, height=max(260, 34 * len(pivot) + 90), legend=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(side="top", gridcolor="rgba(0,0,0,0)")
    fig.update_layout(title_text="Month-over-month inflation by calendar month")
    return fig


# ----------------------------------------------------------------------------
# Purchasing power
# ----------------------------------------------------------------------------
def peso_waffle(peso_value):
    """10×10 grid of centavos: filled squares are what ₱1 still buys versus 2018."""
    filled = int(round(min(max(peso_value, 0.0), 1.0) * 100))
    grid = np.zeros(100)
    grid[:filled] = 1
    grid = grid.reshape(10, 10)
    fig = go.Figure(go.Heatmap(
        z=grid, colorscale=[[0, "rgba(148,163,184,0.25)"], [1, ACCENT]], showscale=False, xgap=3, ygap=3,
        hoverinfo="skip"))
    style(fig, height=300, legend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, autorange="reversed", scaleanchor="x")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def real_value_line(worth, income):
    fig = go.Figure(go.Scatter(x=worth["date"], y=worth["real_income"], line=dict(color=ACCENT, width=2.5),
                               name="Value in 2018 pesos", hovertemplate="%{x|%b %Y}: ₱%{y:,.0f}<extra></extra>"))
    fig.add_hline(y=income, line_dash="dot", line_color=NEUTRAL, annotation_text="Nominal income",
                  annotation_position="top left")
    style(fig, height=300, legend=False)
    fig.update_yaxes(title="Value in 2018 pesos (PHP)", tickprefix="₱")
    return fig


def benchmark_bars(income, income_bench, expend_bench, survey_year):
    labels = ["Your income", f"Avg family income ({survey_year})", f"Avg family expenditure ({survey_year})"]
    values = [income, income_bench, expend_bench]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=[ACCENT, NEUTRAL, NEUTRAL],
        text=[f"₱{v:,.0f}" for v in values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: ₱%{x:,.0f}<extra></extra>"))
    style(fig, height=230, legend=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title="Monthly amount (PHP)", range=[0, max(values) * 1.2])
    return fig
