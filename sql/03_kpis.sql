CREATE OR REPLACE VIEW vw_window_failures AS
SELECT DISTINCT f.machine_id, f.datetime, f.component,
       NOT EXISTS (
           SELECT 1 FROM fact_maintenance AS m
           WHERE m.machine_id = f.machine_id AND m.datetime = f.datetime AND m.component = f.component
       ) AS failure_without_replacement
FROM fact_failure AS f CROSS JOIN ref_window
WHERE f.datetime >= window_start AND f.datetime < window_end;

CREATE OR REPLACE VIEW vw_replacement_class AS
SELECT m.maintenance_id, m.machine_id, m.datetime, m.component,
       CASE WHEN f.machine_id IS NULL THEN 'planned' ELSE 'reactive' END AS replacement_class
FROM fact_maintenance AS m
CROSS JOIN ref_window AS w
LEFT JOIN vw_window_failures AS f USING (machine_id, datetime, component)
WHERE m.datetime >= w.window_start AND m.datetime < w.window_end;

CREATE OR REPLACE VIEW vw_failure_intervals AS
WITH events AS (
    SELECT machine_id, datetime AS failure_time, count(*) AS components_failed,
           lead(datetime) OVER (PARTITION BY machine_id ORDER BY datetime) AS next_failure
    FROM vw_window_failures
    GROUP BY machine_id, datetime
)
SELECT e.machine_id, e.failure_time, e.components_failed,
       m.datetime AS next_maintenance_at,
       epoch(m.datetime - e.failure_time) / 3600 AS mttr_hours,
       epoch(least(m.datetime, e.next_failure, w.window_end) - e.failure_time) / 3600
           AS event_limit_hours
FROM events AS e
ASOF LEFT JOIN fact_maintenance AS m
    ON e.machine_id = m.machine_id AND e.failure_time < m.datetime
CROSS JOIN ref_window AS w;

CREATE OR REPLACE VIEW vw_downtime_events AS
SELECT machine_id, failure_time, components_failed, next_maintenance_at, mttr_hours,
       least(a.value, event_limit_hours) AS downtime_hours
FROM vw_failure_intervals
CROSS JOIN assumptions_repair AS a
WHERE a.parameter = 'assumed_repair_hours';

CREATE OR REPLACE VIEW vw_availability_sensitivity AS
WITH fleet AS (
    SELECT count(*) * any_value(window_hours) AS hours
    FROM dim_machine CROSS JOIN ref_window
), scenarios AS (
    SELECT repair_hours, coalesce(sum(least(repair_hours, event_limit_hours)) FILTER (WHERE event_limit_hours IS NOT NULL), 0) AS downtime_hours,
           coalesce(sum(components_failed), 0) AS failures
    FROM (VALUES (4), (8), (12), (24), (48)) AS assumptions(repair_hours)
    LEFT JOIN vw_failure_intervals ON true
    GROUP BY repair_hours
)
SELECT repair_hours, downtime_hours,
       (hours - downtime_hours) / nullif(hours, 0) AS availability_proxy_assumed_repair,
       (hours - downtime_hours) / nullif(failures, 0) AS mtbf_hours_assumed_repair
FROM scenarios CROSS JOIN fleet;

CREATE OR REPLACE VIEW vw_machine_totals AS
WITH events AS (
    SELECT machine_id, sum(components_failed) AS failures, sum(downtime_hours) AS downtime_hours,
           sum(mttr_hours) AS mttr_total, count(mttr_hours) AS mttr_events
    FROM vw_downtime_events GROUP BY machine_id
), unmatched AS (
    SELECT machine_id, count(*) AS failures_without_replacement
    FROM vw_window_failures WHERE failure_without_replacement GROUP BY machine_id
), replacements AS (
    SELECT machine_id, count(*) FILTER (WHERE replacement_class = 'reactive') AS reactive,
           count(*) FILTER (WHERE replacement_class = 'planned') AS planned
    FROM vw_replacement_class GROUP BY machine_id
)
SELECT m.machine_id, m.site_id, m.equipment_type, m.model, w.window_hours,
       coalesce(e.failures, 0) AS failures, coalesce(e.downtime_hours, 0) AS downtime_hours,
       coalesce(e.mttr_total, 0) AS mttr_total, coalesce(e.mttr_events, 0) AS mttr_events,
       coalesce(u.failures_without_replacement, 0) AS failures_without_replacement,
       coalesce(r.reactive, 0) AS reactive, coalesce(r.planned, 0) AS planned
FROM dim_machine AS m CROSS JOIN ref_window AS w
LEFT JOIN events AS e USING (machine_id)
LEFT JOIN unmatched AS u USING (machine_id)
LEFT JOIN replacements AS r USING (machine_id);

CREATE OR REPLACE VIEW vw_kpi_totals AS
SELECT grouping_id(machine_id, site_id, equipment_type, model) AS scope,
       machine_id, site_id, equipment_type, model,
       sum(window_hours) AS window_hours, sum(downtime_hours) AS downtime_hours,
       sum(window_hours - downtime_hours) AS operating_hours, sum(failures) AS failures,
       sum(mttr_total) AS mttr_total, sum(mttr_events) AS mttr_events,
       sum(failures_without_replacement) AS failures_without_replacement,
       sum(reactive) AS reactive, sum(planned) AS planned
FROM vw_machine_totals
GROUP BY GROUPING SETS ((machine_id, site_id, equipment_type, model),
                        (site_id), (equipment_type), (model), ());

CREATE OR REPLACE VIEW vw_kpi_rates AS
SELECT * EXCLUDE (mttr_total, mttr_events),
       1000 * failures / nullif(operating_hours, 0) AS failure_rate_per_1000h,
       operating_hours / nullif(failures, 0) AS mtbf_hours_assumed_repair,
       mttr_total / nullif(mttr_events, 0) AS mttr_proxy_hours,
       operating_hours / nullif(window_hours, 0) AS availability_proxy_assumed_repair,
       reactive / nullif(reactive + planned, 0) AS reactive_share,
       1 - reactive / nullif(reactive + planned, 0) AS planned_share
FROM vw_kpi_totals;

CREATE OR REPLACE VIEW vw_kpi_machine AS
SELECT * EXCLUDE (scope) FROM vw_kpi_rates WHERE scope = 0;

CREATE OR REPLACE VIEW vw_kpi_site AS
SELECT * EXCLUDE (scope, machine_id, equipment_type, model) FROM vw_kpi_rates WHERE scope = 11;

CREATE OR REPLACE VIEW vw_kpi_equipment_type AS
SELECT * EXCLUDE (scope, machine_id, site_id, model) FROM vw_kpi_rates WHERE scope = 13;

CREATE OR REPLACE VIEW vw_kpi_model AS
SELECT * EXCLUDE (scope, machine_id, site_id, equipment_type) FROM vw_kpi_rates WHERE scope = 14;

CREATE OR REPLACE VIEW vw_kpi_network AS
SELECT * EXCLUDE (scope, machine_id, site_id, equipment_type, model)
FROM vw_kpi_rates WHERE scope = 15;

CREATE OR REPLACE VIEW vw_kpi_component AS
WITH failures AS (
    SELECT f.component, count(*) AS failures, avg(e.mttr_hours) AS mttr_proxy_hours
    FROM vw_window_failures AS f
    JOIN vw_downtime_events AS e ON f.machine_id = e.machine_id AND f.datetime = e.failure_time
    GROUP BY f.component
), replacements AS (
    SELECT component,
           count(*) FILTER (WHERE replacement_class = 'reactive') / count(*) AS reactive_share
    FROM vw_replacement_class GROUP BY component
)
SELECT c.component, coalesce(f.failures, 0) AS failures,
       1000 * coalesce(f.failures, 0) / nullif(n.operating_hours, 0) AS failure_rate_per_1000h,
       f.mttr_proxy_hours, r.reactive_share
FROM dim_component AS c CROSS JOIN vw_kpi_network AS n
LEFT JOIN failures AS f USING (component)
LEFT JOIN replacements AS r USING (component);
