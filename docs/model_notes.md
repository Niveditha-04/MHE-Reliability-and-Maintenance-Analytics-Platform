# Prediction and parts demand

The target is a machine failure in (t, t + 24 hours]. Simultaneous
component failures form one machine-hour event. The first 24 hours and
hours without complete forward coverage are excluded. Training covers
January through August, validation September through October, and test
November through December. Reporting months begin at 06:00. The last
24 training and validation hours are excluded at each split boundary.

Telemetry features use means and population standard deviations over
[t − 2 h, t] and [t − 23 h, t]. Error counts use [t − 23 h, t].
Replacement age uses the latest record at or before t, including 2014
history. Missing ages are encoded as −1. Machine age and one-hot model
are features. Machine ID identifies rows and is excluded from the model.
Scaling parameters are fitted on training rows.

The baselines are positive rate, any error in 24 hours, and class-weighted
logistic regression. Class-weighted histogram gradient boosting is selected
by validation average precision. The metric is average precision, with
95% percentile intervals from 1,000 machine bootstrap samples. Validation
permutation importance measures the drop in average precision.

The threshold minimizes assumed validation cost over score quantiles and
a no-alert threshold. An alert suppresses further alerts for 24 hours. Validation and test policy
scoring include the 24 hours before the split. Those scores carry no
training or evaluation labels.
A failure is caught when an alert fired in the preceding 24 hours, excluding
the event hour. Inspection costs 100 per alert. Missed-event cost uses the
assumed repair duration times the assumed hourly downtime rate, which is
500 for every component. The cost model assumes an alert leads to an action
that avoids the event's downtime. Cost ratios of 10, 30, and 60 test the
effect of changing the missed-event cost. Model scores use class weights
and are not calibrated probabilities.

Parts demand counts Monday 06:00 to Monday 06:00 replacements, with partial
weeks excluded. Four- and eight-week means and simple exponential smoothing
are compared on rolling origins over the final 12 weeks. The smoothing
parameter is selected on earlier 2015 weeks, beginning January 5 at 06:00. MAE uses only horizons with known
actuals. The four weeks after the last full source week use 80% Poisson ranges conditional on each point forecast. Empirical residual
quantiles provide a fallback when pooled coverage for a component is below
70%. All four components meet the coverage cutoff. Planned replacements follow
a fixed cycle, so the reactive part is the less predictable part.

The source is synthetic. The model score makes no claim about real equipment.
The source has one year of telemetry and few test failure events. Site and
equipment groupings are simulated. Repair hours and costs are assumed.

The partial week starting 2015-12-28 at 06:00 is shown separately and
excluded from fitting. Forecasts start on 2016-01-04 at 06:00. Planned
and reactive shares use the 2015 reporting window and exact failure matches.

The asset risk field uses the share of November and December test hours at
or above the validation threshold. The measure is selected descriptively
using test-period event counts. November and December ranks have Spearman
correlation 0.020, so the ranking has low month-to-month stability.
