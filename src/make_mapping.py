import csv
from pathlib import Path

MAPPING = Path(__file__).resolve().parents[1] / "data" / "sim_mapping.csv"


if __name__ == "__main__":
    MAPPING.parent.mkdir(parents=True, exist_ok=True)
    with MAPPING.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(("machine_id", "site_id", "equipment_type"))
        for machine in range(1, 101):
            site = "ABCDE"[(machine - 1) // 20]
            equipment = "conveyor" if machine % 2 else "sorter"
            writer.writerow((machine, f"DC-{site}", equipment))
