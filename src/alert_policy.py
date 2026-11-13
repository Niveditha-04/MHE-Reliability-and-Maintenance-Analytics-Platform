import numpy as np
import pandas as pd
from scipy.special import expit, logit


def fire(candidates):
    fired = []
    for hour in candidates:
        if not fired or hour >= fired[-1] + 24:
            fired.append(hour)
    return fired


def evaluate(rows, events, scores, threshold, inspection, missed_cost):
    alerts = caught = useful = 0
    leads = []
    all_hours = rows.hour.to_numpy()
    for machine, positions in rows.groupby("machine_id", sort=False).indices.items():
        hours = all_hours[positions]
        candidates = hours[scores[positions] >= threshold]
        fired = fire(candidates)
        failures = events.get(machine, np.array([], dtype=int))
        fired = np.asarray(fired, dtype=int)
        first = np.searchsorted(fired, failures - 24)
        eligible = first < np.searchsorted(fired, failures, side="left")
        leads.extend(failures[eligible] - fired[first[eligible]])
        caught += eligible.sum()
        following = np.searchsorted(failures, fired, side="right")
        eligible = following < len(failures)
        useful += np.sum(failures[following[eligible]] - fired[eligible] <= 24)
        alerts += len(fired)
    missed = sum(map(len, events.values())) - caught
    return dict(alerts=alerts, caught=caught, missed=missed, false_alerts=alerts-useful,
                recall=caught / max(caught+missed, 1), precision=useful / alerts if alerts else None,
                lead_min=min(leads, default=None), lead_median=np.median(leads) if leads else None,
                lead_max=max(leads, default=None),
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
        start, end = frame["datetime"].min() + pd.Timedelta(hours=24), frame["datetime"].max() + pd.Timedelta(hours=24)
        subset = failure_events[(failure_events.datetime >= start) & (failure_events.datetime <= end)]
        grouped.append({key: hours(group.datetime) for key, group in subset.groupby("machine_id")})
    candidates = np.r_[expit(np.linspace(logit(.0005), logit(.9995), 501)), 1.01]
    trial = [evaluate(validation, grouped[0], scores[0], t, inspection, 0) for t in candidates]
    results, curve = [], []

    def record(split, threshold, outcome):
        return dict(split=split, threshold=threshold,
                    **{k: outcome[k] for k in ("alerts", "caught", "missed", "false_alerts")},
                    **{f"cost_ratio_{r}": inspection * (outcome["alerts"] + r*outcome["missed"])
                       for r in (10, 30, 60)})

    curve.extend(record("validation", t, row) for t, row in zip(candidates, trial))
    test_results = {}
    for ratio in sorted({10, 30, base_ratio}):
        price = ratio * inspection
        index = min(range(len(trial)), key=lambda i: (trial[i]["cost"] + trial[i]["missed"] * price,
                                                      -candidates[i]))
        threshold = candidates[index]
        if threshold not in test_results:
            outcome = evaluate(test, grouped[1], scores[1], threshold, inspection, 0)
            test_results[threshold] = outcome
            curve.append(record("test", threshold, outcome))
        outcome = test_results[threshold]
        results.append(dict(policy="boosting", ratio=ratio, threshold=threshold,
                            **(outcome | {"cost": inspection*outcome["alerts"] + price*outcome["missed"]})))
    for name, values, threshold in [("no alerts", np.zeros(len(test)), 1.01),
                                    ("any error", error_scores, 1.0)]:
        results.append(dict(policy=name, ratio=base_ratio, threshold=threshold,
                            **evaluate(test, grouped[1], values, threshold, inspection, repair*hourly)))
    for result in results:
        result["alerts_per_machine_month"] = result["alerts"] / (2 * test.machine_id.nunique())
    return pd.DataFrame(results), pd.DataFrame(curve)
