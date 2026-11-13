CREATE OR REPLACE TABLE rule_action AS
SELECT component, 'Review replacement interval for ' || component AS recommended_action
FROM dim_component;

CREATE OR REPLACE VIEW vw_cost_detail AS
WITH replacement_cost AS (
    SELECT r.machine_id, date_trunc('month', r.datetime)::DATE AS month, r.component,
           count(*) AS replacements, sum(c.part_cost + c.labor_cost) AS assumed_replacement_cost
    FROM vw_replacement_class AS r JOIN assumptions_cost AS c USING (component)
    GROUP BY ALL
), downtime_cost AS (
    SELECT f.machine_id, date_trunc('month', f.datetime)::DATE AS month, f.component,
           sum(e.downtime_hours / e.components_failed) AS allocated_downtime_hours,
           sum(e.downtime_hours / e.components_failed * c.downtime_cost_per_hour) AS assumed_downtime_cost
    FROM vw_window_failures AS f
    JOIN vw_downtime_events AS e ON e.machine_id = f.machine_id AND e.failure_time = f.datetime
    JOIN assumptions_cost AS c USING (component)
    GROUP BY ALL
)
SELECT machine_id, month, component, coalesce(replacements, 0) AS replacements,
       coalesce(allocated_downtime_hours, 0) AS allocated_downtime_hours,
       coalesce(assumed_replacement_cost, 0) AS assumed_replacement_cost,
       coalesce(assumed_downtime_cost, 0) AS assumed_downtime_cost
FROM replacement_cost FULL JOIN downtime_cost USING (machine_id, month, component);

CREATE OR REPLACE VIEW vw_cost_monthly AS
SELECT month, component, sum(replacements) AS replacements,
       sum(allocated_downtime_hours) AS allocated_downtime_hours,
       sum(assumed_replacement_cost) AS assumed_replacement_cost,
       sum(assumed_downtime_cost) AS assumed_downtime_cost,
       sum(assumed_replacement_cost + assumed_downtime_cost) AS assumed_total_cost
FROM vw_cost_detail
GROUP BY month, component;

CREATE OR REPLACE VIEW vw_top_assets AS
WITH components AS (
    SELECT machine_id, component, count(*) AS failures
    FROM vw_window_failures GROUP BY machine_id, component
    QUALIFY row_number() OVER (PARTITION BY machine_id ORDER BY count(*) DESC, component) = 1
), ranks AS (
    SELECT machine_id, site_id, equipment_type, model, failures, mtbf_hours_assumed_repair,
           rank() OVER (ORDER BY failures DESC) AS failure_rank,
           rank() OVER (ORDER BY mtbf_hours_assumed_repair ASC NULLS LAST) AS mtbf_rank
    FROM vw_kpi_machine
)
SELECT r.* EXCLUDE (failure_rank, mtbf_rank), c.component AS top_failing_component,
       (failure_rank + mtbf_rank) / 2.0 AS risk_score,
       coalesce(a.recommended_action, 'Continue routine inspection') AS recommended_action
FROM ranks AS r
LEFT JOIN components AS c USING (machine_id)
LEFT JOIN rule_action AS a USING (component)
ORDER BY risk_score, r.failures DESC, r.machine_id;

CREATE OR REPLACE VIEW vw_events_monthly AS
WITH failures AS (
    SELECT machine_id, date_trunc('month', datetime)::DATE AS month, component, count(*) AS failures
    FROM vw_window_failures GROUP BY ALL
), replacements AS (
    SELECT machine_id, date_trunc('month', datetime)::DATE AS month, component,
           count(*) FILTER (WHERE replacement_class = 'reactive') AS reactive,
           count(*) FILTER (WHERE replacement_class = 'planned') AS planned
    FROM vw_replacement_class GROUP BY ALL
)
SELECT machine_id, month, component, coalesce(failures, 0) AS failures,
       coalesce(reactive, 0) AS reactive, coalesce(planned, 0) AS planned
FROM failures FULL JOIN replacements USING (machine_id, month, component);

CREATE OR REPLACE VIEW vw_machine_monthly AS
WITH months AS (
    SELECT DISTINCT date_trunc('month', date)::DATE AS month
    FROM dim_date CROSS JOIN ref_window
    WHERE date >= window_start::DATE AND date <= window_end::DATE
), hours AS (
    SELECT machine_id, month,
           epoch(least(window_end, month + INTERVAL 1 MONTH) -
                 greatest(window_start, month)) / 3600 AS window_hours
    FROM dim_machine CROSS JOIN months CROSS JOIN ref_window
), downtime AS (
    SELECT e.machine_id, h.month,
           sum(epoch(least(e.failure_time + e.downtime_hours * INTERVAL 1 HOUR,
                           h.month + INTERVAL 1 MONTH) -
                     greatest(e.failure_time, h.month)) / 3600) AS downtime_hours
    FROM vw_downtime_events AS e JOIN months AS h
      ON e.failure_time < h.month + INTERVAL 1 MONTH
     AND e.failure_time + e.downtime_hours * INTERVAL 1 HOUR > h.month
    GROUP BY ALL
), events AS (
    SELECT machine_id, date_trunc('month', failure_time)::DATE AS month,
           sum(components_failed) AS failures, sum(mttr_hours) AS mttr_total,
           count(mttr_hours) AS mttr_events
    FROM vw_downtime_events GROUP BY ALL
), replacements AS (
    SELECT machine_id, month, sum(reactive) AS reactive, sum(planned) AS planned
    FROM vw_events_monthly GROUP BY ALL
)
SELECT h.machine_id, h.month, h.window_hours, coalesce(d.downtime_hours, 0) AS downtime_hours,
       h.window_hours - coalesce(d.downtime_hours, 0) AS operating_hours,
       coalesce(e.failures, 0) AS failures, coalesce(e.mttr_total, 0) AS mttr_total,
       coalesce(e.mttr_events, 0) AS mttr_events, coalesce(r.reactive, 0) AS reactive,
       coalesce(r.planned, 0) AS planned
FROM hours AS h
LEFT JOIN downtime AS d USING (machine_id, month)
LEFT JOIN events AS e USING (machine_id, month)
LEFT JOIN replacements AS r USING (machine_id, month)
WHERE h.window_hours > 0;
