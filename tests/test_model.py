import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from alert_policy import evaluate, hours
from load_data import DATABASE
from train_model import bootstrap_ap


def check_features(db):
    for machine, offset in [(1, 24), (73, 2000), (99, 8000)]:
        row = db.execute("""
            SELECT * FROM model_features WHERE machine_id = ?
            ORDER BY datetime LIMIT 1 OFFSET ?
        """, [machine, offset]).df().iloc[0]
        t = row.datetime.to_pydatetime()
        expected = {}
        for size in (3, 24):
            readings = db.execute("""
                SELECT volt, rotate, pressure, vibration FROM fact_telemetry
                WHERE machine_id = ? AND datetime > ? - ? * INTERVAL 1 HOUR AND datetime <= ?
            """, [machine, t, size, t]).df()
            for col in readings:
                expected[f"{col}_mean_{size}h"] = readings[col].mean()
                expected[f"{col}_sd_{size}h"] = readings[col].std(ddof=0)
        errors = db.execute("""
            SELECT error_id FROM fact_error WHERE machine_id = ?
              AND datetime > ? - INTERVAL 24 HOUR AND datetime <= ?
        """, [machine, t, t]).fetchall()
        for i in range(1, 6):
            expected[f"error{i}_24h"] = errors.count((f"error{i}",))
        maintenance = db.execute("""
            SELECT component, datetime FROM fact_maintenance WHERE machine_id = ?
              AND datetime <= ? ORDER BY datetime
        """, [machine, t]).fetchall()
        latest = dict(maintenance)
        for i in range(1, 5):
            part = f"comp{i}"
            expected[f"hours_since_{part}"] = (t-latest[part]).total_seconds()/3600 if part in latest else np.nan
        np.testing.assert_allclose([row[key] for key in expected], list(expected.values()), atol=1e-8)
        assert tuple(row[["age", "model"]]) == db.execute(
            "SELECT age, model FROM dim_machine WHERE machine_id = ?", [machine]).fetchone()
        target = db.execute("""
            SELECT count(*) > 0 FROM fact_failure WHERE machine_id = ?
              AND datetime > ? AND datetime <= ? + INTERVAL 24 HOUR
        """, [machine, t, t]).fetchone()[0]
        assert row.target == target
        print(machine, t, len(expected)+2, "features matched", "target", target)


def check_alerts():
    rows = pd.DataFrame({"machine_id": [1]*5, "hour": [0, 10, 23, 24, 48]})
    result = evaluate(rows, {1: np.array([12, 24, 25, 80])},
                      np.ones(5), 0.5, 100, 6000)
    assert (result["alerts"], result["caught"], result["missed"], result["false_alerts"],
            result["cost"]) == (3, 3, 1, 1, 6300)


if __name__ == "__main__":
    check_alerts()
    labels, scores, machines = np.array([1, 0, 1, 0]), np.array([.1, .4, .4, .3]), [1, 1, 2, 2]
    result = bootstrap_ap(labels, scores, machines, 1000)
    assert result == bootstrap_ap(labels, scores, machines, 1000)
    assert np.isclose(result[0], average_precision_score(labels, scores))
    with duckdb.connect(str(DATABASE), read_only=True) as db:
        check_features(db)
        bounds = dict((s, (lo, hi)) for s, lo, hi in db.sql(
            "SELECT split, min(datetime), max(datetime) FROM model_features GROUP BY split").fetchall())
        for before, after in [("train", "validation"), ("validation", "test")]:
            assert hours([bounds[before][1]])[0] + 24 < hours([bounds[after][0]])[0]
        assert db.sql("""
            SELECT count(*), count(DISTINCT machine_id),
                   count(*) FILTER (WHERE mean_risk BETWEEN 0 AND 1)
            FROM model_machine_risk
        """).fetchone() == (100, 100, 100)
    print("Leakage, split, alert, bootstrap and risk checks passed")
