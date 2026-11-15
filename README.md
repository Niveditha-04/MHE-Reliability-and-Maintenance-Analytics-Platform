# MHE Reliability and Maintenance Analytics

## What this is

A DuckDB pipeline for conveyor and sorter reliability. It measures failures,
maintenance activity, and reliability over the observation window.

## Data

The Microsoft Azure Predictive Maintenance dataset contains 100 machines,
hourly telemetry, errors, component replacements, and failures. The
pipeline reads the five extracted CSVs from `data/raw/`.
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
- `tests/` contains reconciliation and fixture checks.
- `docs/` contains data notes and KPI definitions.
- `dashboard/` contains the dashboard build guide.
- `data/processed/` contains the local database and dashboard CSVs.

| Job | Scripts in `src/` |
| --- | --- |
| Source inspection | `inspect_data.py` |
| Simulated mapping | `make_mapping.py` |
| Data loader | `load_data.py` |
| Data quality | `run_quality.py` |
| Features and model training | `train_model.py` |
| Alert policy and cost | `alert_policy.py` |
| Machine scoring | `score_machines.py` |
| Parts forecast | `forecast_parts.py` |
| KPI and dashboard views | `build_kpis.py` |
| Dashboard CSV export | `export_bi.py` |
| Weekly reporting | `weekly_report.py` |
| Synthetic sample generation | `make_sample.py` |
| Model and ranking audits | `model_audit.py`, `risk_audit.py` |

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
The commands for `train_model.py`, `score_machines.py`, and
`forecast_parts.py` rebuild those tables before the full report.

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
- The test window contains 114 failure events.
- The parts forecast uses 51 full weeks in 2015.
- The top three assets are machine 99 (19 failures, score 4), machine 37
  (14 failures, score 6), and machine 83 (14 failures, score 6).

| Test policy | Alerts | Caught | Missed | Assumed cost |
| --- | ---: | ---: | ---: | ---: |
| Boosting | 116 | 114 | 0 | 11,600 |
| Any error | 587 | 114 | 0 | 58,700 |
| No alerts | 0 | 0 | 114 | 684,000 |

| Component | Forecast method | MAE, replacements |
| --- | --- | ---: |
| comp1 | 8-week mean | 2.268 |
| comp2 | 8-week mean | 3.196 |
| comp3 | 8-week mean | 3.146 |
| comp4 | 4-week mean | 2.702 |

## Dashboard

The [dashboard build guide](dashboard/build.md) is in `dashboard/`.
Tableau Public is the dashboard tool. The Network overview page shows
failures by model. The other pages are in progress. The workbook is kept
local because the dataset license is Unknown.

## Limits

- The telemetry covers one year.
- The source has no repair durations or actual costs.
- Site and equipment mappings are simulated.
- Parts, labor, and downtime costs are assumed.
- The source dataset is synthetic. The project generates the CI sample.

[Model notes](docs/model_notes.md) cover the alert threshold, lead time,
asset ranking, and forecast interval coverage.
