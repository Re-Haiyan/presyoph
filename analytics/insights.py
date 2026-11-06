"""Plain-language one-line summaries generated from the data."""

import pandas as pd

from analytics.calculations import classify_inflation_level


def _pts(value):
    return f"{abs(value):.1f} point{'s' if round(abs(value), 1) != 1.0 else ''}"


def dashboard_headline(rank_df, region_name, period, is_national=False):
    """Headline for the price-change ranking.

    ``rank_df`` needs ``Commodity Group``, ``YoY Inflation (%)`` and
    ``National YoY (%)`` columns, already sorted from highest to lowest.
    """
    if rank_df.empty:
        return "No year-over-year rates are available for this period."
    top = rank_df.iloc[0]
    when = f"{period:%B %Y}"
    text = f"In {when}, **{top['Commodity Group']}** led price increases in {region_name} at **{top['YoY Inflation (%)']:.1f}%**"
    if not is_national and pd.notna(top.get("National YoY (%)")):
        gap = top["YoY Inflation (%)"] - top["National YoY (%)"]
        if abs(gap) >= 0.05:
            text += f", {_pts(gap)} {'above' if gap > 0 else 'below'} the national rate"
    text += "."
    high = int((rank_df["YoY Inflation (%)"] > 5.0).sum())
    if high:
        text += f" {high} of {len(rank_df)} groups are in the High range (above 5%)."
    else:
        text += f" None of the {len(rank_df)} groups are in the High range."
    return text


def inflation_headline(latest_yoy, previous_yoy, group, region_name, date):
    """Headline for the inflation viewer."""
    level, _ = classify_inflation_level(latest_yoy)
    if pd.isna(latest_yoy):
        return f"Not enough history to compute year-over-year inflation for {group}."
    direction = "up from" if latest_yoy > previous_yoy else "down from" if latest_yoy < previous_yoy else "unchanged from"
    text = f"{group} inflation in {region_name} was **{latest_yoy:.2f}%** in {date:%B %Y} ({level.lower()} level)"
    if not pd.isna(previous_yoy) and latest_yoy != previous_yoy:
        text += f", {direction} {previous_yoy:.2f}% the month before"
    return text + "."


def forecast_headline(best_model, horizon, end_date, end_yoy, last_actual_date):
    """Headline for the forecast page."""
    if pd.isna(end_yoy):
        return f"{best_model} was the most accurate model on the test period."
    level, _ = classify_inflation_level(end_yoy)
    return (
        f"{best_model} was the most accurate model. It projects year-over-year inflation of "
        f"**{end_yoy:.1f}%** by {end_date:%B %Y} ({level.lower()} level), {horizon} months after "
        f"the last reading in {last_actual_date:%B %Y}."
    )


def purchasing_headline(peso_value, region_name, income, vs_income_pct):
    """Headline for the purchasing power page."""
    text = f"In {region_name}, ₱1.00 today buys what **₱{peso_value:.2f}** bought in 2018"
    if income > 0:
        text += f". Your income is {abs(vs_income_pct):.0f}% {'above' if vs_income_pct >= 0 else 'below'} the regional average family income"
    return text + "."
