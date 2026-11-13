import duckdb

from load_data import DATABASE

TABLES = (
    "dim_machine", "dim_component", "vw_cost_detail", "vw_top_assets",
    "vw_events_monthly", "vw_machine_monthly", "vw_cost_sensitivity",
    "model_machine_risk", "model_metrics", "model_threshold_costs", "forecast_parts",
)



def export():
    with duckdb.connect(str(DATABASE), read_only=True) as db:
        for table in TABLES:
            db.table(table).write_csv(str(DATABASE.parent / f"{table}.csv"), header=True)


if __name__ == "__main__":
    export()
