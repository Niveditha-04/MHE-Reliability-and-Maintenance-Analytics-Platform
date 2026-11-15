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

The threshold minimizes assumed validation cost across 501 logit-spaced
thresholds and a no-alert threshold. An alert suppresses further alerts
for 24 hours. Validation and test policy scoring include 24 unlabeled
hours before each split.
A failure is caught when an alert fired in the preceding 24 hours, excluding
the event hour. Inspection costs 100 per alert. Missed-event cost uses the
assumed repair duration times the assumed hourly downtime rate, which is
500 for every component. The cost model assumes an alert leads to an action
that avoids the event's downtime. Cost ratios of 10, 30, and 60 test the
effect of changing the missed-event cost. Model scores use class weights
and are not calibrated probabilities.

Parts demand counts Monday 06:00 to Monday 06:00 replacements, with partial
weeks excluded. Four- and eight-week means and simple exponential smoothing
are compared with lag-2, parity mean, and a calendar proxy on rolling
origins over the final 12 weeks. Smoothing uses earlier 2015 weeks,
starting January 5 at 06:00. MAE uses horizons with known actuals. The
four forecast weeks use 80% Poisson ranges conditional on each point
forecast. Empirical residual
quantiles provide a fallback when coverage for the selected method and component is below
70%. All four components meet the coverage cutoff. Planned replacements
occur at regular intervals. Reactive replacements are less predictable.

The source is synthetic. The model score makes no claim about real equipment.
The source has one year of telemetry and few test failure events. Site and
equipment groupings are simulated. Repair hours and costs are assumed.

The partial week starting 2015-12-28 at 06:00 is shown separately and
excluded from fitting. Forecasts start on 2016-01-04 at 06:00. Planned
and reactive shares use the 2015 reporting window and exact failure matches.

The any-error rule also catches all 114 test events. Boosting fires fewer
alerts at the same recall. Average precision for failures 24 to 48 hours
ahead is 0.83. The signal extends beyond the next 24 hours. The validation
comparison covers two boosting settings.

A score and a failure count taken over the same period describe that period.
Predictive agreement uses scores from September and October and counts from
November and December. Their Spearman correlation is 0.191. Overall
half-year failure count persistence is 0.465, so the network ranking retains
the blend with the earlier score period.

Forecast fitting and testing use the 51 full weeks starting January 5,
2015. The 2014 weekly totals average about 12 against 55 in 2015 and
alternate with zero weeks. The replacement history includes 2014 for age
features and maintenance actions. The half-open KPI window contains 25
start-partial replacements, 2,807 full-week replacements and 47 end-partial
replacements.

Alerts cost 100 and a missed event costs at least 1,000. Event scores are
well separated from other hours. One threshold wins at every tested cost
ratio. The search found no cost trade-off.

The 24-hour label concentrates lead times near 24 hours. The median is
24 hours, the range is 8 to 26 hours, and no event had 48 hours of lead.

Within models 1 to 3, half-year machine failure ranks have Spearman
correlations of 0.03 to 0.10. Model differences account for much of the
pooled 0.46. The ranking is labeled “failures plus alert history, Sep to Oct”.

The 80% forecast intervals cover 83.3% of comp2 and 78.6% of comp3
backtest observations for the selected methods.
