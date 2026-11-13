import csv
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "processed" / "maintenance.duckdb"


def check(database, report):
    result = subprocess.run(
        [sys.executable, str(ROOT / "src" / "run_quality.py"),
         "--database", str(database), "--report", str(report)],
        check=False,
    )
    with report.open(newline="", encoding="utf-8") as file:
        rows = {(row["check"], row["table"]): (int(row["rows_failed"]), row["status"])
                for row in csv.DictReader(file)}
    return result.returncode, rows


def test_quality():
    with TemporaryDirectory() as directory:
        copy = Path(directory) / DATABASE.name
        report = copy.with_suffix(".csv")
        shutil.copyfile(DATABASE, copy)
        clean_code, before = check(DATABASE, report)
        assert clean_code == 0, clean_code
        with duckdb.connect(str(copy)) as db:
            db.execute("""
                INSERT INTO fact_telemetry
                SELECT * FROM fact_telemetry ORDER BY machine_id, datetime LIMIT 1
            """)
            db.execute("""
                INSERT INTO fact_error
                VALUES (999, (SELECT window_start FROM ref_window), 'error1')
            """)
            db.execute("""
                DELETE FROM fact_telemetry WHERE machine_id = 2 AND datetime IN (
                    SELECT window_start FROM ref_window
                    UNION ALL SELECT window_start + INTERVAL 10 HOUR FROM ref_window
                )
            """)
            db.execute("UPDATE dim_machine SET age = NULL WHERE machine_id = 3")
            db.execute("INSERT INTO dim_machine SELECT * FROM dim_machine WHERE machine_id = 4")
        code, after = check(copy, report)
        assert code == 1, code
        expected = {
            ("duplicate machine hour", "fact_telemetry"): 1,
            ("orphan machine", "fact_error"): 1,
            ("missing hourly readings", "fact_telemetry"): 2,
            ("null age", "dim_machine"): 1,
            ("duplicate dimension key", "dim_machine"): 1,
        }
        for key, count in expected.items():
            assert before[key] == (0, "pass"), before[key]
            assert after[key] == (count, "fail"), after[key]
        with report.with_name("telemetry_gaps.csv").open(newline="") as file:
            gaps = list(csv.DictReader(file))
        with duckdb.connect(str(copy), read_only=True) as db:
            hours = db.execute("""
                SELECT window_start, window_start + INTERVAL 10 HOUR FROM ref_window
            """).fetchone()
        assert [(g["machine_id"], g["first_missing"], g["last_missing"], g["hours_missing"])
                for g in gaps] == [("2", str(hour), str(hour), "1") for hour in hours]
        print("Duplicate telemetry, orphan error, two missing hours, null and duplicate key caught")


if __name__ == "__main__":
    test_quality()
