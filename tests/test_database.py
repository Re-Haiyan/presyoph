import pandas as pd
import pytest

from database import db_manager


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_manager, "DB_PATH", str(tmp_path / "test.db"))
    return db_manager


def test_initialize_loads_expected_dataset(db):
    assert db.initialize_db() is True
    first, last, rows = db.get_data_coverage()
    assert rows == 26208  # 18 regions x 14 series x 104 months
    assert first == pd.Timestamp("2018-01-01")
    assert last == pd.Timestamp("2026-08-01")
    assert len(db.get_fies_data()) == 18


def test_initialize_is_idempotent_until_sources_change(db, tmp_path):
    db.initialize_db()
    assert db.initialize_db() is False  # unchanged CSVs: no rebuild

    changed = tmp_path / "cpi.csv"
    pd.read_csv(db.DEFAULT_CPI_CSV).head(50).to_csv(changed, index=False)
    assert db.initialize_db(cpi_csv_path=str(changed)) is True
    assert db.get_data_coverage()[2] == 50


def test_missing_columns_are_rejected(db, tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"date": ["2018-01-01"], "cpi_value": [100.0]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        db.initialize_db(cpi_csv_path=str(bad))


def test_filters_and_commodity_groups(db):
    db.initialize_db()
    series = db.get_cpi_data(region_code="NCR", commodity_group="All Items")
    assert len(series) == 104
    assert series["date"].is_monotonic_increasing
    groups = db.get_commodity_groups("NCR")
    assert groups[0] == "All Items"
    assert len(groups) == 14
    assert db.get_fies_data("NCR").iloc[0]["survey_year"] == 2023
