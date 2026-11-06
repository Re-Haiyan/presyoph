"""SQLite storage for the cleaned PSA CPI and FIES tables.

The database is a derived artefact: it is rebuilt from the CSV files in ``data/``
whenever it is missing or the CSVs have changed, so it never needs to be committed.
"""

import hashlib
import os
import sqlite3
from contextlib import closing

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("PRESYOPH_DB", os.path.join(BASE_DIR, "presyoph.db"))
DEFAULT_CPI_CSV = os.path.join(BASE_DIR, "data", "PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv")
DEFAULT_FIES_CSV = os.path.join(BASE_DIR, "data", "PH_FIES_Income_Expenditure_2023_clean.csv")

CPI_COLUMNS = {"date", "region_code", "commodity_code", "commodity_group", "cpi_value"}
FIES_COLUMNS = {
    "region_code",
    "region_name",
    "avg_annual_income_php_thousands",
    "avg_annual_expenditure_php_thousands",
    "survey_year",
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def _file_digest(*paths):
    digest = hashlib.sha256()
    for path in paths:
        with open(path, "rb") as handle:
            digest.update(handle.read())
    return digest.hexdigest()


def _validate(df, required, label):
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} CSV is missing columns: {sorted(missing)}")


def _stored_digest(conn):
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'source_digest'").fetchone()
    except sqlite3.OperationalError:
        return None
    return row[0] if row else None


def initialize_db(cpi_csv_path=None, fies_csv_path=None, force_rebuild=False):
    """Create the database, or rebuild it if the source CSVs changed."""
    cpi_csv_path = cpi_csv_path or DEFAULT_CPI_CSV
    fies_csv_path = fies_csv_path or DEFAULT_FIES_CSV
    digest = _file_digest(cpi_csv_path, fies_csv_path)

    with closing(get_connection()) as conn:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cpi_data'"
        ).fetchone()
        if has_table and not force_rebuild and _stored_digest(conn) == digest:
            return False

        cpi_df = pd.read_csv(cpi_csv_path)
        fies_df = pd.read_csv(fies_csv_path)
        _validate(cpi_df, CPI_COLUMNS, "CPI")
        _validate(fies_df, FIES_COLUMNS, "FIES")
        cpi_df["date"] = pd.to_datetime(cpi_df["date"]).dt.strftime("%Y-%m-%d")

        cpi_df.to_sql("cpi_data", conn, if_exists="replace", index=False)
        fies_df.to_sql("fies_data", conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cpi_lookup ON cpi_data(region_code, commodity_group, date)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fies_region ON fies_data(region_code)")
        conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('source_digest', ?)", (digest,)
        )
        conn.commit()
    return True


def get_cpi_data(region_code=None, commodity_group=None):
    """CPI rows, optionally filtered by region and/or commodity group."""
    query = "SELECT * FROM cpi_data WHERE 1=1"
    params = []
    if region_code:
        query += " AND region_code = ?"
        params.append(region_code)
    if commodity_group:
        query += " AND commodity_group = ?"
        params.append(commodity_group)
    query += " ORDER BY date ASC"

    with closing(get_connection()) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    df["date"] = pd.to_datetime(df["date"])
    return df


def get_fies_data(region_code=None):
    """FIES benchmark rows, optionally filtered by region."""
    query = "SELECT * FROM fies_data WHERE 1=1"
    params = []
    if region_code:
        query += " AND region_code = ?"
        params.append(region_code)

    with closing(get_connection()) as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_commodity_groups(region_code=None):
    """Distinct commodity groups, with 'All Items' first."""
    groups = get_cpi_data(region_code=region_code)["commodity_group"].unique().tolist()
    return sorted(groups, key=lambda g: (g != "All Items", g))


def get_data_coverage():
    """First and last month, plus row count, of the stored CPI data."""
    with closing(get_connection()) as conn:
        first, last, rows = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM cpi_data"
        ).fetchone()
    return pd.to_datetime(first), pd.to_datetime(last), rows
