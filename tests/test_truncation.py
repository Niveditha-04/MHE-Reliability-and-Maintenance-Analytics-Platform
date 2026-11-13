import duckdb
import numpy as np

import test_model as model

SQL = (model.DATABASE.parents[2] / "sql" / "05_features.sql").read_text()


def run():
    with duckdb.connect(str(model.DATABASE), read_only=True) as source:
        sample = source.sql("""
            WITH flags AS (
                SELECT m.machine_id, m.datetime, m.target,
                    EXISTS (FROM fact_error e WHERE e.machine_id=m.machine_id AND e.datetime=m.datetime) AS error_at_t,
                    EXISTS (FROM fact_maintenance r WHERE r.machine_id=m.machine_id AND r.datetime=m.datetime) AS replacement_at_t,
                    EXISTS (FROM fact_failure f WHERE f.machine_id=m.machine_id
                        AND f.datetime=m.datetime+INTERVAL 1 HOUR) AS failure_next
                FROM model_features m
            ), cases AS (
                SELECT *, CASE WHEN target=1 AND failure_next THEN 1
                               WHEN target=1 AND error_at_t THEN 2
                               WHEN target=0 AND replacement_at_t THEN 3
                               WHEN target=1 THEN 4
                               WHEN target=0 THEN 5 END AS category
                FROM flags
            )
            SELECT * EXCLUDE(category) FROM cases WHERE category IS NOT NULL
            QUALIFY row_number() OVER (PARTITION BY category ORDER BY datetime,machine_id)
                    <= CASE category WHEN 1 THEN 4 WHEN 4 THEN 3 WHEN 5 THEN 7 ELSE 3 END
            ORDER BY category, datetime, machine_id
        """).fetchall()
        assert len(sample) == 20 and sum(row[2] for row in sample) == 10
        assert all(sum(row[i] for row in sample) >= n for i,n in [(3,3),(4,3),(5,4)])
        for machine, hour, target, error, replacement, next_failure in sample:
            with duckdb.connect() as copy:
                for name in ("dim_machine", "ref_window", "fact_telemetry", "fact_error",
                             "fact_failure", "fact_maintenance"):
                    relation = source.table(name)
                    if name != "ref_window":
                        relation = relation.filter(f"machine_id = {int(machine)}")
                    copy.register("raw_copy", relation.df())
                    copy.execute(f"CREATE TABLE {name} AS FROM raw_copy")
                    if name.startswith("fact_"):
                        copy.execute(f"DELETE FROM {name} WHERE datetime > ?", [hour])
                copy.execute(SQL)
                original = source.execute("""
                    SELECT * EXCLUDE(machine_id, datetime, target, split)
                    FROM model_features WHERE machine_id=? AND datetime=?
                """, [machine, hour]).fetchone()
                truncated = copy.execute("""
                    SELECT * EXCLUDE(machine_id, datetime, target, split, hour_number,
                                     last_hour, target_later)
                    FROM model_feature_grid WHERE datetime=?
                """, [hour]).fetchone()
                assert len(original) == len(truncated) == 27
                assert original[:2] == truncated[:2]
                np.testing.assert_allclose(np.array(original[2:], dtype=float),
                                           np.array(truncated[2:], dtype=float), atol=1e-8)
            print(f"| {machine} | {hour} | {target} | {int(error)} | {int(replacement)} | {int(next_failure)} | pass |")


if __name__ == "__main__":
    run()
