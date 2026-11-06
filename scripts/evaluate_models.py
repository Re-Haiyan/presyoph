"""Benchmark Prophet, ARIMA and SARIMA on every region x commodity-group series.

Usage:
    python scripts/evaluate_models.py                # all series
    python scripts/evaluate_models.py --scope all-items   # headline CPI only

Writes ``results/model_evaluation.csv`` (one row per series and model) and
``results/model_summary.csv`` (aggregate accuracy per model).
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from analytics.forecasting import (  # noqa: E402
    evaluate_models,
    prepare_series,
    select_best_model,
    split_train_test,
)
from analytics.quality import find_stale_series  # noqa: E402
from database.db_manager import get_cpi_data, initialize_db  # noqa: E402


def evaluate_series(args):
    region, group, frame = args
    train, test = split_train_test(prepare_series(frame))
    results = evaluate_models(train, test)
    best = select_best_model(results)
    rows = []
    for model, metrics in results.items():
        rows.append(
            {
                "region_code": region,
                "commodity_group": group,
                "model": model,
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "mape": metrics["mape"],
                "status": metrics["status"],
                "selected": model == best,
                "train_end": train.index[-1].strftime("%Y-%m"),
                "test_end": test.index[-1].strftime("%Y-%m"),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["all", "all-items"], default="all")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--out", default=os.path.join(ROOT, "results"))
    args = parser.parse_args()

    initialize_db()
    cpi = get_cpi_data()
    if args.scope == "all-items":
        cpi = cpi[cpi["commodity_group"] == "All Items"]

    # Series whose CPI is frozen for months carry no signal; scoring them would flatter every model.
    stale = {tuple(r) for r in find_stale_series(get_cpi_data())[["region_code", "commodity_group"]].values}
    jobs = [
        (region, group, frame[["date", "cpi_value"]])
        for (region, group), frame in cpi.groupby(["region_code", "commodity_group"])
        if (region, group) not in stale
    ]
    print(f"Skipping {len(stale)} stale series; evaluating {len(jobs)} series with {args.workers} workers...",
          flush=True)

    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, series_rows in enumerate(pool.map(evaluate_series, jobs), 1):
            rows.extend(series_rows)
            if i % 20 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} series done", flush=True)

    os.makedirs(args.out, exist_ok=True)
    detail = pd.DataFrame(rows)
    detail.to_csv(os.path.join(args.out, "model_evaluation.csv"), index=False)

    ok = detail[detail["status"] == "Success"]
    summary = ok.groupby("model").agg(
        series=("rmse", "size"),
        mean_rmse=("rmse", "mean"),
        median_rmse=("rmse", "median"),
        mean_mae=("mae", "mean"),
        mean_mape=("mape", "mean"),
        median_mape=("mape", "median"),
    )
    summary["times_selected"] = detail[detail["selected"]].groupby("model").size()
    summary["times_selected"] = summary["times_selected"].fillna(0).astype(int)
    summary["failures"] = detail[detail["status"] != "Success"].groupby("model").size()
    summary["failures"] = summary["failures"].fillna(0).astype(int)
    summary.round(4).to_csv(os.path.join(args.out, "model_summary.csv"))
    print(summary.round(4).to_string())


if __name__ == "__main__":
    main()
