"""Refresh data/PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv from PSA OpenSTAT.

Source table: "Consumer Price Index for All Income Households by Commodity Group (2018=100)",
PSA OpenSTAT > Prices > Consumer Price Index > 2018-based (New Geographic Code).

    python scripts/update_cpi_from_psa.py            # fetch and overwrite the CSV
    python scripts/update_cpi_from_psa.py --dry-run  # fetch and report differences only

The script keeps the Philippines, the 17 regions and the Negros Island Region (NIR), plus the 13 major
commodity groups and All Items. Provinces and the NCR/"areas outside NCR" split are left out.
It prints how many values were revised and which months are new, so every refresh is auditable.
Only the Python standard library and pandas are needed.
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv")
TABLE_URL = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/PI/CPI/2018NEW"
TABLE_ID = "0012M4ACP22.px"  # file name changes when PSA starts a new series; update here if it moves

REGION_CODES = {
    "PHILIPPINES": "PH",
    "National Capital Region (NCR)": "NCR",
    "Cordillera Administrative Region (CAR)": "CAR",
    "Region I (Ilocos Region)": "R1",
    "Region II (Cagayan Valley)": "R2",
    "Region III (Central Luzon)": "R3",
    "Region IV-A (CALABARZON)": "R4A",
    "MIMAROPA Region": "MIMAROPA",
    "Region V (Bicol Region)": "R5",
    "Region VI (Western Visayas)": "R6",
    "Region VII (Central Visayas)": "R7",
    "Region VIII (Eastern Visayas)": "R8",
    "Region IX (Zamboanga Peninsula)": "R9",
    "Region X (Northern Mindanao)": "R10",
    "Region XI (Davao Region)": "R11",
    "Region XII (SOCCSKSARGEN)": "R12",
    "Region XIII (Caraga)": "R13",
    "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)": "BARMM",
    "Negros Island Region (NIR)": "NIR",
}


def request(url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": "PresyoPH-data-update", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read()


def fetch_psa():
    url = f"{TABLE_URL}/{TABLE_ID}"
    meta = json.loads(request(url))
    print("PSA table:", meta["title"])
    variables = {v["code"]: v for v in meta["variables"]}

    geo = variables["Geolocation"]
    geo_values = [
        value for value, text in zip(geo["values"], geo["valueTexts"])
        if text.strip(". ").strip() in REGION_CODES and not text.startswith("....")
    ]
    com = variables["Commodity Description"]
    com_values = [
        value for value, text in zip(com["values"], com["valueTexts"])
        if re.match(r"^(0|\d{2}) - ", text)
    ]
    periods = [v for v, t in zip(variables["Period"]["values"], variables["Period"]["valueTexts"]) if t != "Ave"]

    query = {
        "query": [
            {"code": "Geolocation", "selection": {"filter": "item", "values": geo_values}},
            {"code": "Commodity Description", "selection": {"filter": "item", "values": com_values}},
            {"code": "Year", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Period", "selection": {"filter": "item", "values": periods}},
        ],
        "response": {"format": "csv"},
    }
    raw = request(url, query).decode("utf-8-sig")
    wide = pd.read_csv(io.StringIO(raw))

    long = wide.melt(id_vars=["Geolocation", "Commodity Description"], var_name="month", value_name="cpi_value")
    long["cpi_value"] = pd.to_numeric(long["cpi_value"], errors="coerce")  # ".." marks months not yet published
    long = long.dropna(subset=["cpi_value"])
    long["date"] = pd.to_datetime(long["month"], format="%Y %b")
    long["region_code"] = long["Geolocation"].str.strip(". ").str.strip().map(REGION_CODES)
    split = long["Commodity Description"].str.extract(r"^(\d+)\s*-\s*(.+)$")
    long["commodity_code"] = split[0]
    long["commodity_group"] = split[1].str.strip().str.title()
    out = long[["date", "region_code", "commodity_code", "commodity_group", "cpi_value"]]
    out = out.sort_values(["region_code", "commodity_code", "date"]).reset_index(drop=True)
    out["cpi_value"] = out["cpi_value"].round(6)  # keep PSA's precision, drop floating-point noise only
    return out


def report(old, new):
    key = ["date", "region_code", "commodity_code"]
    old = old.assign(commodity_code=old["commodity_code"].astype(str).str.zfill(2).replace({"00": "0"}))
    merged = new.merge(old, on=key, how="outer", suffixes=("_new", "_old"), indicator=True)
    both = merged[merged["_merge"] == "both"]
    # PSA publishes one decimal; ignore differences far below that (a few regional series carry long decimals).
    changed = both[(both["cpi_value_new"] - both["cpi_value_old"]).abs() > 0.001]
    added = merged[merged["_merge"] == "left_only"]
    removed = merged[merged["_merge"] == "right_only"]
    print(f"Rows: {len(old):,} -> {len(new):,}")
    print(f"Unchanged values: {len(both) - len(changed):,} of {len(both):,}")
    print(f"Revised values:   {len(changed):,}")
    if len(changed):
        print("  revised months:", sorted(changed['date'].dt.strftime('%Y-%m').unique()))
    print(f"New rows:         {len(added):,}  (new months: {sorted(added['date'].dt.strftime('%Y-%m').unique())[-6:]})")
    print(f"Rows no longer in PSA table: {len(removed):,}")
    print(f"New regions: {sorted(set(new['region_code']) - set(old['region_code']))}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="report differences without writing the CSV")
    args = parser.parse_args()

    new = fetch_psa()
    if os.path.exists(CSV_PATH):
        report(pd.read_csv(CSV_PATH, parse_dates=["date"]), new)
    if args.dry_run:
        print("Dry run: CSV not written.")
        return 0
    out = new.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    print(f"Wrote {len(out):,} rows to {CSV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
