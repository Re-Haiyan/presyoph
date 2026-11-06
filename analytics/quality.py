"""Data-quality checks for CPI series."""

import pandas as pd

DEFAULT_MIN_FLAT_MONTHS = 6


def trailing_flat_months(values):
    """Number of consecutive final months with exactly the same value.

    A CPI that does not move for many months is almost always a stale or
    carried-forward value rather than genuinely stable prices.
    """
    values = list(values)
    if not values:
        return 0
    last = values[-1]
    count = 0
    for value in reversed(values):
        if value != last:
            break
        count += 1
    return count


def find_stale_series(cpi_df, min_months=DEFAULT_MIN_FLAT_MONTHS):
    """Series whose CPI has been unchanged for at least ``min_months`` months.

    Returns a DataFrame with ``region_code``, ``commodity_group`` and
    ``flat_months`` (empty when every series is moving).
    """
    rows = []
    for (region, group), frame in cpi_df.sort_values("date").groupby(["region_code", "commodity_group"]):
        months = trailing_flat_months(frame["cpi_value"])
        if months >= min_months:
            rows.append({"region_code": region, "commodity_group": group, "flat_months": months})
    return pd.DataFrame(rows, columns=["region_code", "commodity_group", "flat_months"])
