import csv
from datetime import datetime, timedelta

from load_data import ROOT

MACHINES = (1, 21, 41, 61, 81)
START = datetime(2015, 1, 1, 6)
HOUR = timedelta(hours=1)
PARTS = ("comp1", "comp2", "comp3", "comp4")


def write(folder, name, header, rows):
    with (folder / f"PdM_{name}.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def make():
    folder = ROOT / "data" / "sample"
    folder.mkdir(parents=True, exist_ok=True)
    with (ROOT / "data" / "sim_mapping.csv").open(newline="") as file:
        ids = {int(row["machine_id"]) for row in csv.DictReader(file)}
    assert set(MACHINES) <= ids

    telemetry, errors, maintenance, failures = [], [], [], []
    for index, (machine, spacing) in enumerate(zip(MACHINES, (510, 515, 520, 525, 520))):
        events = {240 + index * 29 + step * spacing: PARTS[step % 4]
                  for step in range(17)}
        assert len(events) == 17 and max(events) < 8760
        for offset in range(8761):
            time = START + offset * HOUR
            signal = int(any(offset + lead in events for lead in range(1, 25)))
            telemetry.append((time, machine, 165 + (offset + index) % 19 + signal * 7,
                              400 + offset % 23, 100 + offset % 17, 38 + offset % 11))
            if offset in events:
                failures.append((time, machine, events[offset]))
                maintenance.append((time, machine, events[offset]))
            if offset + 24 in events or offset % (121 + index) == 0:
                errors.append((time, machine, f"error{offset % 5 + 1}"))
        for part_index, part in enumerate(PARTS):
            for offset in range(-168 * (part_index + 1), 8760, 672 + index * 24):
                time = START + offset * HOUR
                if events.get(offset) != part:
                    maintenance.append((time, machine, part))

    write(folder, "machines", ("machineID", "model", "age"),
          ((machine, f"model{index % 4 + 1}", index + 3) for index, machine in enumerate(MACHINES)))
    write(folder, "telemetry", ("datetime", "machineID", "volt", "rotate", "pressure", "vibration"), telemetry)
    write(folder, "errors", ("datetime", "machineID", "errorID"), errors)
    write(folder, "maint", ("datetime", "machineID", "comp"), sorted(maintenance))
    write(folder, "failures", ("datetime", "machineID", "failure"), sorted(failures))


if __name__ == "__main__":
    make()
