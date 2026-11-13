import duckdb
import numpy as np
import pandas as pd
from scipy.stats import poisson

from load_data import DATABASE

METHODS = ("mean 4", "mean 8", "smoothing")
ALPHAS = (0.1, 0.2, 0.4, 0.6, 0.8)


def smooth(series, alpha):
    level = series[0]
    for value in series[1:]:
        level += alpha * (value - level)
    return level


def predict(series, alpha):
    return (np.mean(series[-4:]), np.mean(series[-8:]), smooth(series, alpha))


def choose_alpha(series):
    return min(ALPHAS, key=lambda a: sum(abs(series[i] - smooth(series[:i], a))
                                         for i in range(8, len(series))))


def interval(estimate, residuals, empirical):
    if empirical:
        low, high = estimate + np.quantile(residuals, [0.1, 0.9])
        return max(0, np.floor(low)), np.ceil(high)
    return poisson.ppf([0.1, 0.9], estimate)


def weekly(db):
    return db.sql("""
        WITH bounds AS (
            SELECT min(datetime) AS start_at, max(datetime) AS end_at FROM fact_maintenance
        ), weeks AS (
            SELECT week_start FROM bounds
            CROSS JOIN generate_series(
                date_trunc('week', start_at - INTERVAL 6 HOUR) + INTERVAL 6 HOUR,
                date_trunc('week', end_at - INTERVAL 6 HOUR) + INTERVAL 6 HOUR,
                INTERVAL 1 WEEK
            ) AS w(week_start)
            WHERE week_start >= start_at AND week_start + INTERVAL 1 WEEK <= end_at
        ), demand AS (
            SELECT date_trunc('week', m.datetime - INTERVAL 6 HOUR) + INTERVAL 6 HOUR AS week_start,
                   m.component, count(*) AS actual, count(f.failure_id) AS reactive
            FROM fact_maintenance m LEFT JOIN fact_failure f USING (machine_id, datetime, component)
            GROUP BY 1, 2
        )
        SELECT w.week_start, c.component, coalesce(d.actual, 0) AS actual,
               coalesce(d.reactive, 0) AS reactive
        FROM weeks w CROSS JOIN dim_component c
        LEFT JOIN demand d USING (week_start, component)
        ORDER BY component, week_start
    """).df()


def forecast():
    with duckdb.connect(str(DATABASE)) as db:
        rows, errors, shares = [], [], []
        for component, group in weekly(db).groupby("component"):
            y = group.actual.to_numpy(dtype=float)
            first_test = len(y) - 12
            eligible = group.week_start.dt.year.eq(2015).to_numpy() & (np.arange(len(y)) < first_test)
            alpha = choose_alpha(y[eligible])
            history = y[:first_test]
            residuals = {method: [] for method in METHODS}
            for origin in range(8, len(history)):
                for method, estimate in zip(METHODS, predict(history[:origin], alpha)):
                    for actual in history[origin:origin+4]:
                        residuals[method].append(actual - estimate)
            checks = []
            for origin in range(first_test, len(y)):
                for method, estimate in zip(METHODS, predict(y[:origin], alpha)):
                    for ahead in range(1, min(4, len(y)-origin)+1):
                        actual = y[origin+ahead-1]
                        low, high = poisson.ppf([0.1, 0.9], estimate)
                        checks.append((method, ahead, actual, estimate, low <= actual <= high))
            use_residuals = np.mean([covered for _, _, _, _, covered in checks]) < .7
            for method, ahead, actual, estimate, covered in checks:
                low, high = interval(estimate, residuals[method], use_residuals)
                errors.append((component, method, ahead, abs(actual-estimate),
                               low <= actual <= high, covered, use_residuals))
            for week, actual in zip(group.week_start, y):
                rows.append((component, week, "observed", actual, None, None, "actual"))
            for method, estimate in zip(METHODS, predict(y, alpha)):
                low, high = interval(estimate, residuals[method], use_residuals)
                for ahead in range(1, 5):
                    week = group.week_start.iloc[-1] + pd.Timedelta(weeks=ahead + 1)
                    rows.append((component, week, method, estimate, low, high, "forecast"))
            reactive, total = db.execute("""
                SELECT count(*) FILTER (WHERE replacement_class = 'reactive'), count(*)
                FROM vw_replacement_class WHERE component = ?
            """, [component]).fetchone()
            partial = db.execute("""
                SELECT count(*) FROM fact_maintenance
                WHERE component = ? AND datetime >= ? + INTERVAL 1 WEEK
            """, [component, group.week_start.iloc[-1]]).fetchone()[0]
            rows.append((component, group.week_start.iloc[-1] + pd.Timedelta(weeks=1),
                         "observed", partial, None, None, "partial"))
            shares.append((component, len(y), alpha, reactive / total))
        tables = {
            "forecast_parts": pd.DataFrame(rows, columns=["component", "week_start", "method",
                                                         "forecast", "low", "high", "kind"]),
            "forecast_errors": pd.DataFrame(errors, columns=["component", "method", "ahead", "error", "covered", "poisson_covered", "empirical"]),
            "forecast_shares": pd.DataFrame(shares, columns=["component", "weeks", "alpha", "reactive_share"]),
        }
        for name, table in tables.items():
            db.register("forecast_output", table)
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM forecast_output")
            db.unregister("forecast_output")


if __name__ == "__main__":
    forecast()
