import duckdb
import pandas as pd

from alert_policy import fire, hours
from load_data import DATABASE


def candidates(frame, threshold):
    rows = []
    for machine, group in frame.groupby("machine_id"):
        above = group.probability >= threshold
        rows.append((machine, group.probability.mean(), above.mean(),
                     len(fire(hours(group.datetime[above])))))
    return pd.DataFrame(rows, columns=["machine_id", "mean_risk", "threshold_share", "alerts"])


def score():
    with duckdb.connect(str(DATABASE)) as db:
        frame = db.sql("FROM model_test_predictions ORDER BY datetime").df()
        threshold, = db.sql("""
            SELECT threshold FROM model_threshold_costs WHERE policy = 'boosting'
            ORDER BY ratio DESC LIMIT 1
        """).fetchone()
        measures = candidates(frame, threshold)
        failures = db.sql("""
            SELECT machine_id, count(DISTINCT datetime) AS failures
            FROM fact_failure CROSS JOIN ref_window
            WHERE datetime >= window_start + INTERVAL 10 MONTH AND datetime < window_end
            GROUP BY machine_id
        """).df()
        comparison = measures.merge(failures, on="machine_id", how="left").fillna({"failures": 0})
        correlations = comparison.drop(columns="machine_id").corr(method="spearman").failures
        selected = correlations[["threshold_share", "alerts"]].idxmax()
        halves = [candidates(frame[frame.datetime.dt.month == month], threshold).set_index("machine_id")
                  for month in (11, 12)]
        print(correlations.to_string())
        print("November to December:", halves[0][selected].corr(halves[1][selected], method="spearman"))
        print("Mean risk distribution:", measures.mean_risk.quantile([0, .25, .5, .75, 1]).to_dict())
        ordered = sorted(measures.mean_risk)
        print("Machines within 0.001 of another:", sum(
            (i > 0 and value - ordered[i-1] <= .001) or
            (i+1 < len(ordered) and ordered[i+1] - value <= .001)
            for i, value in enumerate(ordered)))
        measures["predicted_risk"] = measures[selected]
        measures["risk_measure"] = selected
        db.register("scores", measures)
        db.execute("""
            CREATE OR REPLACE TABLE model_machine_risk AS
            SELECT *, rank() OVER (ORDER BY predicted_risk DESC) AS predicted_risk_rank
            FROM scores
        """)


if __name__ == "__main__":
    score()
