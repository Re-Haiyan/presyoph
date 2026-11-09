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
| **Price Change Dashboard** | A generated one-line takeaway, headline KPIs, and three views. *Commodity groups*: a dumbbell chart of YoY inflation by group against the national figure (Normal / Increasing / High). *Trends*: region vs. national headline inflation with shaded bands, plus a mini chart for every group. *Regions*: a map of the 18 regions coloured by inflation with a ranked list beside it, and a region × commodity heatmap. |
| **Time-Series Forecasting** | Trains Prophet, ARIMA and SARIMA on the same series, scores them on a held-out period (RMSE, MAE, MAPE), and forecasts 6–12 months ahead with the best model and a 95% interval. Shows the inflation the forecast implies, how each model did on months it had not seen, and a CSV download. |
| **Inflation Rate Viewer** | Month-over-month or year-over-year inflation for any region and group, with a year × month calendar that exposes seasonality. |
| **Purchasing Power** | Converts a monthly income to 2018 pesos, shows what ₱1 still buys, the income needed to match 2018, and what a fixed income has been worth over time. A **What if?** tool applies a yearly inflation rate (it starts at the latest reading), a time span of 1–10 years and an optional yearly raise, and shows what your income would be worth and what you would need to stay even. A third tab compares your income with FIES regional averages. Income is never stored. |
| **About & Methodology** | Data sources, formulas, thresholds, limitations and data-quality findings. |

The interface follows Streamlit's light or dark theme, so charts and cards adapt automatically.

## Installation

### What you need

- **Python 3.10 – 3.12** (tested on 3.12). Download it from python.org. On Windows, tick **Add python.exe to PATH**
  on the first screen of the installer.
- About **1 GB** of free disk space and an internet connection for the first install only.
- Any modern web browser.

### Step 1: Get the project

Choose one:

- **Download the ZIP:** on this page click the green **Code** button, then **Download ZIP**.
  Extract it to a **short folder**, for example `C:\presyoph`. (Very long folder paths can make the install fail on Windows.)
- **Or use Git:**

  ```bash
  git clone https://github.com/Re-Haiyan/presyoph.git
  cd presyoph
  ```

### Step 2: Install and run

**Windows:** open the project folder and double-click **`run.bat`**. Or, in a terminal inside the folder:

```bash
.\run.bat
```

**macOS / Linux:**

```bash
chmod +x run.sh
./run.sh
```

The first run takes a few minutes. It creates a virtual environment, installs the packages, builds the database
and starts the app. Your browser opens at **http://localhost:8501**. Press `Ctrl + C` in the terminal to stop it.
Next time, run the same file again and it starts in seconds.

### Manual installation (if you prefer the steps one by one)

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Check that it works

- The **Price Change Dashboard** opens and shows a latest CPI of **138.6** (October 2026) with about **7.8%** national inflation.
- Optional: run `pytest` in the project folder. You should see `73 passed`.

### If something goes wrong

| Problem | Fix |
| --- | --- |
| `python` is not recognised, or opens the Microsoft Store | Reinstall Python with **Add python.exe to PATH** ticked, then turn off the `python` entry in Windows Settings → Apps → Advanced app settings → App execution aliases. |
| Install fails with `No such file or directory` and mentions long paths | Move the project to a short folder such as `C:\presyoph` and run it again. |
| `pip install` fails on `prophet` | Use Python 3.10–3.12 and upgrade pip first: `python -m pip install --upgrade pip`. |
| Port 8501 is already in use | Close the other copy, or start with `streamlit run app.py --server.port 8600`. |
| The page is blank at first | Wait about 20 seconds on first load, then refresh. |
| The forecast page is slow the first time | Normal: three models are trained once, then the result is cached. |

The SQLite database (`presyoph.db`) is built automatically from the CSV files in `data/` on first run and
rebuilt whenever those files change. More detail, including deployment to Streamlit Community Cloud and
using your own data, is in [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Data

| File | Source | Contents |
| --- | --- | --- |
| `data/PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv` | PSA OpenSTAT | Monthly CPI (2018 = 100), Jan 2018 – Oct 2026, Philippines + 18 regions (including the Negros Island Region) × 13 commodity groups + All Items (28,196 records) |
| `data/PH_FIES_Income_Expenditure_2023_clean.csv` | PSA 2023 FIES | Average annual family income and expenditure for the Philippines and 17 regions (18 rows) |
| `data/ph_regions.geojson` | [faeldon/philippines-json-maps](https://github.com/faeldon/philippines-json-maps) (MIT) | Simplified boundaries of the 18 regions for the map (247 KB). Licence text in `data/ph_regions.LICENSE.txt` |

Both statistics files are aggregate public data. No personal or household-level records are used.

### Keeping the data current

The CPI file was checked against PSA OpenSTAT's official table (*Consumer Price Index for All Income
Households by Commodity Group, 2018=100*) on 7 November 2026: **26,191 of 26,208 values matched exactly**.
PSA had revised 17 values for June–August 2026, published September and October 2026, and added the Negros
Island Region as a separate region. All of that is now in the file. To refresh it again when PSA publishes
new months:

```bash
python scripts/update_cpi_from_psa.py --dry-run   # see what would change
python scripts/update_cpi_from_psa.py             # write the new CSV
```

The script prints how many values were revised and which months are new. Restart the app afterwards and the
database rebuilds itself. The benchmark (`scripts/evaluate_models.py`) can then be re-run.

### Negros Island Region

PSA now reports the Negros Island Region (NIR: Negros Occidental, Negros Oriental, Siquijor) separately, and
its Regions VI and VII exclude those provinces. The app follows PSA, so NIR is a region of its own in the data
and on the map. The 2023 FIES survey predates NIR, so it has no income benchmark and the calculator says so.
The FIES benchmarks for Regions VI and VII still include the Negros provinces.
`scripts/build_region_map.py` rebuilds the map file (`pip install shapely`; the app does not need it). If the
map file is missing, the app falls back to a schematic tile map.

### Data-quality finding

**Financial Services never moves.** PSA's own national index for it has had only three values since 2018:
100.0, then 143.3 from April 2021, then 142.4 from January 2024 (the regional series are flat for 34–67
months). This matches PSA's published table, so it is not an error in this project's data. It means there is
no month-to-month movement to rank or forecast, so the app detects any series unchanged for 6+ months,
leaves it out of rankings, maps and forecasts, and says so on screen. That affects the 19 Financial
Services series (one per area).

## Method

- **Inflation**: YoY = CPI(t)/CPI(t−12) − 1; MoM = CPI(t)/CPI(t−1) − 1. Levels: Normal ≤ 3%, Increasing ≤ 5%, High > 5%.
- **Evaluation**: each model is trained on Jan 2018 – Dec 2025 (96 months) and tested on every later month
  (Jan – Oct 2026, 10 months, in the current data). The lowest-RMSE model is refit on all data to produce the forecast.
- **Models**: Prophet (yearly seasonality), ARIMA(1,1,1), SARIMA(1,1,1)(1,1,1)₁₂.
- **Purchasing power**: income × 100 / latest regional CPI.

## Model benchmark

`python scripts/evaluate_models.py` evaluates every area × commodity-group series that has monthly movement
(247 of 266; the 19 Financial Services series never change and are skipped). Output is in
[`results/`](results/). Trained through Dec 2025, tested on Jan – Oct 2026 (10 months):

| Model | Mean RMSE | Median RMSE | Mean MAE | Mean MAPE | Median MAPE | Selected as best |
| --- | --- | --- | --- | --- | --- | --- |
| ARIMA | 4.96 | 3.33 | 4.41 | 3.06% | 2.15% | 30 / 247 |
| Prophet | 4.99 | 3.33 | 4.50 | 3.16% | 2.18% | 60 / 247 |
| **SARIMA** | **3.84** | **2.50** | **3.38** | **2.38%** | **1.59%** | **157 / 247** |

SARIMA has the lowest error on every measure and is selected most often. ARIMA and Prophet are essentially
tied, and Prophet was less accurate than ARIMA on the headline All Items series. This is one ten-month test
window, so read it as a result for this data, not a general ranking. The app picks a model per series, so it
benefits from all three.

## Project structure

```
app.py                  Entry point: layout, navigation, sidebar
views/                  One module per page (dashboard, forecasting, inflation, purchasing_power, about)
ui/charts.py            All Plotly figures, with one shared minimal style
analytics/
  calculations.py       Inflation, classification and purchasing-power math
  forecasting.py        Prophet / ARIMA / SARIMA, evaluation and forecasting
  quality.py            Detects series with no month-to-month movement
  insights.py           One-line takeaways generated from the data
database/db_manager.py  SQLite loading, validation and queries
data/                   Cleaned PSA CSV files
scripts/                PSA data refresh, batch model benchmark, region map builder, labelled demo workflow
results/                Benchmark output
docs/                   Project paper (DOCX and PDF)
tests/                  pytest suite
.streamlit/config.toml  Theme settings
```

## Testing

```bash
pytest
```

73 tests cover the calculations (including the what-if scenarios), database loading, forecasting,
data-quality checks, charts, the map data and a smoke test of every page. CI runs the same suite on every push and pull request.

## Limitations

- FIES values are from 2023 and do not reflect later income changes; the calculator states the survey year. They
  predate the Negros Island Region, which therefore has no income benchmark.
- Forecasts extrapolate past patterns and cannot anticipate shocks. Read the interval, not only the central line.
  The what-if tool is a steady-rate scenario, not a forecast.
- Map boundaries are simplified; there are no city-, barangay- or store-level prices.
- Series that never change (Financial Services) are excluded from rankings, maps and forecasts.

## Authors

- Mark Rhean Caballero - Project Leader
- Earl Naniong - Member
- Joenhel Pico - Member

Instructor: Dr. Caren A. Pacol

## License

The source code is released under the [MIT License](LICENSE). The data files are not covered by it:
the CPI and FIES statistics come from the PSA (see below), and the map boundaries are MIT-licensed
separately by their author (`data/ph_regions.LICENSE.txt`).

## Data attribution

Source data: Philippine Statistics Authority (OpenSTAT and FIES), cleaned and reshaped for this project.
Check the PSA's terms of use before redistributing the data.
