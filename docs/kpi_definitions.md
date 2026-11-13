# Reliability KPIs

The observation window includes its start and excludes its end. Replacement
counts exclude maintenance before the window and the seven rows at its endpoint.

- Window hours are the observation hours in `ref_window` multiplied by the number of machines in the group.
- Downtime hours sum the event intervals bounded by assumed repair hours, the next maintenance record, the next failure on the same machine, and the end of the window.
- Operating hours are window hours minus downtime hours.
- Failures count distinct machine, timestamp, and component keys.
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
- Site and equipment type are simulated.
