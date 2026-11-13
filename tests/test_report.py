import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from weekly_report import snapshot


def command(*args, env=None):
    return subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=False).returncode


def test_report():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        database = root / "sample.duckdb"
        reports = root / "reports"
        env = os.environ | {"MHE_DATABASE": str(database),
                            "MHE_SAMPLE_DIR": str(ROOT / "data" / "sample")}
        exports = root / "exports"
        assert command("src/weekly_report.py", "--sample", "--reports", str(reports),
                       "--sample-exports", str(exports)) == 0
        assert len(list(exports.glob("*.csv"))) == 13
        report = reports / "weekly_report.md"
        assert report.read_text().startswith("Status: PASSED\n")
        title, blank, scope = report.read_text().splitlines()[2:5]
        assert (title, blank, scope) == (
            "# Weekly reliability report", "",
            "Scope: synthetic sample, not the Kaggle data. Values show that the pipeline runs and are not results.",
        )
        assert command("src/load_data.py", env=env) == 0
        copy = root / "broken.duckdb"
        copy.write_bytes(database.read_bytes())
        with duckdb.connect(str(copy)) as db:
            db.execute("INSERT INTO fact_telemetry SELECT * FROM fact_telemetry LIMIT 1")
        assert command("src/weekly_report.py", "--database", str(copy),
                       "--reports", str(reports)) == 1
        assert report.read_text().startswith("Status: FAILED\n")

        path = root / "fixture.csv"
        first = [1, 2, 3, 4, 5]
        second = [2, 1, 4, 4, 8]
        assert snapshot(path, date(2026, 11, 2), first) == [None] * 5
        assert snapshot(path, date(2026, 11, 9), second) == [1, -1, 1, 0, 3]
        assert snapshot(path, date(2026, 11, 9), second) == [1, -1, 1, 0, 3]
        assert snapshot(path, date(2026, 11, 23), second) == [None] * 5


if __name__ == "__main__":
    test_report()
    print("Sample report, duplicate gate, and snapshot checks passed")
