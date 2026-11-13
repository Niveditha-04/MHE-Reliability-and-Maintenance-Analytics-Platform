import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from alert_policy import costs, hours
from load_data import DATABASE, ROOT

SEED = 42
META = ["machine_id", "datetime", "target", "split", "hour"]


def fit(frames):
    matrices = [pd.get_dummies(f.drop(columns=META), columns=["model"], dtype=float) for f in frames]
    train, validation, test = [m.reindex(columns=matrices[0].columns, fill_value=0).fillna(-1)
                               for m in matrices]
    y, vy = (f.target for f in frames[:2])
    scaler = StandardScaler().fit(train)
    logistic = LogisticRegression(class_weight="balanced", random_state=SEED, max_iter=300)
    logistic.fit(scaler.transform(train), y)
    candidates = [HistGradientBoostingClassifier(max_leaf_nodes=leaves, max_iter=70, early_stopping=False,
                                                class_weight="balanced", random_state=SEED).fit(train, y)
                  for leaves in (15, 31)]
    model = max(candidates, key=lambda m: average_precision(vy, m.predict_proba(validation)[:, 1]))
    importance = permutation_importance(model, validation, vy, scoring="average_precision",
                                        random_state=SEED, n_repeats=2, max_samples=10000)
    scores = []
    for frame, matrix in zip(frames[1:], (validation, test)):
        scores.append({"positive rate": np.zeros(len(frame)),
                       "any error": (frame.filter(regex=r"^error").sum(axis=1) > 0).to_numpy(),
                       "logistic": logistic.predict_proba(scaler.transform(matrix))[:, 1],
                       "boosting": model.predict_proba(matrix)[:, 1]})
    return scores, pd.DataFrame({"feature": train.columns, "importance": importance.importances_mean})


def average_precision(target, scores):
    return bootstrap_ap(target, scores, np.zeros(len(target), dtype=int), 0)[0]


def bootstrap_ap(target, scores, machines, repeats=1000):
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    labels = np.asarray(target)[order]
    group = np.unique(machines, return_inverse=True)[1][order]
    ends = np.r_[np.flatnonzero(scores[order][1:] != scores[order][:-1]), len(order)-1]
    starts = np.r_[0, ends[:-1]+1]
    rng = np.random.default_rng(SEED)
    n = group.max()+1

    def ap(weights):
        weight = weights[group]
        pos = np.add.reduceat(weight * labels, starts)
        count = np.add.reduceat(weight, starts).cumsum()
        precision = np.divide(pos.cumsum(), count, out=np.zeros(len(count)), where=count > 0)
        return np.dot(pos, precision) / max(pos.sum(), 1)

    estimate = ap(np.ones(n))
    draws = [ap(np.bincount(rng.integers(n, size=n), minlength=n)) for _ in range(repeats)]
    return (estimate, *np.quantile(draws, [0.025, 0.975])) if repeats else (estimate,)


def train():
    with duckdb.connect(str(DATABASE)) as db:
        db.execute((ROOT / "sql" / "05_features.sql").read_text())
        data = db.sql("FROM model_features ORDER BY datetime, machine_id").df()
        data["hour"] = hours(data.datetime)
        frames = [data[data.split == split].reset_index(drop=True) for split in ("train", "validation", "test")]
        events = db.sql("SELECT DISTINCT machine_id, datetime FROM fact_failure ORDER BY datetime").df()
        with threadpool_limits(limits=2):
            scores, importance = fit(frames)
            metrics = []
            for frame, methods in zip(frames[1:], scores):
                for method, values in methods.items():
                    ap, low, high = bootstrap_ap(frame.target, values, frame.machine_id.to_numpy())
                    metrics.append((method, frame.split.iloc[0], ap, low, high))
        results = pd.DataFrame(metrics, columns=["method", "split", "auc_pr", "range_low", "range_high"])
        policies = costs(db, *frames[1:], events, [s["boosting"] for s in scores], scores[1]["any error"])
        predictions = frames[-1][["machine_id", "datetime"]].assign(probability=scores[-1]["boosting"])
        for name, table in [("model_metrics", results), ("model_threshold_costs", policies),
                            ("model_test_predictions", predictions), ("model_importance", importance)]:
            db.register("model_output", table)
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM model_output")
            db.unregister("model_output")
        print(results.to_string(index=False))
        print(policies.to_string(index=False))


if __name__ == "__main__":
    train()
