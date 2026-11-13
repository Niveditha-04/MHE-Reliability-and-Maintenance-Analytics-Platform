# MHE Reliability and Maintenance Analytics

## What this is

A DuckDB pipeline for conveyor and sorter reliability. It measures failures,
maintenance activity, and reliability over the observation window.

## Data

The Microsoft Azure Predictive Maintenance dataset contains 100 machines,
hourly telemetry, errors, component replacements, and failures. Download the
five CSVs and extract them into `data/raw/`.
[Dataset](https://www.kaggle.com/datasets/arnabbiswas1/microsoft-azure-predictive-maintenance)

## Simulated and assumed items

- Site and equipment type are simulated.
- Parts, labor, and hourly downtime costs are assumed.
- Availability and MTBF use a 12-hour assumed repair duration bounded by
  event timing. The MTTR proxy measures the next maintenance interval.
- Planned replacement share is a PM compliance proxy.

## Tools

Python, DuckDB, SQL, pandas, NumPy, scikit-learn, and Git.

## Structure

- `sql/` defines tables, checks, KPIs, and dashboard views.
- `src/` contains the loader, quality runner, KPI builder, and exporter.
- `tests/` contains reconciliation and fixture checks.
- `docs/` contains data notes and KPI definitions.
- `data/processed/` contains the local database and dashboard CSVs.

## How to run

Full dataset, with Python 3.14.4.

```sh
python -m pip install -r requirements.txt
python src/load_data.py
python src/run_quality.py
python src/train_model.py
python src/score_machines.py
python src/forecast_parts.py
python src/build_kpis.py
python src/export_bi.py
python tests/test_quality.py
python tests/test_kpis.py
python tests/test_bi.py
python tests/test_model.py
python tests/test_truncation.py
python tests/test_forecast.py
python src/weekly_report.py
```

Sample pipeline and report.

```sh
python -m pip install -r requirements.txt
python src/weekly_report.py --sample
python tests/test_report.py
```

The sample command loads the synthetic CSVs into a temporary database,
runs quality checks, builds features, trains and scores the model, builds
KPI views, forecasts demand, and exports the dashboard tables. The full
report command uses the existing full-data model and forecast tables.

GitHub Actions runs the sample every Monday at 06:00 UTC and on manual
dispatch. The artifact contains the weekly report and quality results.
Local sample reports are written to `reports/sample/`. Snapshots compare
report runs on static input.

## Results

- 761 component failures and 2,879 in-window replacements.
- Availability proxy based on assumed repair hours is 99.02%.
- MTBF based on assumed repair hours is 1,139.80 hours.
- Planned replacement share is 74.19%.
- Assumed total cost is 5,490,630.
- Test average precision is 0.997519 for boosting and 0.828968 for logistic regression.
- At the selected threshold, 116 alerts cover 114 of 114 test failure events.
- The parts forecast uses 51 full weeks in 2015.

## Dashboard

Four pages cover network reliability, site and equipment drill-down with a
network top 10, component failures and assumed costs, and maintenance and
spare parts. Labels identify the simulated site mapping, assumed repair
hours, assumed downtime cost per hour, and proxy measures.

## Limits

The source covers one year and has no repair durations or actual costs.
The any-error rule also catches all 114 test events. Boosting fires fewer alerts at the same recall.
Average precision for failures 24 to 48 hours ahead is 0.83. The signal extends beyond the next 24 hours.
The validation comparison covers two boosting settings.
The data is synthetic. The model score makes no claim about real equipment.
Site and equipment groupings are simulated.

Alerts cost 100 and a missed event costs at least 1,000. Event scores are
well separated from other hours. One threshold wins at every tested cost
ratio. The search found no cost trade-off.

The 24-hour label concentrates lead times near 24 hours. The median is
24 hours, the range is 8 to 26 hours, and no event had 48 hours of lead.

Within models 1 to 3, half-year machine failure ranks have Spearman
correlations of 0.03 to 0.10. Model differences account for much of the
pooled 0.46. The ranking is labeled “failures plus alert history, Sep to Oct”.

The 80% forecast intervals cover 83.3% of comp2 and 78.6% of comp3
backtest observations for the selected methods.
