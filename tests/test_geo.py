import json
import os

import pandas as pd
import pytest

from database.db_manager import DEFAULT_FIES_CSV
from ui import charts

GEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ph_regions.geojson")


@pytest.fixture(scope="module")
def geojson():
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


def coords(obj):
    if isinstance(obj[0], (int, float)):
        yield obj
    else:
        for item in obj:
            yield from coords(item)


def test_regions_match_the_data_exactly(geojson):
    expected = set(pd.read_csv(DEFAULT_FIES_CSV)["region_code"]) - {"PH"}
    assert {f["id"] for f in geojson["features"]} == expected
    assert len(geojson["features"]) == 17


def test_file_is_small_and_credits_its_source(geojson):
    assert os.path.getsize(GEO) < 1_000_000
    assert "faeldon" in geojson["attribution"]
    assert os.path.exists(os.path.join(os.path.dirname(GEO), "ph_regions.LICENSE.txt"))


def test_shapes_are_inside_the_philippines(geojson):
    for feature in geojson["features"]:
        assert feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
        for lon, lat in coords(feature["geometry"]["coordinates"]):
            assert 116 <= lon <= 128 and 4 <= lat <= 21, feature["id"]


def test_negros_is_merged_into_regions_vi_and_vii(geojson):
    # Negros Island lies near lon 123, lat 10; it must belong to R6 or R7, never to a separate region.
    by_id = {f["id"]: f for f in geojson["features"]}
    for code in ("R6", "R7"):
        points = list(coords(by_id[code]["geometry"]["coordinates"]))
        assert any(122.5 < lon < 124 and 9 < lat < 11 for lon, lat in points), code


def test_region_map_greys_out_missing_regions(geojson):
    names = {f["id"]: f["id"] for f in geojson["features"]}
    values = {f["id"]: 5.0 for f in geojson["features"]}
    values["R1"] = None
    values["R2"] = float("nan")
    fig = charts.region_map(geojson, values, names)
    assert len(fig.data) == 2
    assert len(fig.data[0].locations) == 17          # grey base layer covers every region
    assert len(fig.data[1].locations) == 15          # coloured layer skips the two missing
    assert "R1" not in fig.data[1].locations


def test_region_bars_skip_missing():
    fig = charts.region_bars({"A": 1.0, "B": None, "C": 3.0}, {})
    assert list(fig.data[0].y) == ["A", "C"]
