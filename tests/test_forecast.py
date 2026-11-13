import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from forecast_parts import predict, smooth

assert smooth([2, 6, 4], 0.5) == 4
assert predict(np.arange(1, 9), 1) == (6.5, 4.5, 8)
print("Forecast fixture passed")
