# Installation Guide

This guide takes you from a fresh computer to a running PresyoPH dashboard. It takes about 10 minutes,
most of it downloading packages.

## 1. Requirements

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.10 – 3.12 | Tested on 3.12. Newer versions may lack prebuilt packages for Prophet. |
| Git | any recent | Only needed to clone the repository. You can also download a ZIP. |
| Disk space | ~1 GB | Mostly the Python packages. |
| Internet | first install only | The app itself runs offline after installation. |
| Browser | any modern one | Chrome, Edge, Firefox or Safari. |

Check what you already have:

```bash
python --version
git --version
```

If `python` is not found on Windows, install Python 3.12 from <https://www.python.org/downloads/> and tick
**Add python.exe to PATH** on the first screen of the installer. Then close and reopen your terminal.

## 2. Get the code

```bash
git clone https://github.com/Re-Haiyan/presyoph.git
cd presyoph
```

The repository is private. Sign in first with `gh auth login` (GitHub CLI) or use a personal access token
when Git asks for a password. Without Git, open the repository page, choose **Code → Download ZIP**, extract
it, and open a terminal in the extracted folder.

## 3. Quick install (recommended)

**Windows:** double-click `run.bat`, or run it in a terminal (the `.\` is required in PowerShell):

```bash
.\run.bat
```

**macOS / Linux:**

```bash
chmod +x run.sh
./run.sh
```

The script creates a virtual environment, installs the packages, builds the database, and starts the app.
Your browser opens at <http://localhost:8501>. The first start takes a little longer while the database is built.

## 4. Manual install

Use this if you prefer to see each step.

**Windows (PowerShell or Command Prompt)**

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

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once,
or use Command Prompt instead.

## 5. Check that it works

1. The terminal shows `Local URL: http://localhost:8501`.
2. The **Price Change Dashboard** opens and shows **136.4** as the latest CPI for the Philippines
   (August 2026) with about **6.15%** national inflation.
3. In **Time-Series Forecasting**, a forecast chart appears within about 10 seconds. The first run for each
   series trains three models, and later runs are instant.

Run the automated tests to confirm the install is healthy:

```bash
pytest
```

You should see `56 passed`.

## 6. Everyday use

| Task | Command |
| --- | --- |
| Start the app | `.\run.bat` (Windows) or `./run.sh`, or `streamlit run app.py` with the environment active |
| Stop the app | Press `Ctrl + C` in the terminal |
| Use another port | `streamlit run app.py --server.port 8600` |
| Rebuild the database | Delete `presyoph.db` and restart. It is rebuilt from `data/` automatically. |
| Re-run the model benchmark | `python scripts/evaluate_models.py` (takes a few minutes, writes to `results/`) |
| Update to the latest version | `git pull`, then `pip install -r requirements.txt` |

## 7. Using your own data

Replace the two files in `data/` with updated PSA exports that keep the same column names:

- `PH_CPI_ByRegion_MajorGroups_2018_2026_clean.csv`: `date, region_code, commodity_code, commodity_group, cpi_value`
- `PH_FIES_Income_Expenditure_2023_clean.csv`: `region_code, region_name, avg_annual_income_php_thousands, avg_annual_expenditure_php_thousands, survey_year`

The app notices the change and rebuilds the database on the next start. It stops with a clear message if a
required column is missing.

## 8. Deploy online (optional)

To share the dashboard with others, use [Streamlit Community Cloud](https://streamlit.io/cloud), which is free
and works with private GitHub repositories.

1. Sign in with GitHub and choose **New app**.
2. Pick the `Re-Haiyan/presyoph` repository, branch `main`, and main file `app.py`.
3. Under **Advanced settings**, choose Python 3.12.
4. Deploy. The first build takes a few minutes while Prophet installs.

The database is built on first launch, so nothing else needs to be uploaded.

## 9. Troubleshooting

| Problem | Fix |
| --- | --- |
| `python` is not recognised, or opens the Microsoft Store | Reinstall Python with **Add to PATH** ticked, then turn off the `python` entry under Settings → Apps → Advanced app settings → App execution aliases. You can also use `py -3.12` on Windows. |
| `pip install` fails with `No such file or directory` and mentions long paths | Windows limits path length. Move the project to a short folder such as `C:\presyoph` and run it again, or enable long paths (see <https://pip.pypa.io/warnings/enable-long-paths>). |
| `pip install` fails on `prophet` | Use Python 3.10–3.12 and upgrade pip first: `python -m pip install --upgrade pip`. Without Prophet the app still runs and compares ARIMA and SARIMA only. |
| `No module named 'views'` or similar | Run the commands from the project folder (the one containing `app.py`). |
| Port 8501 is already in use | Close the other app, or start with `--server.port 8600`. |
| The page is blank or keeps spinning | Wait about 20 seconds on first load, then refresh. Check the terminal for errors. |
| Forecast page is slow the first time | Normal: three models are trained. The result is cached for the session. |
| Want a fixed light or dark theme | Add `base = "light"` or `base = "dark"` under `[theme]` in `.streamlit/config.toml`. By default the app follows your system setting. |
| `database is locked` | Close any other copy of the app that is using the same `presyoph.db`. |
| Financial Services shows a notice instead of data | Expected. Its CPI is frozen in the source data, so it is excluded. See the README. |

Still stuck? Open an issue at <https://github.com/Re-Haiyan/presyoph/issues> with your operating system,
Python version (`python --version`) and the full error text.

## 10. Uninstall

Close the app, then delete the project folder. Everything, including the virtual environment, lives inside it.
