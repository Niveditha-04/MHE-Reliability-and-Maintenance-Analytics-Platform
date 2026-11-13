import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score


def booster(leaves):
    return HistGradientBoostingClassifier(max_leaf_nodes=leaves, max_iter=70,
                                          early_stopping=False, class_weight="balanced",
                                          random_state=42)


def ablations(train, validation, y, vy, later, leaves):
    telemetry = [c for c in train if "_mean_" in c or "_sd_" in c]
    errors = [c for c in train if c.startswith("error")]
    ages = [c for c in train if c.startswith("hours_since")]
    rows = []
    for name, columns, labels, check, masks in [
        ("telemetry", telemetry, y, vy, None),
        ("errors", errors, y, vy, None),
        ("replacement age", ages, y, vy, None),
        ("errors and age", errors + ages, y, vy, None),
        ("all", list(train), y, vy, None),
        ("shuffled labels", list(train), np.random.default_rng(42).permutation(y), vy, None),
        ("24 to 48 hours", list(train), later[0], later[1], later[2]),
        ("missing age flags", list(train), y, vy, None),
    ]:
        x, v = train[columns], validation[columns]
        if name == "missing age flags":
            x, v = [frame.assign(**{c + "_missing": frame[c].eq(-1) for c in ages})
                    .replace({c: {-1: 0} for c in ages}) for frame in (x, v)]
        if masks is not None:
            x, v, labels, check = x[masks[0]], v[masks[1]], labels[masks[0]], check[masks[1]]
        model = booster(leaves).fit(x, labels)
        rows.append((name, average_precision_score(check, model.predict_proba(v)[:, 1])))
    return pd.DataFrame(rows, columns=["method", "auc_pr"])
