# MHE reliability leadership summary

Source dataset is synthetic. Site mapping is simulated. Costs and repair hours are assumed.

## Findings

- Model 1 and Model 2 had 1.369 and 1.143 failures per 1,000 operating hours, compared with 0.877 across the network.
- Comp2 had the most failures at 259, and 33.64% of its replacements were reactive.
- In the test window, boosting issued 116 alerts and the any-error rule issued 587, with both catching all 114 failure events.

## Recommendations

| Finding | Action | Owner type | Progress KPI |
| --- | --- | --- | --- |
| Model failure rates | Inspect recurring faults on the higher-rate models and record the cause of each failure. | Reliability engineer | Failures per 1,000 operating hours by model |
| Comp2 failures | Review the Comp2 replacement interval and record replacement reasons. | Maintenance planner | Comp2 reactive replacement share |
| Alert volume | Pilot the boosting policy on equipment data and track alerts alongside caught events. | Reliability analytics lead | Alerts per caught failure and event recall |

## Assumptions and limits

- Repair hours and costs are scenario inputs.
- The maintenance interval serves as the MTTR proxy.
- Model and alert results require validation on real equipment.
