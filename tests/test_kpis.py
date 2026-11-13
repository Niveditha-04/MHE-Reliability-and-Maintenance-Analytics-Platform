from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "processed" / "maintenance.duckdb"
SQL = (ROOT / "sql" / "03_kpis.sql").read_text()


def reconcile(db):
    failures, = db.execute("""
        SELECT count(*) FROM fact_failure CROSS JOIN ref_window
        WHERE datetime >= window_start AND datetime < window_end
    """).fetchone()
    for scope in ("machine", "site", "model", "equipment_type", "component", "network"):
        assert db.table(f"vw_kpi_{scope}").aggregate("sum(failures)").fetchone() == (failures,)
    assert db.execute("""
        SELECT reactive + planned = (
            SELECT count(*) FROM fact_maintenance CROSS JOIN ref_window
            WHERE datetime >= window_start AND datetime < window_end
        ) FROM vw_kpi_network
    """).fetchone() == (True,)
    assert db.execute("""
        SELECT count(*) FROM vw_kpi_machine
        WHERE availability_proxy_assumed_repair IS NULL
           OR availability_proxy_assumed_repair NOT BETWEEN 0 AND 1
           OR downtime_hours > window_hours
           OR (failures > 0 AND mtbf_hours_assumed_repair IS NULL)
    """).fetchone() == (0,)


def fixture():
    with duckdb.connect() as db:
        db.execute((ROOT / "tests" / "fixtures" / "kpis.sql").read_text())
        db.execute(SQL)
        reconcile(db)
        assert db.execute("""
            SELECT components_failed, mttr_hours, downtime_hours
            FROM vw_downtime_events ORDER BY failure_time
        """).fetchall() == [(2, 3.0, 3.0), (1, None, 12.0)]
        assert db.execute("""
            SELECT failures, downtime_hours, operating_hours, mtbf_hours_assumed_repair,
                   mttr_proxy_hours, availability_proxy_assumed_repair, reactive, planned
            FROM vw_kpi_network
        """).fetchone() == (3, 15, 33, 11, 3, 33 / 48, 3, 1)
        assert db.execute("""
            SELECT failures, mtbf_hours_assumed_repair
            FROM vw_kpi_machine WHERE machine_id = 2
        """).fetchone() == (0, None)
        assert db.execute("""
            SELECT repair_hours, downtime_hours FROM vw_availability_sensitivity ORDER BY repair_hours
        """).fetchall() == [(4, 7), (8, 11), (12, 15), (24, 22), (48, 22)]
        db.execute("DELETE FROM fact_maintenance WHERE maintenance_id = 4")
        assert db.execute("""
            SELECT mttr_hours, downtime_hours FROM vw_downtime_events ORDER BY failure_time
        """).fetchall() == [(None, 3.0), (None, 12.0)]
        assert db.execute("""
            SELECT failures_without_replacement FROM vw_kpi_machine ORDER BY machine_id
        """).fetchall() == [(1,), (0,)]
        db.execute("DELETE FROM fact_failure")
        assert db.execute("""
            SELECT min(downtime_hours), max(downtime_hours), min(availability_proxy_assumed_repair)
            FROM vw_availability_sensitivity
        """).fetchone() == (0, 0, 1)


if __name__ == "__main__":
    with duckdb.connect(str(DATABASE), read_only=True) as database:
        reconcile(database)
        assert database.execute("""
            SELECT failures, downtime_hours, mtbf_hours_assumed_repair, mttr_proxy_hours
            FROM vw_kpi_machine WHERE machine_id = 1
        """).fetchone() == (7, 84, (8760 - 84) / 7, 360)
        assert database.execute("""
            SELECT failures, downtime_hours, mtbf_hours_assumed_repair, mttr_proxy_hours
            FROM vw_kpi_machine WHERE machine_id = 73
        """).fetchone() == (12, 3 + 11 * 12, (8760 - 135) / 12, (3 + 10 * 360 + 1080) / 12)
        assert database.execute("""
            SELECT failures, failures_without_replacement
            FROM vw_kpi_network
        """).fetchone() == (761, 18)
    print("Source reconciliation and machine 1 hand check passed")
    fixture()
    print("In-memory KPI fixture passed")
