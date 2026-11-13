import argparse
import csv
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from load_data import DATABASE, REPORTS, ROOT
from run_quality import run, write_csv

LABELS = ("Failures", "Availability proxy, assumed repair hours (%)",
          "MTBF, assumed repair hours (h)", "MTTR proxy, maintenance interval (h)",
          "Planned share, PM compliance proxy (%)")


def snapshot(path, week, values):
    history = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                history[date.fromisoformat(row["week"])] = [float(row[label]) for label in LABELS]
    prior = history.get(week - timedelta(days=7))
    history[week] = values
    write_csv(path, ("week", *LABELS),
              ((key, *history[key]) for key in sorted(history)[-2:]))
    return [current - old for current, old in zip(values, prior)] if prior else [None] * len(values)


def step(name, env):
    with TemporaryDirectory() as logs:
        with (Path(logs) / "step.log").open("w+") as output:
            result = subprocess.run([sys.executable, str(ROOT / "src" / name)],
                                    env=env, stdout=output, stderr=output, check=False)
            if result.returncode:
                if "GITHUB_ACTIONS" not in env:
                    output.seek(0)
                    print(output.read(), file=sys.stderr)
                raise RuntimeError(f"{name} exited with code {result.returncode}")


def publish(database, reports, scope, today, rebuild):
    reports.mkdir(parents=True, exist_ok=True)
    report = reports / "weekly_report.md"
    report.write_text("Status: FAILED\n\nThe pipeline did not complete.\n", encoding="utf-8")
    quality = reports / "data_quality_report.csv"
    if run(database, quality):
        report.write_text("Status: FAILED\n\nData quality checks failed.\n", encoding="utf-8")
        return 1
    env = os.environ | {"MHE_DATABASE": str(database), "MHE_REPORTS": str(database.parent) if rebuild else str(reports)}
    if rebuild:
        for name in ("train_model.py", "score_machines.py"):
            step(name, env)
    step("build_kpis.py", env)
    if rebuild:
        step("forecast_parts.py", env)
    step("export_bi.py", env)

    with quality.open(newline="", encoding="utf-8") as file:
        warnings = sum(row["status"] == "warn" for row in csv.DictReader(file))
    with duckdb.connect(str(database), read_only=True) as db:
        values = db.sql("""
            SELECT failures, 100 * availability_proxy_assumed_repair,
                   mtbf_hours_assumed_repair, mttr_proxy_hours, 100 * planned_share
            FROM vw_kpi_network
        """).fetchone()
        assets = db.sql("""
            SELECT machine_id, failures, risk_score, recommended_action
            FROM vw_top_assets ORDER BY network_position LIMIT 5
        """).fetchall()
    week = today - timedelta(days=today.weekday())
    changes = snapshot(reports / f"{scope}_snapshot.csv", week, values)
    lines = ["Status: PASSED", "", "# Weekly reliability report", "",
             f"Scope: {scope}. Week starting {week}.", "",
             f"Data quality: passed with {warnings} warning checks.", "",
             "| KPI | Value | Change from prior week |", "| --- | ---: | ---: |"]
    for label, value, change in zip(LABELS, values, changes):
        delta = f"{change:+.2f}" if change is not None else "Unavailable"
        lines.append(f"| {label} | {value:,.2f} | {delta} |")
    lines += ["", "Changes compare report runs on static source data. An unchanged",
              "source and calculation give zero change. Share changes are percentage points.",
              "", "## Top 5 assets", "", "| Machine | Failures | Rank score | Action |",
              "| ---: | ---: | ---: | --- |"]
    lines.extend(f"| {machine} | {failures} | {score:g} | {action} |"
                 for machine, failures, score, action in assets)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--reports", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    if args.reports is None:
        args.reports = REPORTS / "sample" if args.sample else REPORTS
    if not args.sample:
        return publish(args.database, args.reports, "full", args.as_of, False)
    args.reports.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as folder:
        database = Path(folder) / "maintenance.duckdb"
        env = os.environ | {"MHE_DATABASE": str(database), "MHE_SAMPLE_DIR": str(ROOT / "data" / "sample")}
        step("load_data.py", env)
        status = publish(database, args.reports, "sample", args.as_of, True)
        if status == 0:
            exports = ROOT / "data" / "processed" / "sample"
            exports.mkdir(parents=True, exist_ok=True)
            for file in database.parent.glob("*.csv"):
                shutil.copyfile(file, exports / file.name)
        return status


if __name__ == "__main__":
    raise SystemExit(main())
