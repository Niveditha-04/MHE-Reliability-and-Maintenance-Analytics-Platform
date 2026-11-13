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
```

## Results

- 761 component failures and 2,879 in-window replacements.
- Availability proxy based on assumed repair hours is 99.02%.
- MTBF based on assumed repair hours is 1,139.80 hours.
- Planned replacement share is 74.19%.
- Assumed total cost is 5,490,630.
- Test average precision is 0.997519 for boosting and 0.828968 for logistic regression.
- At the selected threshold, 189 alerts cover 114 of 114 test failure events.
- The parts forecast uses 82 full weeks.

## Dashboard

Four pages cover network reliability, site and equipment drill-down with a
network top 10, component failures and assumed costs, and maintenance and
spare parts. Labels identify the simulated site mapping, assumed repair
hours, assumed downtime cost per hour, and proxy measures.

## Limits

The source covers one year and has no repair durations or actual costs.
The data is synthetic. The model score makes no claim about real equipment.
Site and equipment groupings are simulated.
