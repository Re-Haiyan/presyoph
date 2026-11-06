# PresyoPH

**A time series inflation and household purchasing power analytics system for the Philippines.**

PresyoPH turns the Philippine Statistics Authority's (PSA) published Consumer Price Index (CPI) and
Family Income and Expenditure Survey (FIES) data into a web dashboard that shows where prices are
rising, where they are likely heading, and what a household income is actually worth after inflation.

Built for *Elective 4: Special Topics on Data Analytics 2*, BS Information Technology (Data Analytics),
Pangasinan State University – Urdaneta City Campus.

## Features

| Page | What it does |
| --- | --- |
| **Price Change Dashboard** | A generated one-line takeaway, headline KPIs, and three views. *Commodity groups*: a dumbbell chart of YoY inflation by group against the national figure (Normal / Increasing / High). *Trends*: region vs. national headline inflation with shaded bands, plus a mini chart for every group. *Regions*: a map of the 17 regions coloured by inflation with a ranked list beside it, and a region × commodity heatmap. |
| **Time-Series Forecasting** | Trains Prophet, ARIMA and SARIMA on the same series, scores them on a held-out period (RMSE, MAE, MAPE), and forecasts 6–12 months ahead with the best model and a 95% interval. Shows the inflation the forecast implies, how each model did on months it had not seen, and a CSV download. |
| **Inflation Rate Viewer** | Month-over-month or year-over-year inflation for any region and group, with a year × month calendar that exposes seasonality. |
| **Purchasing Power** | Converts a monthly income to 2018 pesos, shows what ₱1 still buys, the income needed to match 2018, what a fixed income has been worth over time, and a comparison with FIES regional averages. Income is never stored. |
| **About & Methodology** | Data sources, formulas, thresholds, limitations and data-quality findings. |

The interface follows Streamlit's light or dark theme, so charts and cards adapt automatically.

## Quick start

You need Python 3.10–3.12. Then:

```bash
git clone https://github.com/Re-Haiyan/presyoph.git
cd presyoph
.\run.bat          # Windows (macOS/Linux: ./run.sh)
```

The launcher creates a virtual environment, installs the packages and opens the app at
<http://localhost:8501>. The SQLite database (`presyoph.db`) is built automatically from the CSV files in
`data/` on first run and rebuilt whenever those files change.

**Full instructions, manual steps, deployment and troubleshooting: [docs/INSTALLATION.md](docs/INSTALLATION.md).**

## Data

| File | Source | Contents |
| --- | --- | --- |
| `data/PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv` | PSA OpenSTAT | Monthly CPI (2018 = 100), Jan 2018 – Aug 2026, Philippines + 17 regions × 13 commodity groups + All Items (26,208 records) |
| `data/PH_FIES_Income_Expenditure_2023_clean.csv` | PSA 2023 FIES | Average annual family income and expenditure for the Philippines and each region (18 rows) |

| `data/ph_regions.geojson` | [faeldon/philippines-json-maps](https://github.com/faeldon/philippines-json-maps) (MIT) | Simplified boundaries of the 17 regions for the map (247 KB). Licence text in `data/ph_regions.LICENSE.txt` |

Both statistics files are aggregate public data. No personal or household-level records are used.

**About the map file.** The source map includes the Negros Island Region, which the PSA data does not yet use.
`scripts/build_region_map.py` merges Negros Occidental back into Region VI and Negros Oriental plus Siquijor
back into Region VII so the map matches the data. The script is only needed to rebuild the file
(`pip install shapely`); the app does not need it. If the map file is missing, the app falls back to a
schematic tile map.

### Data-quality finding

**19 of the 252 series have a frozen CPI.** Financial Services is unchanged in every region (nationally it
has been 142.4 since January 2024; regionally it has been flat for 32–65 months), and Information and
Communication in Region III has been flat for six months. That pattern points to a stale or carried-forward
value in the source table, not stable prices. The app detects any series unchanged for 6+ months, leaves it
out of rankings, maps and forecasts, and says so on screen. Please verify these values against the PSA release.

## Method

- **Inflation**: YoY = CPI(t)/CPI(t−12) − 1; MoM = CPI(t)/CPI(t−1) − 1. Levels: Normal ≤ 3%, Increasing ≤ 5%, High > 5%.
- **Evaluation**: each model is trained on Jan 2018 – Dec 2025 (96 months) and tested on Jan – Aug 2026 (8 months).
  The lowest-RMSE model is refit on all data to produce the forecast.
- **Models**: Prophet (yearly seasonality), ARIMA(1,1,1), SARIMA(1,1,1)(1,1,1)₁₂.
- **Purchasing power**: income × 100 / latest regional CPI.

## Model benchmark

`python scripts/evaluate_models.py` evaluates every region × commodity-group series that passes the
data-quality check (233 of 252). Output is in [`results/`](results/). Jan – Aug 2026 test period:

| Model | Mean RMSE | Median RMSE | Mean MAE | Mean MAPE | Median MAPE | Selected as best |
| --- | --- | --- | --- | --- | --- | --- |
| ARIMA | 4.40 | 2.81 | 3.86 | 2.70% | 1.85% | 30 / 233 |
| Prophet | 4.50 | 2.71 | 4.02 | 2.84% | 1.79% | 56 / 233 |
| **SARIMA** | **3.46** | **2.17** | **3.00** | **2.12%** | **1.36%** | **147 / 233** |

SARIMA has the lowest error on every measure and is selected most often. Prophet and ARIMA are close
to each other, and Prophet was less accurate than ARIMA on the headline All Items series. This is one
eight-month test window, so read it as a result for this data, not a general ranking. The app picks a model
per series, so it benefits from all three.

## Project structure

```
app.py                  Entry point: layout, navigation, sidebar
views/                  One module per page (dashboard, forecasting, inflation, purchasing_power, about)
ui/charts.py            All Plotly figures, with one shared minimal style
analytics/
  calculations.py       Inflation, classification and purchasing-power math
  forecasting.py        Prophet / ARIMA / SARIMA, evaluation and forecasting
  quality.py            Detects frozen (stale) CPI series
  insights.py           One-line takeaways generated from the data
database/db_manager.py  SQLite loading, validation and queries
data/                   Cleaned PSA CSV files
scripts/                Batch model benchmark, region map builder
results/                Benchmark output
docs/                   Project paper (DOCX and PDF)
tests/                  pytest suite
.streamlit/config.toml  Theme settings
```

## Testing

```bash
pytest
```

62 tests cover the calculations, database loading, forecasting, data-quality checks, charts, the map data
and a smoke test of every page. CI runs the same suite on every push and pull request.

## Limitations

- FIES values are from 2023 and do not reflect later income changes; the calculator states the survey year.
- Forecasts extrapolate past patterns and cannot anticipate shocks. Read the interval, not only the central line.
- Map boundaries are simplified and show the 17 regions used by the data; there are no city-, barangay- or store-level prices.
- Frozen series (above) are excluded until the source values are verified.

## Authors

Mark Rhean Caballero · Earl Naniong · Joenhel Pico — Instructor: Dr. Caren A. Pacol

## License

The source code is released under the [MIT License](LICENSE). The data files are not covered by it:
the CPI and FIES statistics come from the PSA (see below), and the map boundaries are MIT-licensed
separately by their author (`data/ph_regions.LICENSE.txt`).

## Data attribution

Source data: Philippine Statistics Authority (OpenSTAT and FIES), cleaned and reshaped for this project.
Check the PSA's terms of use before redistributing the data.
