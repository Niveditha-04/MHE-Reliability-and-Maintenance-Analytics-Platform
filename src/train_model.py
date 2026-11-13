import duckdb
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from alert_policy import costs, hours
from load_data import DATABASE, ROOT
from model_audit import ablations, booster

SEED = 42
META = ["machine_id", "datetime", "target", "split", "hour"]


def fit(frames, policy_frames, later):
    matrices = [pd.get_dummies(f.drop(columns=META), columns=["model"], dtype=float) for f in frames]
    train, validation, test = [m.reindex(columns=matrices[0].columns, fill_value=0).fillna(-1)
                               for m in matrices]
    y, vy = (f.target for f in frames[:2])
    scaler = StandardScaler().fit(train)
    logistic = LogisticRegression(class_weight="balanced", random_state=SEED, max_iter=300)
    logistic.fit(scaler.transform(train), y)
    np.testing.assert_allclose(scaler.mean_, train.mean().to_numpy())
    candidates = [booster(leaves).fit(train, y) for leaves in (15, 31)]
    tuning = pd.DataFrame([(m.max_leaf_nodes, average_precision(vy, m.predict_proba(validation)[:, 1]))
                           for m in candidates], columns=["leaves", "auc_pr"])
    model = candidates[tuning.auc_pr.idxmax()]
    audit = ablations(train, validation, y, vy, later, model.max_leaf_nodes)
    importance = permutation_importance(model, validation, vy, scoring="average_precision",
                                        random_state=SEED, n_repeats=2, max_samples=10000)
    scores = []
    for frame, matrix in zip(frames[1:], (validation, test)):
        scores.append({"positive rate": np.zeros(len(frame)),
                       "any error": (frame.filter(regex=r"^error").sum(axis=1) > 0).to_numpy(),
                       "logistic": logistic.predict_proba(scaler.transform(matrix))[:, 1],
                       "boosting": model.predict_proba(matrix)[:, 1]})
    policy_scores = []
    for frame in policy_frames:
        matrix = pd.get_dummies(frame.drop(columns=META), columns=["model"], dtype=float)
        matrix = matrix.reindex(columns=train.columns, fill_value=0).fillna(-1)
        policy_scores.append(model.predict_proba(matrix)[:, 1])
    return scores, policy_scores, tuning, audit, pd.DataFrame({"feature": train.columns, "importance": importance.importances_mean})


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
        policy_frames = []
        later_targets, later_masks = [], []
        for frame in frames[:2]:
            grid = db.sql("SELECT datetime, machine_id, target_later FROM model_feature_grid").df()
            keys = frame[["datetime", "machine_id"]]
            later_targets.append(keys.merge(grid, on=["datetime", "machine_id"], how="left").target_later.fillna(False))
            later_masks.append(frame.datetime <= frame.datetime.max() - pd.Timedelta(hours=24))
        for frame in frames[1:]:
            start = frame.datetime.min() - pd.Timedelta(hours=24)
            end = frame.datetime.max()
            policy = db.execute("""
                SELECT * EXCLUDE (hour_number, last_hour, target_later)
                FROM model_feature_grid WHERE datetime BETWEEN ? AND ? ORDER BY datetime, machine_id
            """, [start, end]).df()
            policy["hour"] = hours(policy.datetime)
            policy_frames.append(policy)
        with threadpool_limits(limits=2):
            scores, policy_scores, tuning, audit, importance = fit(
                frames, policy_frames, (*later_targets, later_masks))

            metrics = []
            for frame, methods in zip(frames[1:], scores):
                for method, values in methods.items():
                    ap, low, high = bootstrap_ap(frame.target, values, frame.machine_id.to_numpy())
                    metrics.append((method, frame.split.iloc[0], ap, low, high))
        results = pd.DataFrame(metrics, columns=["method", "split", "auc_pr", "range_low", "range_high"])
        errors = (policy_frames[1].filter(regex=r"^error").sum(axis=1) > 0).to_numpy()
        policies, curve = costs(db, *policy_frames, events, policy_scores, errors)

        predictions = frames[-1][["machine_id", "datetime"]].assign(probability=scores[-1]["boosting"])
        for name, table in [("model_metrics", results), ("model_threshold_costs", policies),
                            ("model_test_predictions", predictions), ("model_importance", importance),
                            ("model_tuning", tuning), ("model_ablation", audit), ("model_cost_curve", curve)]:
            db.register("model_output", table)
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM model_output")
            db.unregister("model_output")
        print(results.to_string(index=False))
        print(policies.to_string(index=False))


if __name__ == "__main__":
    train()
