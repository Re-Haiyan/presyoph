"""Run PresyoPH's analytical workflow step by step, with labelled output (no dashboard).

    python scripts/demo_workflow.py
    python scripts/demo_workflow.py --region NCR --group "Transport" --horizon 12

Each STEP prints what it does and the real result, so the workflow can be shown live:
load data -> check quality -> compute inflation -> split train/test -> compare three models
-> forecast -> purchasing power. It uses the same functions as the app, so the output is the app's output.
"""

import argparse
import logging
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analytics.calculations import (  # noqa: E402
    calculate_inflation_series,
    calculate_purchasing_power,
    classify_inflation_level,
    future_real_value,
    income_needed_for_same_power,
)
from analytics.forecasting import (  # noqa: E402
    add_forecast_inflation,
    build_forecast,
    evaluate_models,
    prepare_series,
    select_best_model,
    split_train_test,
)
from analytics.quality import find_stale_series  # noqa: E402
from database.db_manager import get_cpi_data, get_data_coverage, initialize_db  # noqa: E402

# Prophet's backend logs a line per model fit; hide them so the labelled steps stay readable.
for noisy in ("cmdstanpy", "prophet"):
    logging.getLogger(noisy).disabled = True


def step(number, title):
    print(f"\n{'=' * 78}\nSTEP {number}: {title}\n{'=' * 78}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default="PH", help="region code, e.g. PH, NCR, R4A, NIR")
    parser.add_argument("--group", default="All Items", help="commodity group")
    parser.add_argument("--horizon", type=int, default=6, help="forecast months (6-12)")
    parser.add_argument("--income", type=float, default=30000.0, help="monthly income for the purchasing power step")
    args = parser.parse_args()

    step(1, "LOAD THE DATA (PSA CPI, 2018 = 100)")
    initialize_db()
    first, last, rows = get_data_coverage()
    all_data = get_cpi_data()
    print(f"Records:          {rows:,}")
    print(f"Months covered:   {first:%b %Y} to {last:%b %Y}")
    print(f"Areas:            {all_data['region_code'].nunique()} (Philippines + regions)")
    print(f"Series per area:  {all_data['commodity_group'].nunique()} (13 commodity groups + All Items)")

    step(2, "DATA-QUALITY CHECK (series with no month-to-month movement)")
    stale = find_stale_series(all_data)
    print(f"Series unchanged for 6+ months: {len(stale)}")
    if len(stale):
        print(stale.groupby("commodity_group")["flat_months"].agg(["count", "min", "max"])
              .rename(columns={"count": "areas", "min": "min_months_flat", "max": "max_months_flat"}).to_string())
        print("-> These are excluded from rankings, maps, forecasts and the model comparison.")
    flat = stale[(stale["region_code"] == args.region) & (stale["commodity_group"] == args.group)]
    if not flat.empty:
        print(f"\nThe series you chose ({args.region}, {args.group}) never changes, so it cannot be forecast.")
        return 1

    step(3, f"INFLATION RATES for {args.region} / {args.group}")
    raw = get_cpi_data(region_code=args.region, commodity_group=args.group)
    inflation = calculate_inflation_series(raw)
    latest = inflation.iloc[-1]
    level, _ = classify_inflation_level(latest["yoy_inflation"])
    print(f"Latest month:        {latest['date']:%B %Y}")
    print(f"CPI:                 {latest['cpi_value']:.1f}")
    print(f"Year-over-year:      {latest['yoy_inflation']:.2f}%   ({level})")
    print(f"Month-over-month:    {latest['mom_inflation']:.2f}%")

    step(4, "TRAIN / TEST SPLIT (models never see the test months)")
    series = prepare_series(raw)
    train, test = split_train_test(series)
    print(f"Training:  {train.index[0]:%b %Y} to {train.index[-1]:%b %Y}  ({len(train)} months)")
    print(f"Testing:   {test.index[0]:%b %Y} to {test.index[-1]:%b %Y}  ({len(test)} months)")

    step(5, "COMPARE THREE MODELS ON THE TEST MONTHS (ARIMA, SARIMA, Prophet)")
    results = evaluate_models(train, test)
    best = select_best_model(results)
    table = pd.DataFrame(
        [{"Model": name, "RMSE": r["rmse"], "MAE": r["mae"], "MAPE (%)": r["mape"], "Status": r["status"]}
         for name, r in results.items()]
    ).sort_values("RMSE")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\n-> Best model (lowest RMSE): {best}")
    actual = test.values
    print("\nActual vs predicted by the best model:")
    compare = pd.DataFrame({"month": test.index.strftime("%b %Y"), "actual": actual,
                            "predicted": results[best]["predictions"]})
    compare["error"] = compare["predicted"] - compare["actual"]
    print(compare.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    step(6, f"FORECAST the next {args.horizon} months with {best} (refit on all data)")
    forecast = add_forecast_inflation(series, build_forecast(series, best, args.horizon))
    forecast["month"] = forecast["date"].dt.strftime("%b %Y")
    shown = forecast[["month", "forecast_cpi", "lower_ci", "upper_ci", "forecast_yoy_inflation"]]
    shown.columns = ["month", "forecast CPI", "lower 95%", "upper 95%", "implied YoY %"]
    print(shown.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    step(7, f"PURCHASING POWER for a monthly income of P{args.income:,.0f}")
    all_items = get_cpi_data(region_code=args.region, commodity_group="All Items")
    cpi_now = all_items.sort_values("date")["cpi_value"].iloc[-1]
    real, peso = calculate_purchasing_power(args.income, cpi_now)
    print(f"Latest CPI ({args.region}, All Items): {cpi_now:.1f}")
    print(f"P1.00 today buys what P{peso:.2f} bought in 2018")
    print(f"P{args.income:,.0f} today equals P{real:,.0f} in 2018 pesos")
    yoy = float((all_items.sort_values('date')['cpi_value'].iloc[-1] / all_items.sort_values('date')['cpi_value'].iloc[-13] - 1) * 100)
    print(f"\nWhat-if: inflation stays at today's {yoy:.1f}% a year for 3 years")
    print(f"  Income in today's pesos after 3 years: P{future_real_value(args.income, yoy, 3):,.0f}")
    print(f"  Income needed to stay even:            P{income_needed_for_same_power(args.income, yoy, 3):,.0f}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
