import argparse
import csv
from pathlib import Path

import duckdb

from load_data import DATABASE, ROOT


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def null_checks(db):
    tables = db.execute("""
        SELECT DISTINCT table_name FROM information_schema.columns
        WHERE table_schema = 'main'
          AND (starts_with(table_name, 'dim_') OR starts_with(table_name, 'fact_')
               OR table_name = 'assumptions_cost')
        ORDER BY table_name
    """).fetchall()
    for table, in tables:
        relation = db.table(table)
        counts = relation.aggregate("count(*) - count(COLUMNS(*))").fetchone()
        for column, failed in zip(relation.columns, counts):
            yield f"null {column}", table, failed


def run(database, report):
    sql = (ROOT / "sql" / "02_quality.sql").read_text()
    results = []
    gaps = []
    with duckdb.connect(str(database), read_only=True) as db:
        checks = list(null_checks(db))
        for query in db.extract_statements(sql):
            checks.extend(db.execute(query).fetchall())

    for check, table, failed, *extra in checks:
        detail = extra[0] if extra else None
        if isinstance(detail, list):
            gaps.extend(detail)
        status = "pass"
        if failed:
            status = "warn" if detail == "warn" else "fail"
        results.append((check, table, failed, status))

    report.parent.mkdir(parents=True, exist_ok=True)
    write_csv(report, ("check", "table", "rows_failed", "status"), results)
    fields = ("machine_id", "first_missing", "last_missing", "hours_missing")
    write_csv(report.with_name("telemetry_gaps.csv"), fields,
              ([gap[field] for field in fields] for gap in gaps))
    print(f"Warnings: {sum(row[3] == 'warn' for row in results)}")
    return int(any(row[3] == "fail" for row in results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "data_quality_report.csv")
    args = parser.parse_args()
    raise SystemExit(run(args.database, args.report))
