import duckdb

from load_data import DATABASE, ROOT

TABLES = (
    "dim_machine", "dim_component", "vw_cost_detail", "vw_top_assets",
    "vw_events_monthly", "vw_machine_monthly",
)



def export():
    sql = (ROOT / "sql" / "04_bi.sql").read_text()
    with duckdb.connect(str(DATABASE)) as db:
        db.execute(sql)
        for table in TABLES:
            db.table(table).write_csv(str(DATABASE.parent / f"{table}.csv"), header=True)


if __name__ == "__main__":
    export()
