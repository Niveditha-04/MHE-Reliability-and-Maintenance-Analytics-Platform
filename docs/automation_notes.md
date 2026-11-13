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
the generated data.

The source dataset's redistribution terms could not be verified from the
Kaggle listing. The sample generator uses no source CSV rows.

The artifact contains the Markdown report and quality CSV. The workflow
cache holds two dated KPI snapshots. A missing prior-week snapshot gives
an unavailable change. With static input and calculations, comparable
runs give zero change. The snapshot tracks report runs and does not
represent newly observed equipment data.
