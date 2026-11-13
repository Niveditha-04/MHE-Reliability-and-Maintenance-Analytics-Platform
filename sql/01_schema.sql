-- The window and inclusive reading count come from the telemetry range.
CREATE OR REPLACE TABLE ref_window AS
SELECT TIMESTAMP '2015-01-01 06:00:00' AS window_start,
       TIMESTAMP '2016-01-01 06:00:00' AS window_end,
       8760 AS window_hours, 8761 AS readings_per_machine;

CREATE OR REPLACE TABLE dim_site AS
SELECT DISTINCT site_id
FROM raw_mapping;

-- Site and equipment type are simulated.
CREATE OR REPLACE TABLE dim_machine AS
SELECT m.machineID AS machine_id, m.model, m.age, s.site_id, s.equipment_type
FROM raw_machines AS m
LEFT JOIN raw_mapping AS s ON m.machineID = s.machine_id;

CREATE OR REPLACE TABLE fact_telemetry AS
SELECT machineID AS machine_id, datetime::TIMESTAMP AS datetime,
       volt, rotate, pressure, vibration
FROM raw_telemetry;

CREATE OR REPLACE TABLE fact_error AS
SELECT machineID AS machine_id, datetime::TIMESTAMP AS datetime, errorID AS error_id
FROM raw_errors;

CREATE OR REPLACE TABLE fact_maintenance AS
SELECT row_number() OVER (ORDER BY machineID, datetime::TIMESTAMP, comp) AS maintenance_id,
       machineID AS machine_id, datetime::TIMESTAMP AS datetime, comp AS component
FROM raw_maintenance;

CREATE OR REPLACE TABLE fact_failure AS
SELECT row_number() OVER (ORDER BY machineID, datetime::TIMESTAMP, failure) AS failure_id,
       machineID AS machine_id, datetime::TIMESTAMP AS datetime, failure AS component
FROM raw_failures;

CREATE OR REPLACE TABLE dim_component AS
SELECT component
FROM (VALUES ('comp1'), ('comp2'), ('comp3'), ('comp4')) AS parts(component);

CREATE OR REPLACE TABLE raw_fact_counts AS
SELECT 'fact_telemetry' AS table_name, count(*) AS rows FROM raw_telemetry
UNION ALL SELECT 'fact_error', count(*) FROM raw_errors
UNION ALL SELECT 'fact_maintenance', count(*) FROM raw_maintenance
UNION ALL SELECT 'fact_failure', count(*) FROM raw_failures;

CREATE OR REPLACE TABLE dim_date AS
WITH dates AS (
    SELECT datetime::DATE AS date FROM fact_telemetry
    UNION ALL
    SELECT datetime::DATE FROM fact_error
    UNION ALL
    SELECT datetime::DATE FROM fact_maintenance
    UNION ALL
    SELECT datetime::DATE FROM fact_failure
)
SELECT day::DATE AS date, year(day) AS year, month(day) AS month,
       dayofmonth(day) AS day
FROM generate_series(
    (SELECT min(date) FROM dates),
    (SELECT max(date) FROM dates),
    INTERVAL 1 DAY
) AS calendar(day);

-- Every amount is assumed. The source contains no cost data.
CREATE OR REPLACE TABLE assumptions_cost AS
SELECT *
FROM (VALUES
    ('comp1', 150, 80, 500, 'assumed'),
    ('comp2', 250, 100, 500, 'assumed'),
    ('comp3', 350, 120, 500, 'assumed'),
    ('comp4', 450, 150, 500, 'assumed')
) AS costs(component, part_cost, labor_cost, downtime_cost_per_hour, cost_basis);

-- Repair hours are assumed.
CREATE OR REPLACE TABLE assumptions_repair AS
SELECT 'assumed_repair_hours' AS parameter, 12 AS value,
       'assumed, no repair duration in source' AS basis;
