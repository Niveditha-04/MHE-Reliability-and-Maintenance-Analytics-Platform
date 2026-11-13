import numpy as np
import pandas as pd


def evaluate(rows, events, scores, threshold, inspection, missed_cost):
    alerts = caught = useful = 0
    for machine, positions in rows.groupby("machine_id", sort=False).indices.items():
        hours = rows["hour"].to_numpy()[positions]
        candidates = hours[scores[positions] >= threshold]
        fired = []
        for hour in candidates:
            if not fired or hour >= fired[-1] + 24:
                fired.append(hour)
        failures = events.get(machine, np.array([], dtype=int))
        fired = np.asarray(fired, dtype=int)
        prior = np.searchsorted(fired, failures, side="left") - 1
        eligible = prior >= 0
        caught += np.sum(failures[eligible] - fired[prior[eligible]] <= 24)
        following = np.searchsorted(failures, fired, side="right")
        eligible = following < len(failures)
        useful += np.sum(failures[following[eligible]] - fired[eligible] <= 24)
        alerts += len(fired)
    missed = sum(map(len, events.values())) - caught
    return dict(alerts=alerts, caught=caught, missed=missed, false_alerts=alerts-useful,
                recall=caught / max(caught+missed, 1), precision=useful / max(alerts, 1),
                cost=alerts*inspection + missed*missed_cost)


def hours(values):
    return np.asarray(values, dtype="datetime64[h]").astype("int64")


def costs(db, validation, test, failure_events, scores, error_scores):
    inspection, repair, hourly = db.sql("""
        SELECT (SELECT value FROM assumptions_model WHERE parameter = 'inspection_cost_per_alert'),
               (SELECT value FROM assumptions_repair WHERE parameter = 'assumed_repair_hours'),
               (SELECT max(downtime_cost_per_hour) FROM assumptions_cost)
    """).fetchone()
    base_ratio = repair * hourly / inspection
    frames = [validation, test]
    grouped = []
    for frame in frames:
        start, end = frame["datetime"].min(), frame["datetime"].max() + pd.Timedelta(hours=24)
        subset = failure_events[(failure_events.datetime >= start) & (failure_events.datetime <= end)]
        grouped.append({key: hours(group.datetime) for key, group in subset.groupby("machine_id")})
    candidates = np.unique(np.r_[np.quantile(scores[0], np.linspace(0, 1, 41)), 1.01])
    trial = [evaluate(validation, grouped[0], scores[0], t, inspection, 0) for t in candidates]
    results = []
    for ratio in sorted({10, 30, base_ratio}):
        price = ratio * inspection
        index = min(range(len(trial)), key=lambda i: (trial[i]["cost"] + trial[i]["missed"] * price,
                                                      trial[i]["alerts"], -candidates[i]))
        threshold = candidates[index]
        results.append(dict(policy="boosting", ratio=ratio, threshold=threshold,
                            **evaluate(test, grouped[1], scores[1], threshold, inspection, price)))
    for name, values, threshold in [("no alerts", np.zeros(len(test)), 1.01),
                                    ("any error", error_scores, 1.0)]:
        results.append(dict(policy=name, ratio=base_ratio, threshold=threshold,
                            **evaluate(test, grouped[1], values, threshold, inspection, repair*hourly)))
    for result in results:
        result["alerts_per_machine_month"] = result["alerts"] / (2 * test.machine_id.nunique())
    return pd.DataFrame(results)
