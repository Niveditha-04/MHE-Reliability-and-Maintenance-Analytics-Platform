import duckdb
import numpy as np

import test_model as model

SQL = (model.DATABASE.parents[2] / "sql" / "05_features.sql").read_text()


def run():
    with duckdb.connect(str(model.DATABASE), read_only=True) as source:
        pool = source.sql("""
            SELECT m.machine_id, m.datetime, m.target,
                EXISTS (FROM fact_error e WHERE e.machine_id=m.machine_id AND e.datetime=m.datetime),
                EXISTS (FROM fact_maintenance r WHERE r.machine_id=m.machine_id AND r.datetime=m.datetime),
                EXISTS (FROM fact_failure f WHERE f.machine_id=m.machine_id
                    AND f.datetime=m.datetime+INTERVAL 1 HOUR),
                m.split, CASE WHEN month(m.datetime)<=6 THEN 0
                              WHEN month(m.datetime)<=10 THEN 1 ELSE 2 END
            FROM model_features m
            WHERE m.datetime >= (SELECT window_start + INTERVAL 1 WEEK FROM ref_window)
              AND (m.target=1 OR EXISTS (FROM fact_maintenance r
                   WHERE r.machine_id=m.machine_id AND r.datetime=m.datetime)
                   OR (m.split <> 'train' AND m.machine_id <= 4))
            ORDER BY m.datetime,m.machine_id
        """).fetchall()
        sample = []
        for split, ids in [("validation", (1,2)), ("test", (3,4))]:
            for machine in ids:
                rows = [row for row in pool if row[0]==machine and row[6]==split]
                sample.extend((rows[0], rows[-1]))
        rng = np.random.default_rng(42)
        pool = [pool[i] for i in rng.permutation(len(pool))]
        for idx, minimum in [(5,3),(4,5),(3,5),(2,10),(None,30)]:
            for row in pool:
                if sum(1 for item in sample if idx is None or item[idx]) >= minimum:
                    break
                if (idx is None or row[idx]) and row not in sample:
                    if sum(item[0]==row[0] for item in sample)<2 and sum(item[7]==row[7] for item in sample)<10:
                        sample.append(row)
            assert sum(1 for item in sample if idx is None or item[idx]) >= minimum
        assert [sum(row[7]==band for row in sample) for band in range(3)] == [10]*3
        for machine, hour, target, error, replacement, next_failure, split, _ in sample:
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
            print(f"| {machine} | {hour} | {split} | {target} | {int(error)} | {int(replacement)} | {int(next_failure)} | pass |")


if __name__ == "__main__":
    run()
