import pandas as pd
import streamlit as st

from analytics.calculations import classify_inflation_level
from analytics.insights import dashboard_headline
from ui import charts
from views.common import (
    fmt_pct,
    headline,
    load_inflation_frame,
    load_region_geojson,
    load_stale_series,
    page_header,
    stale_groups,
)


def render(ctx):
    page_header("Price Change Dashboard", ctx)

    inflation = load_inflation_frame()
    all_items = inflation[inflation["commodity_group"] == "All Items"]
    reg_all = all_items[all_items["region_code"] == ctx.region].sort_values("date")
    ph_all = all_items[all_items["region_code"] == "PH"].sort_values("date")

    # Year-over-year needs 12 prior months, so the first year has no rates.
    years = sorted(reg_all.dropna(subset=["yoy_inflation"])["date"].dt.year.unique(), reverse=True)
    left, _ = st.columns([1, 3])
    with left:
        year = st.selectbox("Ranking year", options=years, index=0, help="Uses the last available month of the year.")

    reg_year = reg_all[reg_all["date"].dt.year == year]
    period = reg_year["date"].max()

    # ---- Headline numbers
    latest, prev = reg_all.iloc[-1], reg_all.iloc[-2]
    ph_latest, ph_prev = ph_all.iloc[-1], ph_all.iloc[-2]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"CPI · {latest['date']:%b %Y}", f"{latest['cpi_value']:.1f}",
              f"{latest['cpi_value'] - prev['cpi_value']:+.1f} MoM", delta_color="inverse", border=True)
    k2.metric("Regional inflation (YoY)", fmt_pct(latest["yoy_inflation"]),
              f"{latest['yoy_inflation'] - prev['yoy_inflation']:+.2f} pts MoM", delta_color="inverse", border=True)
    k3.metric("National inflation (YoY)", fmt_pct(ph_latest["yoy_inflation"]),
              f"{ph_latest['yoy_inflation'] - ph_prev['yoy_inflation']:+.2f} pts MoM", delta_color="inverse", border=True)
    gap = latest["yoy_inflation"] - ph_latest["yoy_inflation"]
    k4.metric("Region vs national", f"{gap:+.2f} pts", border=True,
              help="Regional minus national year-over-year inflation, in percentage points.")

    # ---- Ranking snapshot
    stale = stale_groups(ctx.region)
    groups = inflation[(inflation["region_code"] == ctx.region) & (inflation["commodity_group"] != "All Items")]
    snapshot = groups[groups["date"] == period].dropna(subset=["yoy_inflation"]).copy()
    excluded = sorted(set(snapshot["commodity_group"]) & stale)
    snapshot = snapshot[~snapshot["commodity_group"].isin(stale)]
    snapshot["Status"] = snapshot["yoy_inflation"].apply(lambda v: classify_inflation_level(v)[0])
    national = inflation[(inflation["region_code"] == "PH") & (inflation["date"] == period)].set_index(
        "commodity_group")["yoy_inflation"]
    snapshot["National YoY (%)"] = snapshot["commodity_group"].map(national)
    rank_df = snapshot.rename(
        columns={"commodity_group": "Commodity Group", "yoy_inflation": "YoY Inflation (%)"}
    ).sort_values("YoY Inflation (%)", ascending=False)
    rank_df["vs National (pts)"] = rank_df["YoY Inflation (%)"] - rank_df["National YoY (%)"]

    headline(dashboard_headline(rank_df, ctx.region_name, period, ctx.is_national))

    tab_rank, tab_trend, tab_regions = st.tabs(["Commodity groups", "Trends", "Regions"])

    # ------------------------------------------------------------- ranking
    with tab_rank:
        st.caption(
            f"Year-over-year price change by commodity group, {period:%B %Y}. "
            "● Normal (≤3%) · Increasing (3–5%) · High (>5%)"
        )
        fig = charts.dumbbell(rank_df, ctx.region, show_national=not ctx.is_national)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        if excluded:
            st.info(
                "**Excluded:** " + ", ".join(excluded) + ". The CPI for this series has not changed for "
                "several months because PSA updates it only occasionally, so there is nothing to rank."
            )
        with st.expander("Show the numbers"):
            cols = ["Commodity Group", "YoY Inflation (%)", "National YoY (%)", "vs National (pts)", "Status"]
            st.dataframe(
                rank_df[cols].style.format(
                    {"YoY Inflation (%)": "{:.2f}", "National YoY (%)": "{:.2f}", "vs National (pts)": "{:+.2f}"}),
                use_container_width=True, hide_index=True)

    # --------------------------------------------------------------- trends
    with tab_trend:
        st.markdown("##### Headline inflation")
        trend = (
            reg_all[["date", "yoy_inflation"]]
            .merge(ph_all[["date", "yoy_inflation"]], on="date", suffixes=("_region", "_national"))
            .rename(columns={"yoy_inflation_region": "region", "yoy_inflation_national": "national"})
            .dropna()
        )
        label = "Philippines" if ctx.is_national else ctx.region
        st.plotly_chart(charts.trend_lines(trend, label), use_container_width=True, config={"displayModeBar": False})
        st.caption("Shaded bands mark the Increasing (3–5%) and High (>5%) ranges.")

        st.markdown("##### Every commodity group")
        names = sorted(g for g in groups["commodity_group"].unique() if g not in stale)
        st.plotly_chart(charts.small_multiples(groups, names), use_container_width=True,
                        config={"displayModeBar": False})

    # -------------------------------------------------------------- regions
    with tab_regions:
        all_groups = ["All Items"] + sorted(g for g in inflation["commodity_group"].unique() if g != "All Items")
        left, _ = st.columns([1, 2])
        with left:
            map_group = st.selectbox("Commodity group", options=all_groups, index=0)
        snap = inflation[(inflation["date"] == period) & (inflation["region_code"] != "PH")]
        snap = snap[snap["commodity_group"] == map_group]
        stale_df = load_stale_series()
        stale_regions = set(stale_df.loc[stale_df["commodity_group"] == map_group, "region_code"])
        values = {r: (None if r in stale_regions else v) for r, v in zip(snap["region_code"], snap["yoy_inflation"])}
        map_title = f"{map_group}: YoY inflation, {period:%B %Y}"
        geojson = load_region_geojson()
        if geojson is not None:
            names = {code: name.split(" (")[0] for code, name in ctx.region_map.items()}
            map_col, rank_col = st.columns([3, 2])
            with map_col:
                st.plotly_chart(charts.region_map(geojson, values, names, title=map_title),
                                use_container_width=True, config={"displayModeBar": False})
            with rank_col:
                st.plotly_chart(charts.region_bars(values, names), use_container_width=True,
                                config={"displayModeBar": False})
            st.caption("Grey regions have no usable data for this group. Boundaries: faeldon/philippines-json-maps (MIT).")
        else:  # boundary file missing: fall back to the schematic tile map
            st.plotly_chart(charts.tile_map(values, ctx.region_map, title=map_title),
                            use_container_width=True, config={"displayModeBar": False})
            st.caption("Schematic map: each tile is a region, placed roughly where it sits on the map.")

        st.markdown("##### All regions and commodity groups")
        heat = inflation[(inflation["date"] == period) & (inflation["commodity_group"] != "All Items")]
        heat = heat.merge(stale_df.assign(stale=True), on=["region_code", "commodity_group"], how="left")
        heat.loc[heat["stale"].fillna(False).astype(bool), "yoy_inflation"] = pd.NA
        pivot = heat.pivot(index="commodity_group", columns="region_code", values="yoy_inflation").astype(float)
        pivot = pivot[[c for c in ctx.region_map if c in pivot.columns]].dropna(how="all")
        st.plotly_chart(charts.heatmap(pivot), use_container_width=True, config={"displayModeBar": False})
        st.caption("Blank cells are series with no month-to-month movement (see About & Methodology).")
