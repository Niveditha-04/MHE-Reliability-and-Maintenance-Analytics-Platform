from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "processed" / "maintenance.duckdb"
SOURCES = {
    "raw_machines": "raw/PdM_machines.csv",
    "raw_telemetry": "raw/PdM_telemetry.csv",
    "raw_errors": "raw/PdM_errors.csv",
    "raw_maintenance": "raw/PdM_maint.csv",
    "raw_failures": "raw/PdM_failures.csv",
    "raw_mapping": "sim_mapping.csv",
}


def load():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    schema = (ROOT / "sql" / "01_schema.sql").read_text()
    with duckdb.connect(str(DATABASE)) as db:
        db.begin()
        for table, filename in SOURCES.items():
            db.read_csv(str(ROOT / "data" / filename), header=True).create_view(table)
        db.execute(schema)
        for table in SOURCES:
            db.execute(f"DROP VIEW {table}")
        db.commit()


if __name__ == "__main__":
    load()
