import sys
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from forecast_parts import interval, predict, smooth, weekly
from load_data import DATABASE

assert smooth([2, 6, 4], 0.5) == 4
assert predict(np.arange(1, 9), 1) == (6.5, 4.5, 8)
print("Forecast fixture passed")

assert interval(10, [-2, 0, 2], True) == (8, 12)
with duckdb.connect(str(DATABASE), read_only=True) as db:
    assert len(weekly(db)) == 82 * 4
    assert db.sql("""
        SELECT min(week_start)::VARCHAR, max(week_start)::VARCHAR
        FROM forecast_parts WHERE kind = 'forecast'
    """).fetchone() == ("2016-01-04 06:00:00", "2016-01-25 06:00:00")
    assert db.sql("""
        SELECT sum(forecast) FROM forecast_parts WHERE kind = 'partial'
    """).fetchone() == (54,)
print("Forecast scope and partial week checks passed")
