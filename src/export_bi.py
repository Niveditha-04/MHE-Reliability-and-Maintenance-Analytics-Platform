import duckdb

from load_data import DATABASE

TABLES = (
    "dim_machine", "dim_component", "vw_cost_detail", "vw_top_assets",
    "vw_events_monthly", "vw_machine_monthly", "vw_cost_sensitivity",
    "model_machine_risk", "model_metrics", "model_threshold_costs", "forecast_parts",
    "model_machine_current", "threshold_curve",
)



def export():
    with duckdb.connect(str(DATABASE), read_only=True) as db:
        for table in TABLES:
            relation = db.table("model_cost_curve" if table == "threshold_curve" else table)
            relation.write_csv(str(DATABASE.parent / f"{table}.csv"), header=True)


if __name__ == "__main__":
    export()
