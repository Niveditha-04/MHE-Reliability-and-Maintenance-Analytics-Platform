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

Formulas use the CSV field names. Tableau can display them with spaces
and capital letters. In the calculation editor, field names can come
from the Data pane by dragging them into the formula. The machine-month source supplies
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
its own component filter. The standalone network top 10 is independent of
dashboard filters.

## Build steps

The local workbook is `dashboard/mhe_reliability.twbx`. Sheet 1 is
blank. Sheet 3 is a draft with equipment type and reporting year. The
guide calls for reporting month. Dashboard 2 is empty. The three tabs
are available for reuse or deletion.

### Workbook setup

1. In Tableau Public for Mac, open **File > Open** and select the local
   workbook. Use **File > Save** for local saves.
2. On the **Data Source** tab, check the sources and relationships against
   the tables above. For a missing source, select **Data > New Data
   Source > Text file** and open its CSV from `data/processed/`.
3. For each missing relationship, drag the dimension file from **Files**
   onto the logical canvas next to the fact. Click the line between the
   tables. Select the matching key on both sides. Under **Performance
   Options**, select **One** for the dimension and **Many** for the fact.
4. For filters shared across separate facts, select **Data > Edit
   Relationships** from a worksheet. Match **Site Id** and **Model** by
   field name between the machine-month source and the event and cost
   sources. Match the dimension **Component** between the event and cost
   sources. Leave the standalone leaderboard and forecast out of these
   relationships. Filter scope uses **Apply to Worksheets > Selected
   Worksheets**. [Tableau filter guide](https://help.tableau.com/current/pro/desktop/en-us/filter_across_datasources.htm)

### Page 1. Network overview

1. Open a worksheet and select the machine-month source in the Data pane.
   Control-click the raw **Failures** field and select **Rename**. Use
   **Failure Count** so the aggregate calculation can use **Failures**.
2. Select **Analysis > Create Calculated Field** for each field below.
   Enter the name and formula, then click **OK**.

   | Name | Formula using Tableau display names |
   | --- | --- |
   | Failures | `SUM([Failure Count])` |
   | MTBF | `IF SUM([Failure Count]) > 0 THEN SUM([Operating Hours]) / SUM([Failure Count]) END` |
   | Availability Proxy | `IF SUM([Window Hours]) > 0 THEN SUM([Operating Hours]) / SUM([Window Hours]) END` |
   | MTTR Proxy | `IF SUM([Mttr Events]) > 0 THEN SUM([Mttr Total]) / SUM([Mttr Events]) END` |
   | Planned Share | `IF SUM([Reactive]) + SUM([Planned]) > 0 THEN SUM([Planned]) / (SUM([Reactive]) + SUM([Planned])) END` |
   | Failure Rate per 1000h | `IF SUM([Operating Hours]) > 0 THEN 1000 * SUM([Failure Count]) / SUM([Operating Hours]) END` |

3. Control-click each KPI field in the Data pane and select **Default
   Properties > Number Format**. Set Failures to a whole number with
   separators. Set MTBF and MTTR Proxy to two decimals and label them in
   hours. Set Availability Proxy and Planned Share to percentages with two
   decimals. Set the failure rate to three decimals.
4. Click **New Worksheet** once for each of the five KPI cards. Double-click
   each tab to name it after the KPI. On **Marks**, select **Text** and
   drag only that KPI to **Text**. Leave Rows and Columns empty.
5. Open Sheet 2 or create **Failures by model**. Drag **Model** to Rows and
   **Failures** to Columns. Set **Marks** to **Bar**. Turn on **Show Mark
   Labels**. Create a second bar sheet with **Model** on Rows and
   **Failure Rate per 1000h** on Columns. Title it **Failures per 1,000
   operating hours by model**.
6. Create **Failures by site (simulated site mapping)**. Drag **Site Id**
   to Rows and **Failures** to Columns. Set **Marks** to **Bar** and show
   mark labels.
7. On **Failures by model**, drag **Site Id** and **Model** to Filters.
   Keep all values. Control-click each pill and select **Show Filter**.
   Under **Apply to Worksheets > Selected Worksheets**, select all the
   page 1 views. Extend these filters to the related fact sheets on pages
   2 and 3 as those sheets become available.
8. Open Dashboard 1. Drag the rate and count sheets, site chart, and KPI
   cards from **Sheets** onto the dashboard. Open the **Failures by model**
   tile menu and use **Filters** to show Site Id and Model if the cards
   are absent. Label Site Id **Site (simulated site mapping)**. Double-click
   the dashboard title and enter **Model 1 and model 2 fail more often than
   model 3 and model 4**. Put the rate chart below the title so the
   comparison has a visible unit.

**Check.** With filters clear, read network MTBF, DC-A failures from its
site bar, and Model 1 failures from its model bar.

### Page 2. Site and equipment drill-down

1. Click **New Worksheet**. Select the machine-month source. Drag
   **Machine Id** to Rows and **Reporting Month** to Columns. Open the
   date pill menu and select discrete **Month**. The pill should read
   **MONTH(Reporting Month)** in blue.
2. Drag **Measure Values** to **Text** and **Measure Names** to Columns
   after the month. In the Measure Values card, keep **Failures** and
   **MTBF**. Title the sheet **Monthly failures and MTBF by machine**.
3. On the page 1 filter cards, select **Apply to Worksheets > Selected
   Worksheets** and include the monthly machine sheet for Site Id and
   Model. On the monthly machine sheet, drag **Equipment Type** to
   Filters and keep all values. Control-click the Site Id and Equipment
   Type pills and select **Show Filter**. Label both cards
   **simulated site mapping**.
4. Create a worksheet from standalone `vw_top_assets.csv`. Control-click
   **Network Position** in the Data pane and select **Convert to
   Dimension** if it is a measure. Drag it to Filters and select positions
   1 through 10. Drag it to Rows first and sort ascending.
5. Drag **Machine Id**, **Recommended Action** and **Action Basis** to Rows
   in that order. Use **Analysis > Table Layout > Show Field Labels for
   Rows** if the headers are hidden. Place **Failures** on Text. Enter the
   title **Failures plus alert history, Sep to Oct, network ranking, not
   filtered by slicers**. The exported `recommended_action` field supplies
   the action.
6. Open Dashboard 2 or select **Dashboard > New Dashboard**. Name it
   **Site and equipment drill-down**. Drag in both sheets. Use the KPI
   tile menu under **Filters** to display Site Id and Equipment Type.
   Keep the network table outside the filter scope.

**Check.** Read the 10 machine IDs in position order. Change a slicer and
confirm the order stays the same.

### Page 3. Failure and cost trends

1. Create **Monthly failures by component** from the event source. Rename
   the fact's raw **Failures** to **Failure Count** and create **Failures**
   with `SUM([Failure Count])`. Drag **Reporting Month** to Columns and
   select continuous **Month** from the lower date options. Drag
   **Failures** to Rows and the dimension **Component** to Color. Select
   **Line** on Marks.
2. Drag dimension **Component** to Filters and show its filter card. To
   read a component total, create a **Component failure totals** sheet
   with **Component** on Rows and **Failures** on Text. Include the totals
   sheet in the component filter scope.
3. Create **Monthly assumed costs** from the cost source. Rename the raw
   cost fields **Replacement Cost (Source)** and **Downtime Cost (Source)**.
   Use **Analysis > Create Calculated Field** for **Assumed Replacement
   Cost** and **Assumed Downtime Cost**. Each calculation sums its
   corresponding raw field. For **Assumed Total Cost**, add the two
   aggregate calculations. Format the three calculations as whole numbers
   with separators.
4. Drag **Reporting Month** to Columns and select continuous **Month**.
   Drag **Measure Values** to Rows and **Measure Names** to Color. Keep
   only **Assumed Replacement Cost** and **Assumed Downtime Cost** in
   Measure Values. Select **Line**. Add a separate **Assumed cost totals**
   sheet with no date pill. Put Measure Names on Columns and Measure
   Values on Text. Keep all three cost measures on this totals sheet.
5. Create **Network cost sensitivity** from standalone
   `vw_cost_sensitivity.csv`. Drag **Repair Hours** to Columns. Open its
   pill menu and select **Dimension** and **Continuous**. Drag **Assumed
   Total Cost** to Rows and select **Line**.
6. Select **Dashboard > New Dashboard**. Name it **Failure and cost
   trends**. Drag in the five sheets. Add a **Text** object next to the
   cost visuals that reads **assumed repair hours and assumed downtime
   cost per hour**.
7. On the component filter card, use **Apply to Worksheets > Selected
   Worksheets** for the event and cost sheets. Include the page 4
   replacement sheet when it exists. From the page 1 filters, include the
   event and cost sheets on page 3. Keep network sensitivity outside
   these filters.

**Check.** Read comp2 failures from the component totals sheet. With
filters clear, read assumed total, replacement, and downtime cost.

### Page 4. Maintenance and spare parts

1. Create **Replacements by component** from the event source. Drag the
   dimension **Component** to Rows, **Measure Values** to Columns, and
   **Measure Names** to Color. Keep only **Planned** and **Reactive**.
   Select **Bar**. Show the shared event component filter.
2. Create **Weekly parts demand** from standalone `forecast_parts.csv`.
   In the Data pane, set **Week Start** to **Date & Time** if needed.
   Drag it to Columns and select **Exact Date**, then **Continuous**.
3. Use **Analysis > Create Calculated Field** for each of the five series
   below. The source puts observed demand and forecast demand in the same
   numeric field.

   | Series | Formula |
   | --- | --- |
   | Weekly actuals | `IF [Kind] = "actual" THEN [Forecast] END` |
   | Partial actuals | `IF [Kind] = "partial" THEN [Forecast] END` |
   | Weekly forecast | `IF [Kind] = "forecast" THEN [Forecast] END` |
   | 80% range lower | `IF [Kind] = "forecast" THEN [Low] END` |
   | 80% range upper | `IF [Kind] = "forecast" THEN [High] END` |

4. Drag **Measure Values** to Rows and **Measure Names** to Color. Keep
   only the five series. Select **Line** and enable markers under **Color**
   so isolated partial weeks are visible. The lower and upper lines show
   the 80% range. Keep missing values null.
5. Drag **Component** to Filters. Select one component and show it as a
   **Single Value (List)**. Hide **All** in the filter card menu under
   **Customize**. This keeps the interval at the component level.
6. In the Data pane menu, choose **Create Parameter**. Name it
   **Forecast method**, select **String** and **List**, and enter
   `mean 4`, `mean 8`, `smoothing`, `lag 2`, `parity mean`, and
   `calendar plus reactive`. Select **mean 8** as the starting value.
   Create **Show selected forecast** with
   `[Kind] <> "forecast" OR [Method] = [Forecast method]`. Drag it to
   Filters and keep **True**. Control-click the parameter and select
   **Show Parameter**.
7. Select **Dashboard > New Dashboard** and name it **Maintenance and
   spare parts**. Drag in both sheets. Show the event component filter
   for replacements and the standalone component filter and method
   control for weekly demand.

**Check.** The verification table has no page 4 entry. Confirm the method
selector changes the forecast and range while actuals remain visible.
Confirm both partial weeks appear as markers.

### If Tableau crashes

Save with **File > Save** after every step. After a crash, reopen
`dashboard/mhe_reliability.twbx` and continue from the last save.

### Screenshots and GIF

Save the four dashboard screenshots as `docs/img/page1.png`,
`docs/img/page2.png`, `docs/img/page3.png`, and `docs/img/page4.png`.
Save the demo GIF as `docs/img/dashboard.gif`.

## Verification

MTBF displays to two decimals. Counts and costs display as whole numbers.

| Check | SQL expected | Observed |
| --- | --- | --- |
| Network MTBF, assumed repair hours | 1,139.80 h | |
| DC-A failures | 150 | |
| Model 1 failures | 189 | 189 (match) |
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
