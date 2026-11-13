import duckdb

from load_data import DATABASE, ROOT


def build():
    with duckdb.connect(str(DATABASE)) as db:
        db.begin()
        for name in ("03_kpis.sql", "04_bi.sql"):
            db.execute((ROOT / "sql" / name).read_text())
        db.commit()


if __name__ == "__main__":
    build()
