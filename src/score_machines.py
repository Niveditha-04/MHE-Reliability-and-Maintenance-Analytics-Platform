import duckdb
import pandas as pd

from alert_policy import fire, hours
from load_data import DATABASE
from risk_audit import correlations, current


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
        prior = correlations(db, threshold)
        measures = candidates(frame, threshold).merge(prior, on="machine_id")
        measures["predicted_risk"] = measures.share
        measures["risk_measure"] = "Sep to Oct threshold share"
        db.register("scores", measures)
        db.execute("""
            CREATE OR REPLACE TABLE model_machine_risk AS
            SELECT *, rank() OVER (ORDER BY predicted_risk DESC) AS predicted_risk_rank
            FROM scores
        """)
        db.register("current_scores", current(db, threshold))
        db.execute("CREATE OR REPLACE TABLE model_machine_current AS FROM current_scores")


if __name__ == "__main__":
    score()
