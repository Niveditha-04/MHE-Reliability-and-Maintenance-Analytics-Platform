import csv
from datetime import datetime
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
TYPES = {
    "datetime": datetime.fromisoformat,
    "machineID": int,
    "age": int,
    "volt": float,
    "rotate": float,
    "pressure": float,
    "vibration": float,
}
FILES = (
    "PdM_telemetry.csv",
    "PdM_errors.csv",
    "PdM_maint.csv",
    "PdM_failures.csv",
    "PdM_machines.csv",
)


def inspect(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = csv.reader(source, strict=True)
        columns = next(rows)
        converters = [TYPES.get(column, str) for column in columns]
        timestamp_index = columns.index("datetime") if "datetime" in columns else None
        first = last = None
        samples = []
        count = 0
        for count, row in enumerate(rows, start=1):
            if len(row) != len(columns):
                raise ValueError(f"{path.name}: invalid field count on data row {count}")
            values = tuple(convert(value) for convert, value in zip(converters, row))
            if count <= 5:
                samples.append(values)
            if timestamp_index is not None:
                timestamp = values[timestamp_index]
                first = timestamp if first is None else min(first, timestamp)
                last = timestamp if last is None else max(last, timestamp)

    with path.open("rb") as source:
        file_rows = sum(1 for _ in source) - 1
    if count != file_rows:
        raise ValueError(f"{path.name}: parsed {count:,} rows, file has {file_rows:,}")

    print(path.name)
    print(f"  Shape: ({count:,}, {len(columns)})")
    print(f"  Columns: {', '.join(columns)}")
    dtypes = [convert.__name__ for convert in converters]
    if timestamp_index is not None:
        dtypes[timestamp_index] = "datetime"
    print(f"  Dtypes: {', '.join(dtypes)}")
    print(f"  Timestamp min/max: {first} / {last}" if first else "  No timestamps")
    print(f"  Row count check: passed ({path.stat().st_size:,} bytes)")
    print("  First five rows:")
    for values in samples:
        print("  " + " | ".join(str(value) for value in values))
    print()


if __name__ == "__main__":
    for filename in FILES:
        inspect(RAW / filename)
