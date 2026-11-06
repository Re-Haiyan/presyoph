"""Inflation and purchasing-power calculations used by the PresyoPH dashboard."""

import pandas as pd

# Documented classification thresholds (year-over-year inflation, %).
NORMAL_MAX = 3.0
INCREASING_MAX = 5.0

STATUS_COLORS = {
    "Normal": "#0D9488",
    "Increasing": "#D97706",
    "High": "#DC2626",
    "N/A": "#6C757D",
}


def calculate_inflation_series(df):
    """Add month-over-month and year-over-year inflation (%) to one CPI series."""
    df = df.sort_values("date").copy()
    df["mom_inflation"] = (df["cpi_value"] / df["cpi_value"].shift(1) - 1.0) * 100.0
    df["yoy_inflation"] = (df["cpi_value"] / df["cpi_value"].shift(12) - 1.0) * 100.0
    return df


def calculate_inflation_frame(df, group_cols=("region_code", "commodity_group")):
    """Vectorised version of :func:`calculate_inflation_series` for many series.

    Inflation is computed within each ``group_cols`` combination so that rows from
    different regions or commodity groups never bleed into each other.
    """
    df = df.sort_values(list(group_cols) + ["date"]).copy()
    grouped = df.groupby(list(group_cols), sort=False)["cpi_value"]
    df["mom_inflation"] = (df["cpi_value"] / grouped.shift(1) - 1.0) * 100.0
    df["yoy_inflation"] = (df["cpi_value"] / grouped.shift(12) - 1.0) * 100.0
    return df


def classify_inflation_level(yoy_val):
    """Label a YoY inflation rate as Normal (<=3%), Increasing (<=5%) or High (>5%)."""
    if yoy_val is None or pd.isna(yoy_val):
        return "N/A", STATUS_COLORS["N/A"]
    if yoy_val <= NORMAL_MAX:
        return "Normal", STATUS_COLORS["Normal"]
    if yoy_val <= INCREASING_MAX:
        return "Increasing", STATUS_COLORS["Increasing"]
    return "High", STATUS_COLORS["High"]


def peso_value(cpi_latest):
    """Purchasing power of one peso expressed in 2018 base pesos (100 / CPI)."""
    if cpi_latest is None or pd.isna(cpi_latest) or cpi_latest <= 0:
        return 0.0
    return 100.0 / cpi_latest


def calculate_purchasing_power(income, cpi_latest):
    """Convert a nominal income to 2018 base pesos.

    Returns ``(real_income, one_peso_value)``. The value of one peso depends only on
    the CPI, so it is still reported when the income is zero or missing.
    """
    one_peso = peso_value(cpi_latest)
    if income is None or pd.isna(income) or income <= 0:
        return 0.0, one_peso
    return income * one_peso, one_peso


def purchasing_power_change_pct(cpi_latest):
    """Signed change in the value of one peso since the 2018 base year (%).

    Negative means the peso buys less than in 2018; positive means it buys more.
    """
    one_peso = peso_value(cpi_latest)
    if one_peso == 0.0:
        return 0.0
    return (one_peso - 1.0) * 100.0


def income_needed_to_match_2018(income, cpi_latest):
    """Nominal income required today to match the buying power of ``income`` in 2018."""
    if income is None or pd.isna(income) or income <= 0 or cpi_latest is None or pd.isna(cpi_latest):
        return 0.0
    return income * cpi_latest / 100.0


def real_value_series(income, cpi_df):
    """What a fixed nominal income is worth in 2018 pesos in each month of ``cpi_df``."""
    out = cpi_df.sort_values("date")[["date", "cpi_value"]].copy()
    out["real_income"] = (
        out["cpi_value"].apply(lambda c: calculate_purchasing_power(income, c)[0])
    )
    return out


def _growth_factor(annual_pct, years):
    """(1 + rate)^years, with the rate given as a percentage per year."""
    base = 1.0 + annual_pct / 100.0
    if base <= 0:
        raise ValueError("A yearly rate of -100% or lower is not meaningful.")
    return base ** years


def future_real_value(income, inflation_pct, years, raise_pct=0.0):
    """Value, in today's pesos, of ``income`` after ``years`` of steady inflation.

    ``raise_pct`` is a yearly increase in nominal income; with 0 the income stays the same.
    """
    if income is None or pd.isna(income) or income <= 0:
        return 0.0
    return income * _growth_factor(raise_pct, years) / _growth_factor(inflation_pct, years)


def income_needed_for_same_power(income, inflation_pct, years):
    """Nominal income needed after ``years`` of steady inflation to buy what ``income`` buys today."""
    if income is None or pd.isna(income) or income <= 0:
        return 0.0
    return income * _growth_factor(inflation_pct, years)


def whatif_path(income, inflation_pct, years, raise_pct=0.0):
    """Month-by-month path of an income under steady inflation.

    Columns: ``month`` (0 = today), ``years``, ``nominal`` (pesos received that month, growing with
    ``raise_pct``), ``real`` (that amount in today's pesos) and ``needed`` (nominal income required to
    keep today's buying power).
    """
    months = list(range(int(round(years * 12)) + 1))
    rows = []
    for m in months:
        t = m / 12.0
        nominal = income * _growth_factor(raise_pct, t)
        needed = income * _growth_factor(inflation_pct, t)
        rows.append({"month": m, "years": t, "nominal": nominal, "real": nominal / _growth_factor(inflation_pct, t),
                     "needed": needed})
    return pd.DataFrame(rows)


def annual_to_monthly(amount_thousands):
    """Convert an annual figure in thousands of PHP to a monthly figure in PHP."""
    return amount_thousands * 1000.0 / 12.0


def compare_to_benchmark(income, benchmark):
    """Percentage by which ``income`` is above (+) or below (-) ``benchmark``."""
    if benchmark is None or pd.isna(benchmark) or benchmark <= 0:
        return 0.0
    return (income / benchmark - 1.0) * 100.0
