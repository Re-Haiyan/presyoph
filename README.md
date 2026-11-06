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
| **Price Change Dashboard** | Ranks the 13 commodity groups by year-over-year price change (Normal / Increasing / High), compares each with the national figure, plots region vs. national headline inflation, and shows a region × commodity heatmap. |
| **Time-Series Forecasting** | Trains Prophet, ARIMA and SARIMA on the same series, scores them on a held-out period (RMSE, MAE, MAPE), forecasts 6–12 months ahead with the best model and a 95% interval, and shows the inflation rate the forecast implies. CSV download included. |
| **Inflation Rate Viewer** | Month-over-month or year-over-year inflation for any region and commodity group, with the latest reading, change, and record high. |
| **Purchasing Power Calculator** | Converts a monthly income to 2018 pesos using the regional CPI, shows what that income has been worth over time, and compares it with the regional FIES average income and expenditure. Income is never stored. |
| **About & Methodology** | Data sources, formulas, thresholds and limitations. |

## Quick start

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database (`presyoph.db`) is built automatically from the CSV files in `data/` on first run and
rebuilt whenever those files change.

## Data

| File | Source | Contents |
| --- | --- | --- |
| `data/PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv` | PSA OpenSTAT | Monthly CPI (2018 = 100), Jan 2018 – Aug 2026, Philippines + 17 regions × 13 commodity groups + All Items (26,208 records) |
| `data/PH_FIES_Income_Expenditure_2023_clean.csv` | PSA 2023 FIES | Average annual family income and expenditure for the Philippines and each region (18 rows) |

Both are aggregate public statistics. No personal or household-level records are used.

## Method

- **Inflation**: YoY = CPI(t)/CPI(t−12) − 1; MoM = CPI(t)/CPI(t−1) − 1. Levels: Normal ≤ 3%, Increasing ≤ 5%, High > 5%.
- **Evaluation**: each model is trained on Jan 2018 – Dec 2025 (96 months) and tested on Jan – Aug 2026 (8 months).
  The lowest-RMSE model is refit on all data to produce the forecast.
- **Models**: Prophet (yearly seasonality), ARIMA(1,1,1), SARIMA(1,1,1)(1,1,1)₁₂.
- **Purchasing power**: income × 100 / latest regional CPI.

## Model benchmark

`python scripts/evaluate_models.py` evaluates all 252 region × commodity-group series
(output in [`results/`](results/)). Results for the Jan – Aug 2026 test period:

| Model | Mean RMSE | Median RMSE | Mean MAE | Mean MAPE | Median MAPE | Selected as best |
| --- | --- | --- | --- | --- | --- | --- |
| ARIMA | 4.07 | 2.55 | 3.57 | 2.49% | 1.52% | 48 / 252 |
| Prophet | 4.44 | 2.93 | 3.97 | 2.80% | 1.79% | 56 / 252 |
| **SARIMA** | **3.54** | **2.45** | **3.05** | **2.15%** | 1.55% | **148 / 252** |

SARIMA has the lowest average error and is selected most often. ARIMA has the lowest *median* MAPE, so the
differences are modest for typical series and larger for volatile ones. Because the app picks a model per
series, it benefits from all three.

## Project structure

```
app.py                  Streamlit app (5 pages)
analytics/
  calculations.py       Inflation, classification and purchasing-power math
  forecasting.py        Prophet / ARIMA / SARIMA, evaluation and forecasting
database/db_manager.py  SQLite loading, validation and queries
data/                   Cleaned PSA CSV files
scripts/                Batch model benchmark
results/                Benchmark output
tests/                  pytest suite (calculations, database, forecasting, app smoke tests)
```

## Testing

```bash
pytest
```

CI runs the same suite on every push and pull request.

## Limitations

- FIES values are from 2023 and do not reflect later income changes; the calculator states the survey year.
- Forecasts extrapolate past patterns and cannot anticipate shocks. Read the interval, not only the central line.
- Region-level data only: no city-, barangay- or store-level prices.

## Authors

Mark Rhean Caballero · Earl Naniong · Joenhel Pico — Instructor: Dr. Caren A. Pacol

## Data attribution

Source data: Philippine Statistics Authority (OpenSTAT and FIES), cleaned and reshaped for this project.
Check the PSA's terms of use before redistributing the data.
