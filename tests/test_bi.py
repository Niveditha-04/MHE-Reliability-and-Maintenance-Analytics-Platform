from pathlib import Path

import duckdb

DATABASE = Path(__file__).resolve().parents[1] / "data" / "processed" / "maintenance.duckdb"


def test_exports():
    with duckdb.connect(str(DATABASE), read_only=True) as db:
        assert db.sql("""
            SELECT sum(c.replacements) = any_value(n.reactive + n.planned),
                   sum(c.allocated_downtime_hours) = any_value(n.downtime_hours),
                   sum(c.assumed_downtime_cost) = 500 * any_value(n.downtime_hours),
                   sum(c.assumed_replacement_cost) = (
                       SELECT sum(part_cost + labor_cost)
                       FROM vw_replacement_class JOIN assumptions_cost USING (component)
                   )
            FROM vw_cost_monthly c CROSS JOIN vw_kpi_network n
        """).fetchone() == (True, True, True, True)
        assert db.sql("""
            SELECT sum(m.failures) = any_value(n.failures),
                   sum(m.window_hours) = any_value(n.window_hours),
                   sum(m.downtime_hours) = any_value(n.downtime_hours),
                   sum(m.operating_hours) = any_value(n.operating_hours),
                   sum(m.reactive) = any_value(n.reactive),
                   sum(m.planned) = any_value(n.planned),
                   sum(m.mttr_total) / sum(m.mttr_events) = any_value(n.mttr_proxy_hours)
            FROM vw_machine_monthly m CROSS JOIN vw_kpi_network n
        """).fetchone() == (True,) * 7
        assert db.sql("""
            SELECT sum(failures) FROM vw_machine_monthly JOIN dim_machine USING (machine_id)
            WHERE site_id = 'DC-A'
        """).fetchone() == (150,)
        assert db.sql("""
            SELECT count(*), count(DISTINCT machine_id) FROM vw_top_assets
        """).fetchone() == (100, 100)
        assert db.sql("""
            SELECT list(machine_id ORDER BY network_position), count(DISTINCT rank_scope), min(rank_scope)
            FROM vw_top_assets WHERE network_position <= 10
        """).fetchone() == ([99, 98, 17, 22, 37, 83, 20, 71, 16, 13], 1, "network")
        assert db.sql("""
            SELECT sum(failures), sum(reactive), sum(planned) FROM vw_events_monthly
        """).fetchone() == (761, 743, 2136)
        assert db.sql("""
            SELECT repair_hours, assumed_total_cost
            FROM vw_cost_sensitivity ORDER BY repair_hours
        """).fetchall() == [(4, 2622630), (8, 4056630), (12, 5490630),
                             (24, 9792630), (48, 18348630)]
        assert db.sql("""
            SELECT machine_id, recommended_action FROM vw_top_assets
            WHERE machine_id IN (83, 99) ORDER BY machine_id
        """).fetchall() == [
            (83, "Inspect comp4 before the next scheduled replacement"),
            (99, "Check model fault pattern and review comp2 replacement interval"),
        ]
        for name in ("vw_machine_monthly", "vw_cost_detail", "vw_events_monthly", "vw_top_assets"):
            exported = db.read_csv(str(DATABASE.parent / f"{name}.csv"))
            assert exported.count("*").fetchone() == db.table(name).count("*").fetchone()


if __name__ == "__main__":
    test_exports()
    print("Cost, monthly KPIs, DC-A and export reconciliation passed")
