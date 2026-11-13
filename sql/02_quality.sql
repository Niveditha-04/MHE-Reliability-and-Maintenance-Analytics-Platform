SELECT 'duplicate machine hour', 'fact_telemetry', coalesce(sum(copies - 1), 0)
FROM (
    SELECT count(*) AS copies
    FROM fact_telemetry
    GROUP BY machine_id, datetime
    HAVING count(*) > 1
);

-- The fixed hourly grid includes both endpoints and catches missing edge hours.
WITH missing AS (
    SELECT m.machine_id, h.datetime
    FROM (SELECT DISTINCT machine_id FROM dim_machine) AS m
    CROSS JOIN ref_window AS w
    CROSS JOIN generate_series(w.window_start, w.window_end, INTERVAL 1 HOUR) AS h(datetime)
    ANTI JOIN fact_telemetry AS t
        ON m.machine_id = t.machine_id AND h.datetime = t.datetime
), runs AS (
    SELECT machine_id, datetime,
           datetime - INTERVAL 1 HOUR * row_number() OVER (
               PARTITION BY machine_id ORDER BY datetime
           ) AS gap
    FROM missing
), gaps AS (
    SELECT machine_id, min(datetime) AS first_missing,
           max(datetime) AS last_missing, count(*) AS hours_missing
    FROM runs
    GROUP BY machine_id, gap
)
SELECT 'missing hourly readings', 'fact_telemetry',
       coalesce(sum(hours_missing), 0),
       list(gaps ORDER BY machine_id, first_missing)
FROM gaps;

SELECT 'orphan machine', 'fact_telemetry', count(*)
FROM fact_telemetry ANTI JOIN dim_machine USING (machine_id)
UNION ALL
SELECT 'orphan machine', 'fact_error', count(*)
FROM fact_error ANTI JOIN dim_machine USING (machine_id)
UNION ALL
SELECT 'orphan machine', 'fact_maintenance', count(*)
FROM fact_maintenance ANTI JOIN dim_machine USING (machine_id)
UNION ALL
SELECT 'orphan machine', 'fact_failure', count(*)
FROM fact_failure ANTI JOIN dim_machine USING (machine_id);

-- Sensor specifications are unavailable, so no upper limits are assumed.
SELECT 'invalid sensor value', 'fact_telemetry', count(*)
FROM fact_telemetry
WHERE volt < 0 OR rotate < 0 OR pressure < 0 OR vibration < 0
   OR NOT isfinite(volt) OR NOT isfinite(rotate)
   OR NOT isfinite(pressure) OR NOT isfinite(vibration);

SELECT 'failure without replacement', 'fact_failure', count(*), 'warn'
FROM fact_failure
ANTI JOIN fact_maintenance USING (machine_id, component, datetime);

SELECT 'duplicate event', 'fact_error', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM fact_error GROUP BY machine_id, datetime, error_id);

SELECT 'duplicate event', 'fact_maintenance', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM fact_maintenance GROUP BY machine_id, datetime, component);

SELECT 'duplicate event', 'fact_failure', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM fact_failure GROUP BY machine_id, datetime, component);

SELECT 'duplicate dimension key', 'dim_machine', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM dim_machine GROUP BY machine_id);

SELECT 'duplicate dimension key', 'dim_site', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM dim_site GROUP BY site_id);

SELECT 'duplicate dimension key', 'dim_component', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM dim_component GROUP BY component);

SELECT 'duplicate dimension key', 'dim_date', coalesce(sum(copies - 1), 0)
FROM (SELECT count(*) AS copies FROM dim_date GROUP BY date);

SELECT 'row count differs from raw', 'fact_telemetry', abs(count(*) - (
    SELECT rows FROM raw_fact_counts WHERE table_name = 'fact_telemetry'
))
FROM fact_telemetry;

SELECT 'row count differs from raw', 'fact_error', abs(count(*) - (
    SELECT rows FROM raw_fact_counts WHERE table_name = 'fact_error'
))
FROM fact_error;

SELECT 'row count differs from raw', 'fact_maintenance', abs(count(*) - (
    SELECT rows FROM raw_fact_counts WHERE table_name = 'fact_maintenance'
))
FROM fact_maintenance;

SELECT 'row count differs from raw', 'fact_failure', abs(count(*) - (
    SELECT rows FROM raw_fact_counts WHERE table_name = 'fact_failure'
))
FROM fact_failure;

SELECT 'orphan component', 'fact_maintenance', count(*)
FROM fact_maintenance ANTI JOIN dim_component USING (component);

SELECT 'orphan component', 'fact_failure', count(*)
FROM fact_failure ANTI JOIN dim_component USING (component);

SELECT 'orphan component', 'assumptions_cost', count(*)
FROM assumptions_cost ANTI JOIN dim_component USING (component);

SELECT 'invalid equipment type', 'dim_machine', count(*)
FROM dim_machine WHERE equipment_type NOT IN ('conveyor', 'sorter');

SELECT 'timestamp off hour', 'fact_telemetry', count(*)
FROM fact_telemetry WHERE datetime <> date_trunc('hour', datetime);

SELECT 'timestamp off hour', 'fact_error', count(*)
FROM fact_error WHERE datetime <> date_trunc('hour', datetime);

SELECT 'timestamp off hour', 'fact_maintenance', count(*)
FROM fact_maintenance WHERE datetime <> date_trunc('hour', datetime);

SELECT 'timestamp off hour', 'fact_failure', count(*)
FROM fact_failure WHERE datetime <> date_trunc('hour', datetime);

SELECT 'timestamp outside window', 'fact_error', count(*)
FROM fact_error CROSS JOIN ref_window WHERE datetime NOT BETWEEN window_start AND window_end;

SELECT 'timestamp outside window', 'fact_failure', count(*)
FROM fact_failure CROSS JOIN ref_window WHERE datetime NOT BETWEEN window_start AND window_end;

SELECT 'timestamp outside window', 'fact_maintenance', count(*)
FROM fact_maintenance CROSS JOIN ref_window WHERE datetime > window_end;
