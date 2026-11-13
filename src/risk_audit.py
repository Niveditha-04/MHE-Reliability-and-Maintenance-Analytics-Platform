import pandas as pd

from alert_policy import fire, hours


def machine_period(db, start, end, threshold):
    frames = db.execute("""
        SELECT machine_id, datetime, probability FROM model_hourly_scores
        WHERE datetime >= ? AND datetime < ? ORDER BY datetime
    """, [start, end]).df()
    counts = db.execute("""
        SELECT machine_id, count(*) AS failures FROM fact_failure
        WHERE datetime >= ? AND datetime < ? GROUP BY machine_id
    """, [start, end]).df()
    rows = []
    for machine, group in frames.groupby("machine_id"):
        above = group.probability.ge(threshold)
        rows.append((machine, above.mean(), len(fire(hours(group.datetime[above])))))
    return pd.DataFrame(rows, columns=["machine_id", "share", "alerts"]).merge(
        counts, how="left", on="machine_id").fillna({"failures": 0})


def correlations(db, threshold):
    start, july, sep, nov, end = db.sql("""
        SELECT window_start, window_start + INTERVAL 6 MONTH, window_start + INTERVAL 8 MONTH,
               window_start + INTERVAL 10 MONTH, window_end FROM ref_window
    """).fetchone()
    first = machine_period(db, start, july, threshold)
    second = machine_period(db, july, end, threshold)
    paired = first.merge(second, on="machine_id", suffixes=("_first", "_second"))
    paired = paired.merge(db.sql("SELECT machine_id, model FROM dim_machine").df())
    results = []
    for name, group in [("overall", paired), *paired.groupby("model")]:
        results.append((name, *(group[f"{m}_first"].corr(group[f"{m}_second"], method="spearman")
                               for m in ("failures", "alerts"))))
    print(pd.DataFrame(results, columns=["group", "failure_rho", "alert_rho"]).to_string(index=False))
    prior = machine_period(db, sep, nov, threshold)
    future = machine_period(db, nov, end, threshold)
    paired = prior.merge(future, on="machine_id", suffixes=("_prior", "_future"))
    out = paired.share_prior.corr(paired.failures_future, method="spearman")
    print("Out of time:", out)
    print("Same period:", paired.share_future.corr(paired.failures_future, method="spearman"))
    use_model = max(*results[0][1:], out) >= .3
    prior["use_model"] = use_model
    return prior[["machine_id", "share", "use_model"]]


def current(db, threshold):
    frame = db.sql("""
        SELECT machine_id, datetime, probability FROM model_hourly_scores ORDER BY datetime
    """).df()
    rows = []
    for machine, group in frame.groupby("machine_id"):
        end = hours(group.datetime)[-1]
        alerts = fire(hours(group.datetime[group.probability.ge(threshold)]))
        rows.append((machine, group.probability.iloc[-1],
                     any(hour > end-24 for hour in alerts),
                     sum(hour > end-720 for hour in alerts)))
    return pd.DataFrame(rows, columns=["machine_id", "score_at_end", "alert_active_end",
                                      "alerts_last_30_days"])
