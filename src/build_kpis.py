import duckdb

from load_data import DATABASE, ROOT


def build():
    sql = (ROOT / "sql" / "03_kpis.sql").read_text()
    with duckdb.connect(str(DATABASE)) as db:
        db.execute(sql)


if __name__ == "__main__":
    build()
