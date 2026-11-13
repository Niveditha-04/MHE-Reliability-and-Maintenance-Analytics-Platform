CREATE OR REPLACE TABLE model_features AS
WITH errors AS (
    SELECT machine_id, datetime,
           count(*) FILTER (WHERE error_id = 'error1') AS error1,
           count(*) FILTER (WHERE error_id = 'error2') AS error2,
           count(*) FILTER (WHERE error_id = 'error3') AS error3,
           count(*) FILTER (WHERE error_id = 'error4') AS error4,
           count(*) FILTER (WHERE error_id = 'error5') AS error5
    FROM fact_error GROUP BY machine_id, datetime
), replacements AS (
    SELECT machine_id, datetime,
           max(datetime) FILTER (WHERE component = 'comp1') AS comp1,
           max(datetime) FILTER (WHERE component = 'comp2') AS comp2,
           max(datetime) FILTER (WHERE component = 'comp3') AS comp3,
           max(datetime) FILTER (WHERE component = 'comp4') AS comp4
    FROM fact_maintenance GROUP BY machine_id, datetime
), history AS (
    SELECT machine_id,
           max(comp1) AS comp1,
           max(comp2) AS comp2,
           max(comp3) AS comp3,
           max(comp4) AS comp4
    FROM replacements CROSS JOIN ref_window
    WHERE datetime < window_start GROUP BY machine_id
), failures AS (
    SELECT DISTINCT machine_id, datetime FROM fact_failure
), hourly AS (
    SELECT t.machine_id, t.datetime, m.age, m.model,
           row_number() OVER h AS hour_number,
           max(t.datetime) OVER (PARTITION BY t.machine_id) AS last_hour,
           min(f.datetime) OVER (
               PARTITION BY t.machine_id ORDER BY t.datetime
               ROWS BETWEEN 1 FOLLOWING AND 24 FOLLOWING
           ) AS next_failure,
           avg(t.volt) OVER h3 AS volt_mean_3h,
           stddev_pop(t.volt) OVER h3 AS volt_sd_3h,
           avg(t.rotate) OVER h3 AS rotate_mean_3h,
           stddev_pop(t.rotate) OVER h3 AS rotate_sd_3h,
           avg(t.pressure) OVER h3 AS pressure_mean_3h,
           stddev_pop(t.pressure) OVER h3 AS pressure_sd_3h,
           avg(t.vibration) OVER h3 AS vibration_mean_3h,
           stddev_pop(t.vibration) OVER h3 AS vibration_sd_3h,
           avg(t.volt) OVER h24 AS volt_mean_24h,
           stddev_pop(t.volt) OVER h24 AS volt_sd_24h,
           avg(t.rotate) OVER h24 AS rotate_mean_24h,
           stddev_pop(t.rotate) OVER h24 AS rotate_sd_24h,
           avg(t.pressure) OVER h24 AS pressure_mean_24h,
           stddev_pop(t.pressure) OVER h24 AS pressure_sd_24h,
           avg(t.vibration) OVER h24 AS vibration_mean_24h,
           stddev_pop(t.vibration) OVER h24 AS vibration_sd_24h,
           sum(coalesce(e.error1, 0)) OVER h24 AS error1_24h,
           sum(coalesce(e.error2, 0)) OVER h24 AS error2_24h,
           sum(coalesce(e.error3, 0)) OVER h24 AS error3_24h,
           sum(coalesce(e.error4, 0)) OVER h24 AS error4_24h,
           sum(coalesce(e.error5, 0)) OVER h24 AS error5_24h,
           epoch(t.datetime - greatest(max(r.comp1) OVER h, any_value(p.comp1) OVER h))
               / 3600 AS hours_since_comp1,
           epoch(t.datetime - greatest(max(r.comp2) OVER h, any_value(p.comp2) OVER h))
               / 3600 AS hours_since_comp2,
           epoch(t.datetime - greatest(max(r.comp3) OVER h, any_value(p.comp3) OVER h))
               / 3600 AS hours_since_comp3,
           epoch(t.datetime - greatest(max(r.comp4) OVER h, any_value(p.comp4) OVER h))
               / 3600 AS hours_since_comp4
    FROM fact_telemetry AS t
    JOIN dim_machine AS m USING (machine_id)
    LEFT JOIN errors AS e USING (machine_id, datetime)
    LEFT JOIN replacements AS r USING (machine_id, datetime)
    LEFT JOIN history AS p USING (machine_id)
    LEFT JOIN failures AS f USING (machine_id, datetime)
    WINDOW h AS (PARTITION BY t.machine_id ORDER BY t.datetime),
           h3 AS (h ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
           h24 AS (h ROWS BETWEEN 23 PRECEDING AND CURRENT ROW)
), split_bounds AS (
    SELECT window_start + INTERVAL 8 MONTH AS validation_start,
           window_start + INTERVAL 10 MONTH AS test_start
    FROM ref_window
)
SELECT * EXCLUDE (hour_number, last_hour, next_failure, validation_start, test_start),
       (next_failure IS NOT NULL)::INTEGER AS target,
       CASE WHEN datetime < validation_start THEN 'train'
            WHEN datetime < test_start THEN 'validation' ELSE 'test' END AS split
FROM hourly CROSS JOIN split_bounds
WHERE hour_number > 24 AND datetime + INTERVAL 24 HOUR <= last_hour
  AND datetime NOT BETWEEN validation_start - INTERVAL 24 HOUR
                       AND validation_start - INTERVAL 1 HOUR
  AND datetime NOT BETWEEN test_start - INTERVAL 24 HOUR
                       AND test_start - INTERVAL 1 HOUR;
