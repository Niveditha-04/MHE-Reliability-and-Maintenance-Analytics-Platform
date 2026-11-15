# Source data

The five CSVs come from the Microsoft Azure Predictive Maintenance dataset.
The loader reads the extracted files from `data/raw/`.
[Microsoft Azure Predictive Maintenance on Kaggle](https://www.kaggle.com/datasets/arnabbiswas1/microsoft-azure-predictive-maintenance)

| CSV | Rows | What one row represents |
| --- | ---: | --- |
| `PdM_telemetry.csv` | 876,100 | An hourly voltage, rotation speed, pressure, and vibration reading for one machine. |
| `PdM_errors.csv` | 3,919 | An error of type `errorID` logged for one machine at a timestamp. |
| `PdM_maint.csv` | 3,286 | A replacement of component `comp` on one machine at a timestamp. |
| `PdM_failures.csv` | 761 | A failure of component `failure` on one machine at a timestamp. |
| `PdM_machines.csv` | 100 | A machine with its model and age. |

Event tables join to machines on `machineID`. Events align with telemetry
on `machineID` and `datetime`. Failure and replacement matches also use the
component (`failure` to `comp`). Aggregation to one row per machine-hour
preserves the telemetry grain.

| Table | Earliest timestamp | Latest timestamp |
| --- | --- | --- |
| Telemetry | 2015-01-01 06:00:00 | 2016-01-01 06:00:00 |
| Errors | 2015-01-01 06:00:00 | 2016-01-01 05:00:00 |
| Failures | 2015-01-02 03:00:00 | 2015-12-31 06:00:00 |
| Maintenance | 2014-06-01 06:00:00 | 2016-01-01 06:00:00 |

Each machine has 8,761 hourly telemetry rows, including both endpoints.
Source timestamps carry no time zone. Maintenance starts in June 2014,
before telemetry. The action rules use 2014 replacements as history.
Replacement KPI counts exclude them.

The 761 failure rows represent component failures. Two components can fail on
the same machine at the same time. Failure counts use the machine, timestamp,
and component together.

The inspection command, `python3 src/inspect_data.py`, runs from the
project root with Python 3.11 or later. It prints the shape, column names, parsed types, timestamp range,
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

Maintenance records occur at scheduled intervals of about 15 days. The
time to the next record measures the interval between scheduled records.

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

Two events have downtime below 12 hours, both from 03:00 to 06:00 on 2015-01-02. Machine 73 had its next failure and maintenance at 06:00. Machine 79 had its next maintenance at 06:00.

The GitHub Actions sample contains the full hourly grid for five
synthetic machines.
