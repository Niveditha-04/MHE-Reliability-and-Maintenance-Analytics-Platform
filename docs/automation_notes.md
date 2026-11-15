# Weekly reporting

The workflow runs on Mondays at 06:00 UTC and supports manual runs.
It loads five synthetic machines into a temporary database and runs the
quality checks before training. Warnings are counted in the report.
A failed check exits nonzero and marks the report failed.

The sample contains 43,805 hourly telemetry rows, including both endpoints
for each machine. Machine IDs come from the simulated mapping. All sensor
values, model assignments, and events are generated. The training,
validation, and test dates match the full-data pipeline. The permutation
test uses at most the available validation rows. Sample results describe
the generated data. Sample failures are evenly spaced within each machine,
with an error 24 hours before each one. The fixture encodes the failure
signal, so model scores on the sample are near perfect and say nothing
about real data. Ties in the top five come from the generator.

The Kaggle dataset page lists the license as Unknown (13 Nov 2026).
The repository contains no source CSV rows.

Full mode checks data quality, refreshes KPI views, and exports dashboard
CSVs from the existing model and forecast tables. The commands
`python src/train_model.py`, `python src/score_machines.py`, and
`python src/forecast_parts.py` rebuild those tables before the full report.

The artifact contains the Markdown report and quality CSV. The workflow
cache holds two dated KPI snapshots. A missing prior-week snapshot gives
an unavailable change. The workflow cache can expire after seven days
without access. The next change then shows “Unavailable.” Comparable
runs on static input with the same calculations give zero change. The
snapshot tracks report runs on the same observation window.
