CREATE OR REPLACE TABLE rule_action AS
SELECT * FROM (VALUES
    (1, 'model_pattern', 'Check model fault pattern and review {component} replacement interval'),
    (2, 'past_median', 'Inspect {component} before the next scheduled replacement'),
    (3, 'component_review', 'Review replacement interval for {component}'),
    (4, 'routine', 'Continue routine inspection')
) AS rules(priority, rule, action);

CREATE OR REPLACE VIEW vw_cost_detail AS
WITH replacement_cost AS (
    SELECT r.machine_id, date_trunc('month', r.datetime - INTERVAL 6 HOUR)::DATE AS reporting_month, r.component,
           count(*) AS replacements, sum(c.part_cost + c.labor_cost) AS assumed_replacement_cost
    FROM vw_replacement_class AS r JOIN assumptions_cost AS c USING (component)
    GROUP BY ALL
), downtime_cost AS (
    SELECT f.machine_id, date_trunc('month', f.datetime - INTERVAL 6 HOUR)::DATE AS reporting_month, f.component,
           sum(e.downtime_hours / e.components_failed) AS allocated_downtime_hours,
           sum(e.downtime_hours / e.components_failed * c.downtime_cost_per_hour) AS assumed_downtime_cost
    FROM vw_window_failures AS f
    JOIN vw_downtime_events AS e ON e.machine_id = f.machine_id AND e.failure_time = f.datetime
    JOIN assumptions_cost AS c USING (component)
    GROUP BY ALL
)
SELECT machine_id, reporting_month, component, coalesce(replacements, 0) AS replacements,
       coalesce(allocated_downtime_hours, 0) AS allocated_downtime_hours,
       coalesce(assumed_replacement_cost, 0) AS assumed_replacement_cost,
       coalesce(assumed_downtime_cost, 0) AS assumed_downtime_cost
FROM replacement_cost FULL JOIN downtime_cost USING (machine_id, reporting_month, component);

CREATE OR REPLACE VIEW vw_cost_monthly AS
SELECT reporting_month, component, sum(replacements) AS replacements,
       sum(allocated_downtime_hours) AS allocated_downtime_hours,
       sum(assumed_replacement_cost) AS assumed_replacement_cost,
       sum(assumed_downtime_cost) AS assumed_downtime_cost,
       sum(assumed_replacement_cost + assumed_downtime_cost) AS assumed_total_cost
FROM vw_cost_detail
GROUP BY reporting_month, component;

CREATE OR REPLACE VIEW vw_cost_sensitivity AS
WITH rates AS (
    SELECT f.machine_id, f.datetime, avg(c.downtime_cost_per_hour) AS hourly_cost
    FROM vw_window_failures AS f JOIN assumptions_cost AS c USING (component)
    GROUP BY f.machine_id, f.datetime
), scenarios AS (
    SELECT s.repair_hours,
           coalesce(sum(least(s.repair_hours, e.event_limit_hours) * r.hourly_cost), 0)
               AS assumed_downtime_cost
    FROM vw_availability_sensitivity AS s
    LEFT JOIN vw_failure_intervals AS e ON true
    LEFT JOIN rates AS r ON r.machine_id = e.machine_id AND r.datetime = e.failure_time
    GROUP BY s.repair_hours
), replacements AS (
    SELECT coalesce(sum(assumed_replacement_cost), 0) AS assumed_replacement_cost
    FROM vw_cost_monthly
)
SELECT repair_hours, assumed_replacement_cost, assumed_downtime_cost,
       assumed_replacement_cost + assumed_downtime_cost AS assumed_total_cost
FROM scenarios CROSS JOIN replacements;

CREATE OR REPLACE VIEW vw_component_replacement_history AS
WITH intervals AS (
    SELECT machine_id, component, datetime,
           epoch(datetime - lag(datetime) OVER (
               PARTITION BY machine_id, component ORDER BY datetime
           )) / 3600 AS interval_hours
    FROM fact_maintenance CROSS JOIN ref_window
    WHERE datetime < window_end
), medians AS (
    SELECT component, median(interval_hours) AS median_hours FROM intervals GROUP BY component
)
SELECT machine_id, component, max(datetime) AS latest_replacement, any_value(median_hours) AS median_hours
FROM intervals JOIN medians USING (component)
GROUP BY machine_id, component;

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
), scored AS (
    SELECT *, (failure_rank + mtbf_rank) / 2.0 AS risk_score,
           row_number() OVER (ORDER BY failure_rank + mtbf_rank, failures DESC, machine_id)
               AS network_position
    FROM ranks
)
SELECT s.* EXCLUDE (failure_rank, mtbf_rank), c.component AS top_failing_component,
       'network' AS rank_scope,
       replace(a.action, '{component}', coalesce(c.component, '')) AS recommended_action,
       CASE a.priority
           WHEN 1 THEN printf('%s rate %.3f vs network %.3f per 1,000 h',
                               s.model, m.failure_rate_per_1000h, n.failure_rate_per_1000h)
           WHEN 2 THEN printf('%s age %.0f h vs median %.0f h', c.component,
                               epoch(w.window_end - h.latest_replacement) / 3600, h.median_hours)
           WHEN 3 THEN printf('%s: %d failures', c.component, c.failures)
           ELSE 'No component failures'
       END AS action_basis
FROM scored AS s
LEFT JOIN components AS c USING (machine_id)
LEFT JOIN vw_component_replacement_history AS h USING (machine_id, component)
CROSS JOIN ref_window AS w
JOIN vw_kpi_model AS m ON s.model = m.model
CROSS JOIN vw_kpi_network AS n
JOIN rule_action AS a ON a.priority = CASE
    WHEN s.failure_rank <= 10 AND m.failure_rate_per_1000h > n.failure_rate_per_1000h THEN 1
    WHEN epoch(w.window_end - h.latest_replacement) / 3600 > h.median_hours THEN 2
    WHEN c.component IS NOT NULL THEN 3 ELSE 4 END
ORDER BY network_position;

CREATE OR REPLACE VIEW vw_events_monthly AS
WITH failures AS (
    SELECT machine_id, date_trunc('month', datetime - INTERVAL 6 HOUR)::DATE AS reporting_month, component, count(*) AS failures
    FROM vw_window_failures GROUP BY ALL
), replacements AS (
    SELECT machine_id, date_trunc('month', datetime - INTERVAL 6 HOUR)::DATE AS reporting_month, component,
           count(*) FILTER (WHERE replacement_class = 'reactive') AS reactive,
           count(*) FILTER (WHERE replacement_class = 'planned') AS planned
    FROM vw_replacement_class GROUP BY ALL
)
SELECT machine_id, reporting_month, component, coalesce(failures, 0) AS failures,
       coalesce(reactive, 0) AS reactive, coalesce(planned, 0) AS planned
FROM failures FULL JOIN replacements USING (machine_id, reporting_month, component);

CREATE OR REPLACE VIEW vw_machine_monthly AS
WITH months AS (
    SELECT month_start::DATE AS reporting_month
    FROM ref_window
    CROSS JOIN generate_series(
        date_trunc('month', window_start - INTERVAL 6 HOUR),
        date_trunc('month', window_end - INTERVAL 6 HOUR - INTERVAL 1 MICROSECOND),
        INTERVAL 1 MONTH
    ) AS months(month_start)
), hours AS (
    SELECT machine_id, reporting_month,
           epoch(least(window_end, reporting_month + INTERVAL 1 MONTH + INTERVAL 6 HOUR) -
                 greatest(window_start, reporting_month + INTERVAL 6 HOUR)) / 3600 AS window_hours
    FROM dim_machine CROSS JOIN months CROSS JOIN ref_window
), downtime AS (
    SELECT e.machine_id, h.reporting_month,
           sum(epoch(least(e.failure_time + e.downtime_hours * INTERVAL 1 HOUR,
                           h.reporting_month + INTERVAL 1 MONTH + INTERVAL 6 HOUR) -
                     greatest(e.failure_time, h.reporting_month + INTERVAL 6 HOUR)) / 3600) AS downtime_hours
    FROM vw_downtime_events AS e JOIN months AS h
      ON e.failure_time < h.reporting_month + INTERVAL 1 MONTH + INTERVAL 6 HOUR
     AND e.failure_time + e.downtime_hours * INTERVAL 1 HOUR > h.reporting_month + INTERVAL 6 HOUR
    GROUP BY ALL
), events AS (
    SELECT machine_id, date_trunc('month', failure_time - INTERVAL 6 HOUR)::DATE AS reporting_month,
           sum(components_failed) AS failures, sum(mttr_hours) AS mttr_total,
           count(mttr_hours) AS mttr_events
    FROM vw_downtime_events GROUP BY ALL
), replacements AS (
    SELECT machine_id, reporting_month, sum(reactive) AS reactive, sum(planned) AS planned
    FROM vw_events_monthly GROUP BY ALL
)
SELECT h.machine_id, h.reporting_month, h.window_hours, coalesce(d.downtime_hours, 0) AS downtime_hours,
       h.window_hours - coalesce(d.downtime_hours, 0) AS operating_hours,
       coalesce(e.failures, 0) AS failures, coalesce(e.mttr_total, 0) AS mttr_total,
       coalesce(e.mttr_events, 0) AS mttr_events, coalesce(r.reactive, 0) AS reactive,
       coalesce(r.planned, 0) AS planned
FROM hours AS h
LEFT JOIN downtime AS d USING (machine_id, reporting_month)
LEFT JOIN events AS e USING (machine_id, reporting_month)
LEFT JOIN replacements AS r USING (machine_id, reporting_month)
WHERE h.window_hours > 0;
