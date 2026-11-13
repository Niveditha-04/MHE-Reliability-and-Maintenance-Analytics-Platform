import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATABASE = Path(os.environ.get("MHE_DATABASE", ROOT / "data" / "processed" / "maintenance.duckdb"))
REPORTS = Path(os.environ.get("MHE_REPORTS", ROOT / "reports"))
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
            source = ROOT / "data" / filename
            if table != "raw_mapping" and "MHE_SAMPLE_DIR" in os.environ:
                source = Path(os.environ["MHE_SAMPLE_DIR"]) / source.name
            db.read_csv(str(source), header=True).create_view(table)
        db.execute(schema)
        for table in SOURCES:
            db.execute(f"DROP VIEW {table}")
        db.commit()


if __name__ == "__main__":
    load()
