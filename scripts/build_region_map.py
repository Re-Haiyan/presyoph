"""Build data/ph_regions.geojson, the region boundaries used by the dashboard map.

Source: faeldon/philippines-json-maps (MIT licence, PSGC data as of 31 Dec 2023), which derives from
altcoder/philippines-psgc-shapefiles. Download this low-resolution file from the repository's
``latest/geojson`` folder:

    country/lowres/country.0.001.json

and run:

    python scripts/build_region_map.py country.0.001.json

The map has 18 regions: the 17 original regions plus the Negros Island Region (NIR), exactly as PSA's
current CPI table does (Negros Occidental, Negros Oriental and Siquijor are in NIR, not in Regions VI
and VII). Region codes match the ``region_code`` column of the CPI data.

This is a build-time tool and needs ``shapely`` (``pip install shapely``). The app itself does not.
"""

import argparse
import json
import os

from shapely.geometry import mapping, shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "ph_regions.geojson")

PSGC_TO_CODE = {
    100000000: "R1", 200000000: "R2", 300000000: "R3", 400000000: "R4A", 500000000: "R5",
    600000000: "R6", 700000000: "R7", 800000000: "R8", 900000000: "R9", 1000000000: "R10",
    1100000000: "R11", 1200000000: "R12", 1300000000: "NCR", 1400000000: "CAR",
    1600000000: "R13", 1700000000: "MIMAROPA", 1800000000: "NIR", 1900000000: "BARMM",
}
PRECISION = 3  # decimal degrees, about 110 m: plenty for a national map


def round_coords(obj):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(c, PRECISION) for c in obj]
        return [round_coords(o) for o in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("country_geojson")
    parser.add_argument("--out", default=OUT)
    args = parser.parse_args()

    with open(args.country_geojson, encoding="utf-8") as f:
        country = json.load(f)

    features = []
    for feature in country["features"]:
        code = PSGC_TO_CODE.get(feature["properties"]["adm1_psgc"])
        if code is None:
            continue
        geometry = shape(feature["geometry"]).buffer(0).simplify(0.0005, preserve_topology=True)
        features.append({
            "type": "Feature",
            "id": code,
            "properties": {"region_code": code},
            "geometry": {"type": geometry.geom_type, "coordinates": round_coords(mapping(geometry)["coordinates"])},
        })
    missing = set(PSGC_TO_CODE.values()) - {f["id"] for f in features}
    if missing:
        raise SystemExit(f"Source file is missing regions: {sorted(missing)}")

    out = {
        "type": "FeatureCollection",
        "attribution": "Boundaries: faeldon/philippines-json-maps (MIT), PSGC 2023. Region codes follow the PSA "
                       "CPI table, which lists the Negros Island Region separately.",
        "features": features,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote {len(features)} regions to {args.out} ({os.path.getsize(args.out) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
