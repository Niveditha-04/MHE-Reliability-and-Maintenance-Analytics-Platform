# Power BI Desktop build

Run `python src/export_bi.py` after loading the database and building the
KPI views. Copy the CSVs in `data/processed/` to Windows. The report uses
monthly aggregates and asset ranks.

## Model

Import `dim_machine`, `dim_component`, `vw_machine_monthly`,
`vw_events_monthly`, `vw_cost_detail`, and `vw_top_assets`. Use whole numbers
for IDs and counts, dates for month, and decimal numbers for rates and hours.
Create a month table with one row per month.

```dax
Month = DISTINCT(vw_machine_monthly[month])
```

Use one-to-many, single-direction relationships from dimensions to facts.

| From | To | Key |
| --- | --- | --- |
| dim_machine | vw_machine_monthly, vw_events_monthly, vw_cost_detail, vw_top_assets | machine_id |
| dim_component | vw_events_monthly, vw_cost_detail | component |
| Month | vw_machine_monthly, vw_events_monthly, vw_cost_detail | month |

Sync slicers using `dim_machine[site_id]` and `dim_machine[model]`.

## Measures

```dax
Failures = SUM(vw_machine_monthly[failures])
Availability Proxy (Assumed Repair Hours) =
    DIVIDE(SUM(vw_machine_monthly[operating_hours]), SUM(vw_machine_monthly[window_hours]))
MTBF (Assumed Repair Hours) =
    DIVIDE(SUM(vw_machine_monthly[operating_hours]), [Failures])
Maintenance Interval Proxy =
    DIVIDE(SUM(vw_machine_monthly[mttr_total]), SUM(vw_machine_monthly[mttr_events]))
Planned Share Proxy =
    DIVIDE(SUM(vw_machine_monthly[planned]), SUM(vw_machine_monthly[planned]) + SUM(vw_machine_monthly[reactive]))
Component Failures = SUM(vw_events_monthly[failures])
Reactive Replacements = SUM(vw_events_monthly[reactive])
Planned Replacements = SUM(vw_events_monthly[planned])
Assumed Replacement Cost = SUM(vw_cost_detail[assumed_replacement_cost])
Assumed Downtime Cost = SUM(vw_cost_detail[assumed_downtime_cost])
Assumed Total Cost = [Assumed Replacement Cost] + [Assumed Downtime Cost]
Asset Position =
    VAR Asset = SELECTEDVALUE(vw_top_assets[machine_id])
    VAR Score = SELECTEDVALUE(vw_top_assets[risk_score])
    VAR FailuresForAsset = SELECTEDVALUE(vw_top_assets[failures])
    RETURN IF(
        NOT ISBLANK(Asset),
        1 + COUNTROWS(FILTER(
            ALLSELECTED(vw_top_assets),
            vw_top_assets[risk_score] < Score ||
            (vw_top_assets[risk_score] = Score &&
                (vw_top_assets[failures] > FailuresForAsset ||
                    (vw_top_assets[failures] = FailuresForAsset && vw_top_assets[machine_id] < Asset)))
        ))
    )
```

| Measure | Meaning |
| --- | --- |
| Failures | Component failures in the selected fleet and months. |
| Availability Proxy (Assumed Repair Hours) | Operating hours divided by exposure. |
| MTBF (Assumed Repair Hours) | Operating hours per component failure. |
| Maintenance Interval Proxy | Average next maintenance interval for events with a later record. |
| Planned Share Proxy | Planned replacements divided by all replacements. |
| Component Failures | Failure count by component and month. |
| Reactive Replacements | Replacements with an exact failure match. |
| Planned Replacements | Remaining replacements. |
| Assumed Replacement Cost | Assumed parts and labor. |
| Assumed Downtime Cost | Assumed cost of event downtime. |
| Assumed Total Cost | Combined replacement and downtime costs. |
| Asset Position | Fleet risk order within the selected site and model. |

## Pages

1. Network overview. Lead with model failures and the five KPI cards. Include
   the site breakdown labeled simulated site mapping.
2. Site and equipment drill-down. Use site, equipment type, and machine from
   the machine dimension. Plot monthly KPIs and add the asset table. Filter
   Asset Position to 10 or less and sort ascending.
3. Failure and cost trends. Chart component failures and assumed costs by
   month. Include assumed in the title of each cost visual.
4. Maintenance and spare parts. Chart planned and reactive replacements by
   component. Reserve a space for forecast demand.

Use a single palette. Label downtime-based visuals assumed repair hours.
Label the maintenance interval and planned share as proxies.

## Verification

| Check | SQL expected | Desktop observed |
| --- | ---: | --- |
| Network MTBF | 1139.802890932983 | Pending |
| DC-A failures with slicer | 150 | Pending |
| Model 1 failures | 189 | Pending |
| comp2 failures | 259 | Pending |
| Assumed total cost | 5490630 | Pending |

The unfiltered asset order is 99, 98, 17, 22, 37, 83, 20, 71, 16, 13.
Save the report and PDF in `powerbi/`. Capture each page in `docs/img/`
and record a short GIF showing navigation and a slicer selection.
