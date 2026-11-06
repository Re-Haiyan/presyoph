import numpy as np
import pandas as pd

from ui import charts


def test_short_label():
    assert charts.short_label("abc", 5) == "abc"
    assert charts.short_label("abcdefghij", 5).endswith("…")
    assert len(charts.short_label("abcdefghij", 5)) == 5


def test_tile_positions_are_unique():
    assert len(set(charts.TILE_POSITIONS.values())) == len(charts.TILE_POSITIONS) == 17


def test_tile_map_skips_missing_values():
    names = {code: code for code in charts.TILE_POSITIONS}
    values = {"NCR": 5.0, "R1": None, "R2": float("nan")}
    fig = charts.tile_map(values, names)
    z = np.array(fig.data[0].z, dtype=float)
    assert np.isfinite(z).sum() == 1


def test_peso_waffle_fills_proportionally_and_clamps():
    def filled(value):
        return int(np.nansum(charts.peso_waffle(value).data[0].z))

    assert filled(0.73) == 73
    assert filled(1.4) == 100
    assert filled(-1) == 0


def test_heatmap_handles_missing_cells():
    pivot = pd.DataFrame({"A": [1.0, np.nan], "B": [2.0, 3.0]}, index=["g1", "g2"])
    fig = charts.heatmap(pivot)
    assert fig.data[0].zmid == 0


def test_dumbbell_without_national_has_one_marker_trace():
    df = pd.DataFrame({
        "Commodity Group": ["a", "b"], "YoY Inflation (%)": [1.0, 6.0],
        "National YoY (%)": [1.0, 6.0], "Status": ["Normal", "High"],
    })
    assert len(charts.dumbbell(df, "PH", show_national=False).data) == 1
    assert len(charts.dumbbell(df, "NCR", show_national=True).data) == 3
