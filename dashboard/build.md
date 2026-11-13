# Tableau Public build guide

The workbook uses the full-data exports from `python src/export_bi.py`.
Each CSV is in `data/processed/`. The `reporting_month` field is a date.
The `week_start` field is a date and time.

## Data sources

| CSV | Page and use |
| --- | --- |
| dim_machine.csv | 1–3, model, site and equipment labels |
| dim_component.csv | 3–4, component labels and filters |
| vw_machine_monthly.csv | 1–2, KPI totals and trends |
| vw_events_monthly.csv | 3–4, component failures and replacements |
| vw_cost_detail.csv | 3, assumed replacement and downtime costs |
| vw_top_assets.csv | 2, network top 10 and action evidence |
| vw_cost_sensitivity.csv | 3, network cost by assumed repair hours |
| threshold_curve.csv | 2, validation cost by threshold |
| model_machine_current.csv | 2, end-of-source model view |
| model_machine_risk.csv | 2, September and October alert history |
| model_metrics.csv | 2, validation and test average precision |
| model_threshold_costs.csv | 2, assumed policy costs |
| forecast_parts.csv | 4, actual and forecast weekly demand |

## Relationships

Each fact has its own logical data source. Shared dimensions link to each
applicable fact with one-to-many relationships. Fact tables remain separate.

| One side | Many side | Key |
| --- | --- | --- |
| dim_machine | vw_machine_monthly | machine_id |
| dim_machine | vw_events_monthly | machine_id |
| dim_machine | vw_cost_detail | machine_id |
| dim_component | vw_events_monthly | component |
| dim_component | vw_cost_detail | component |

The leaderboard, sensitivity, threshold curve, model files, and forecast
are standalone sources with no relationships. Monthly charts use the
`reporting_month` field from their fact source. [Tableau cardinality guide](https://help.tableau.com/current/pro/desktop/en-us/cardinality_and_ri.htm)

## Calculated fields

Formulas use the CSV field names. The machine-month source supplies
reliability metrics. The component failure chart uses the Failures formula
on the event source. Replacement shares work with either source. Cost
calculations use the cost source. A zero denominator returns null.

| Field | Tableau formula | Meaning |
| --- | --- | --- |
| Failures | `SUM([failures])` | Component failure count. |
| Operating Hours | `SUM([operating_hours])` | Window hours less assumed downtime. |
| Downtime Hours | `SUM([downtime_hours])` | Downtime based on assumed repair hours. |
| Failure Rate per 1000h | `IF SUM([operating_hours]) > 0 THEN 1000 * SUM([failures]) / SUM([operating_hours]) END` | Failures per 1,000 operating hours. |
| MTBF | `IF SUM([failures]) > 0 THEN SUM([operating_hours]) / SUM([failures]) END` | Operating hours per failure, based on assumed repair hours. |
| Availability Proxy | `IF SUM([window_hours]) > 0 THEN SUM([operating_hours]) / SUM([window_hours]) END` | Operating share of window hours, based on assumed repair hours. |
| MTTR Proxy | `IF SUM([mttr_events]) > 0 THEN SUM([mttr_total]) / SUM([mttr_events]) END` | Average interval to the next maintenance record. |
| Reactive Share | `IF SUM([reactive]) + SUM([planned]) > 0 THEN SUM([reactive]) / (SUM([reactive]) + SUM([planned])) END` | Reactive share of replacements. |
| Planned Share | `IF SUM([reactive]) + SUM([planned]) > 0 THEN SUM([planned]) / (SUM([reactive]) + SUM([planned])) END` | Planned share of replacements, a PM compliance proxy. |
| Assumed Replacement Cost | `SUM([assumed_replacement_cost])` | Assumed parts and labor costs. |
| Assumed Downtime Cost | `SUM([assumed_downtime_cost])` | Assumed cost of event downtime. |
| Assumed Total Cost | `SUM([assumed_replacement_cost]) + SUM([assumed_downtime_cost])` | Combined assumed cost. |

## Pages and filters

1. **Network overview.** Lead with failures by model. Include failures,
   availability proxy, MTBF, MTTR proxy, and planned share.
2. **Site and equipment drill-down.** Show monthly KPIs by machine. Sort
   the network top 10 by `network_position` and keep positions 1 to 10.
   Show the action and its basis. Label the table “failures plus alert
   history, Sep to Oct, network ranking, not filtered by slicers”.
3. **Failure and cost trends.** Lead with monthly failures by component.
   Plot assumed replacement cost and assumed downtime cost as separate
   series. Show network sensitivity by repair duration. Label cost visuals
   “assumed repair hours and assumed downtime cost per hour”.
4. **Maintenance and spare parts.** Show planned and reactive replacements
   by component. Plot weekly actuals, partial actuals, and forecasts with
   80% intervals and a forecast method selector.

Site and equipment type carry the label “simulated site mapping”. Site
and model filters apply to related fact sheets on pages 1 to 3. The
component filter appears on pages 3 and 4. The standalone forecast uses
its own component filter. The standalone network top 10 stays fixed.

## Verification

MTBF displays to two decimals. Counts and costs display as whole numbers.

| Check | SQL expected | Observed |
| --- | --- | --- |
| Network MTBF, assumed repair hours | 1,139.80 h | |
| DC-A failures | 150 | |
| Model 1 failures | 189 | |
| comp2 failures | 259 | |
| Assumed total cost | 5,490,630 | |
| Assumed replacement cost | 1,185,630 | |
| Assumed downtime cost | 4,305,000 | |
| Network top 10 | 99, 37, 83, 13, 20, 71, 23, 21, 49, 90 | |

## Publishing

Tableau Public publishes data extracts with the workbook. Publishing
depends on the dataset license. If redistribution is restricted, only
permitted summary extracts by model, component, and month are eligible
for publication. Those extracts exclude machine-level rows. The workbook
stays local if the license also restricts those summaries.
[Tableau Public FAQ](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm)
