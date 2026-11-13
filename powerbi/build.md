# Power BI Desktop build

Run `python src/export_bi.py` after loading the database and building the
KPI views. Copy the CSVs in `data/processed/` to Windows. The report uses
monthly aggregates and asset ranks.

## Model

Disable Auto date/time in Options before importing the seven CSVs.

Import `dim_machine`, `dim_component`, `vw_machine_monthly`,
`vw_events_monthly`, `vw_cost_detail`, `vw_top_assets`, and `vw_cost_sensitivity`. Use whole numbers
for IDs and counts, dates for month, and decimal numbers for rates and hours.
Create a month table with one row per month for the shared monthly axis across the three facts.

```dax
Month = DISTINCT(vw_machine_monthly[reporting_month])
```

Use one-to-many, single-direction relationships from dimensions to facts.
Keep the network leaderboard independent of the slicers. Use its exported
site, model, and equipment labels in the leaderboard itself.

| From | To | Key |
| --- | --- | --- |
| dim_machine | vw_machine_monthly | machine_id |
| dim_machine | vw_events_monthly | machine_id |
| dim_machine | vw_cost_detail | machine_id |
| dim_component | vw_events_monthly | component |
| dim_component | vw_cost_detail | component |
| Month | vw_machine_monthly | reporting_month |
| Month | vw_events_monthly | reporting_month |
| Month | vw_cost_detail | reporting_month |

Place the component slicer only on pages 3 and 4. Sync slicers using `dim_machine[site_id]` and `dim_machine[model]`.

## Measures

```dax
Failures = SUM(vw_machine_monthly[failures])
Operating Hours = SUM(vw_machine_monthly[operating_hours])
Downtime Hours = SUM(vw_machine_monthly[downtime_hours])
Failure Rate per 1000h = DIVIDE(1000 * [Failures], [Operating Hours])
Reactive Share = DIVIDE(SUM(vw_machine_monthly[reactive]),
    SUM(vw_machine_monthly[reactive]) + SUM(vw_machine_monthly[planned]))
Availability Proxy (Assumed Repair Hours) =
    DIVIDE(SUM(vw_machine_monthly[operating_hours]), SUM(vw_machine_monthly[window_hours]))
MTBF (Assumed Repair Hours) =
    DIVIDE([Operating Hours], [Failures])
MTTR Proxy (Maintenance Interval) =
    DIVIDE(SUM(vw_machine_monthly[mttr_total]), SUM(vw_machine_monthly[mttr_events]))
Planned Share Proxy =
    DIVIDE(SUM(vw_machine_monthly[planned]), SUM(vw_machine_monthly[planned]) + SUM(vw_machine_monthly[reactive]))
Component Failures = SUM(vw_events_monthly[failures])
Reactive Replacements = SUM(vw_events_monthly[reactive])
Planned Replacements = SUM(vw_events_monthly[planned])
Assumed Replacement Cost = SUM(vw_cost_detail[assumed_replacement_cost])
Assumed Downtime Cost = SUM(vw_cost_detail[assumed_downtime_cost])
Assumed Total Cost = [Assumed Replacement Cost] + [Assumed Downtime Cost]
```

| Measure | Meaning |
| --- | --- |
| Failures | Component failures in the selected fleet and months. |
| Operating Hours | Observed window hours less assumed downtime. |
| Downtime Hours | Sum of downtime based on assumed repair hours. |
| Failure Rate per 1000h | Component failures per 1,000 operating hours. |
| Reactive Share | Reactive replacements divided by all replacements. |
| Availability Proxy (Assumed Repair Hours) | Operating hours divided by exposure. |
| MTBF (Assumed Repair Hours) | Operating hours per component failure. |
| MTTR Proxy (Maintenance Interval) | Average next maintenance interval for events with a later record. |
| Planned Share Proxy | Planned replacements divided by all replacements. |
| Component Failures | Failure count by component and month. |
| Reactive Replacements | Replacements with an exact failure match. |
| Planned Replacements | Remaining replacements. |
| Assumed Replacement Cost | Assumed parts and labor. |
| Assumed Downtime Cost | Assumed cost of event downtime. |
| Assumed Total Cost | Combined replacement and downtime costs. |

## Pages

1. Network overview. Lead with model failures and the five KPI cards. Include
   the site breakdown labeled simulated site mapping.
2. Site and equipment drill-down. Use site, equipment type, and machine from
   the machine dimension. Plot monthly KPIs and add the asset table. Filter
   network_position to 10 or less and sort ascending. Label it “Network ranking, not filtered by slicers.”
3. Failure and cost trends. Chart component failures by month. Plot Assumed
   Replacement Cost and Assumed Downtime Cost as two series. Label every
   cost visual “assumed repair hours and assumed downtime cost per hour.”
   Chart assumed total cost by repair hours using the disconnected
   `vw_cost_sensitivity` CSV.
4. Maintenance and spare parts. Chart planned and reactive replacements by
   component. Reserve a space for forecast demand.

Use a single palette. Label downtime-based visuals assumed repair hours.
Label the maintenance interval and planned share as proxies.

### Network cost sensitivity

Assumed repair hours and assumed downtime cost per hour (500).

| Repair h | Assumed replacement cost | Assumed downtime cost | Assumed total cost |
| ---: | ---: | ---: | ---: |
| 4 | 1185630 | 1437000 | 2622630 |
| 8 | 1185630 | 2871000 | 4056630 |
| 12 | 1185630 | 4305000 | 5490630 |
| 24 | 1185630 | 8607000 | 9792630 |
| 48 | 1185630 | 17163000 | 18348630 |

## Verification

| Check | SQL expected | Desktop observed |
| --- | ---: | --- |
| Network MTBF | 1139.802890932983 | Pending |
| DC-A failures with slicer | 150 | Pending |
| Model 1 failures | 189 | Pending |
| comp2 failures | 259 | Pending |
| Assumed total cost | 5490630 | Pending |
| Assumed replacement cost | 1185630 | Pending |
| Assumed downtime cost | 4305000 | Pending |
| Network Top 10 order | 99, 98, 17, 22, 37, 83, 20, 71, 16, 13 | Pending |

Display MTBF to two decimal places (1,139.80). Display counts and assumed
cost totals as whole numbers.

Save the report and PDF in `powerbi/`. Capture each page in `docs/img/`
and record a short GIF showing navigation and a slicer selection.
