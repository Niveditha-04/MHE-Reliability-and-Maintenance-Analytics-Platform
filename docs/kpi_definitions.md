# Reliability KPIs

The KPI window is half open and covers 8,760 hours. The start is included
and the end is excluded. The 8,761st telemetry reading per machine and
seven replacements at the endpoint fall outside it.

- Window hours are the observation hours in `ref_window` multiplied by the number of machines in the group.
- Downtime hours sum the event intervals bounded by assumed repair hours, the next maintenance record, the next failure on the same machine, and the end of the window.
- Operating hours are window hours minus downtime hours.
- Failures count distinct machine, timestamp, and component keys.
- Failures without replacement count failure keys with no exact machine, timestamp, and component match in maintenance.
- Failure rate is 1,000 times failures divided by operating hours. Component rates use fleet operating hours.
- MTBF hours based on assumed repair hours are operating hours divided by failures. Zero failures give a null MTBF.
- MTTR proxy hours average the interval from a machine-hour failure event to its next strictly later maintenance record. Events without a later record are excluded.
- Component MTTR proxy averages the intervals for events involving that component.
- A reactive replacement matches a failure on machine, component, and timestamp. Other in-window replacements are planned.
- Reactive share is reactive replacements divided by all in-window replacements. No replacements give a null share.
- Planned share is one minus reactive share.
- Availability proxy based on assumed repair hours is operating hours divided by window hours.
- Availability and MTBF sensitivity use the same event bounds with assumed repair hours of 4, 8, 12, 24, and 48.

Group rates use summed hours and counts. Group MTTR uses summed intervals
and the count of events with a later maintenance record.

## Proxies and assumptions

- MTTR is a maintenance interval proxy. The aggregate MTTR KPI does not enter the availability calculation. The next maintenance timestamp bounds each event's assumed downtime.
- Availability is a proxy based on assumed repair hours. MTBF also uses operating hours based on assumed repair hours.
- Planned replacement share is a PM compliance proxy.
- The MTTR proxy follows the maintenance schedule. Asset ranking excludes it.
- Site and equipment type are simulated groupings. Model and component are from the source.

## Dashboard measures

- Assumed replacement cost sums the part and labor costs for each in-window replacement.
- Assumed downtime cost allocates each event's downtime equally among its failed components and applies each component's assumed hourly cost. The cost falls in the month the event starts.
- Asset risk averages fleet ranks for highest failures and lowest MTBF based on assumed repair hours. Rank 1 is worst. Equal values share a rank and leave a gap. A null MTBF ranks last.
- The top 10 uses ascending risk score, descending failures, and ascending machine ID. The network top 10 stays fixed when site or model slicers change. Machines 17 and 22 both have 15 failures, 573.6 hours MTBF based on assumed repair hours, and a score of 3. Machine 17 precedes 22 by machine ID.
- The top failing component has the most failures, with component code breaking ties. Actions follow the rules below.

Failure count and MTBF are strongly related because MTBF is derived from
failures and operating hours after downtime. The risk score mostly ranks
failure count. Spearman rho is 0.997806 across 100 machines, using average
ranks for ties and placing undefined MTBF last. The score currently averages the failure rank and MTBF rank, which are
almost the same ranking (Spearman 0.998). Phase 4 replaces the MTBF rank
with the predicted-risk rank.

Action rules use the first matching condition in this order.

1. A top-10 failure-count rank, including ties, and a model failure rate above
   the network failure rate prompt
   a model fault-pattern check and a review of the top component's interval.
2. A latest replacement before window end older than the fleet median interval for
   that component prompts an inspection. The median uses intervals between
   consecutive replacements before window end, including 2014 for the same machine and component.
   Age is measured at the window end.
3. A top failing component prompts a replacement interval review.
4. A machine with no failure component stays on routine inspection.

Cost sensitivity holds replacements and hourly rates fixed and recalculates
event downtime at each assumed repair duration. The current assumed
downtime cost is 500 per hour for every component.

The reporting month starts at 06:00 on the first. Component slicers filter
only the event and cost tables. The cost view splits simultaneous
multi-component event downtime equally across the failed components.
