import duckdb

from load_data import DATABASE


def score():
    with duckdb.connect(str(DATABASE)) as db:
        db.execute("""
            CREATE OR REPLACE TABLE model_machine_risk AS
            WITH risks AS (
                SELECT machine_id, avg(probability) AS mean_risk
                FROM model_test_predictions GROUP BY machine_id
            )
            SELECT *, rank() OVER (ORDER BY mean_risk DESC) AS predicted_risk_rank
            FROM risks
        """)


if __name__ == "__main__":
    score()
