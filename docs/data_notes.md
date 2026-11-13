# Source data

The five CSVs are from the Microsoft Azure Predictive Maintenance dataset. On
Kaggle, open the dataset, select Download, and extract the five CSVs into
`data/raw/`. If telemetry comes in a separate ZIP, extract that file too.
[Microsoft Azure Predictive Maintenance on Kaggle](https://www.kaggle.com/datasets/arnabbiswas1/microsoft-azure-predictive-maintenance)

| CSV | Rows | What one row represents |
| --- | ---: | --- |
| `PdM_telemetry.csv` | 876,100 | An hourly voltage, rotation speed, pressure, and vibration reading for one machine. |
| `PdM_errors.csv` | 3,919 | An error of type `errorID` logged for one machine at a timestamp. |
| `PdM_maint.csv` | 3,286 | A replacement of component `comp` on one machine at a timestamp. |
| `PdM_failures.csv` | 761 | A failure of component `failure` on one machine at a timestamp. |
| `PdM_machines.csv` | 100 | A machine with its model and age. |

Join each event table to machines on `machineID`. To align events with
telemetry at the same hour, use both `machineID` and `datetime`. Use the
component as well when matching a failure to a replacement (`failure` to
`comp`). Aggregate events to one row per machine-hour before joining them to
hourly telemetry if the output needs to keep that grain.

| Table | Earliest timestamp | Latest timestamp |
| --- | --- | --- |
| Telemetry | 2015-01-01 06:00:00 | 2016-01-01 06:00:00 |
| Errors | 2015-01-01 06:00:00 | 2016-01-01 05:00:00 |
| Failures | 2015-01-02 03:00:00 | 2015-12-31 06:00:00 |
| Maintenance | 2014-06-01 06:00:00 | 2016-01-01 06:00:00 |

Each machine has 8,761 hourly telemetry rows, including both endpoints.
Source timestamps carry no time zone. Maintenance starts in June 2014,
before telemetry. Use 2014 replacements only for hours-since-last-replacement
features and exclude them from 2015 KPIs.

The 761 failure rows represent component failures. Two components can fail on
the same machine at the same time. Count failures by machine, timestamp, and
failure component together.

Run `python3 src/inspect_data.py` from the project root with Python 3.11
or later. It prints the shape, column names, parsed types, timestamp range,
and five sample rows per file. It checks parsed row counts against file
line counts after allowing for each header.

## Failures without a matching replacement

All 18 unmatched component failures occurred at 2015-01-02 03:00:00.
Five have maintenance on the same machine within 48 hours before or after
the failure. Thirteen have none. Two of the five have a replacement for the
failed component 21 hours earlier. None has a replacement for any component
at the failure timestamp. The raw and loaded machine, timestamp, and component
keys match exactly for all 761 failure and 3,286 maintenance rows. The raw
component codes are lowercase and have no leading or trailing spaces.

[Unmatched failures and nearby maintenance](../reports/unmatched_failures.csv)

Maintenance records follow a fixed cycle of about 15 days, so the interval to the next record is a schedule interval, not a repair time.

Sixteen of the 18 unmatched failures have their latest earlier replacement
for the same machine and component before the window. Machines 17 (comp4)
and 51 (comp1) have their latest earlier replacement at the window start,
2015-01-01 06:00:00.

[Latest earlier replacement for all 18 failures](../reports/unmatched_failure_history.csv)

The source does not explain why these 18 failures lack a replacement at the
failure timestamp.

## Failure spread by simulated site

| Site | Minimum per machine | Median per machine | Maximum per machine | Top three machines' share |
| --- | ---: | ---: | ---: | ---: |
| DC-A | 0 | 7 | 15 | 41 / 150 (27.33%) |
| DC-B | 2 | 7.5 | 15 | 41 / 155 (26.45%) |
| DC-C | 2 | 7 | 12 | 33 / 137 (24.09%) |
| DC-D | 0 | 7.5 | 13 | 35 / 141 (24.82%) |
| DC-E | 3 | 8.5 | 19 | 49 / 178 (27.53%) |
