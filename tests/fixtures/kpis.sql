CREATE TABLE ref_window AS
SELECT TIMESTAMP '2020-01-01 00:00:00' AS window_start,
       TIMESTAMP '2020-01-02 00:00:00' AS window_end, 24 AS window_hours;

CREATE TABLE assumptions_repair AS
SELECT 'assumed_repair_hours' AS parameter, 12 AS value;

CREATE TABLE dim_machine AS
SELECT * FROM (VALUES (1, 'DC-A', 'conveyor', 'model1'), (2, 'DC-A', 'sorter', 'model1'))
AS machines(machine_id, site_id, equipment_type, model);

CREATE TABLE dim_component AS
SELECT * FROM (VALUES ('comp1'), ('comp2')) AS parts(component);

CREATE TABLE fact_failure AS
SELECT machine_id, window_start + hour * INTERVAL 1 HOUR AS datetime, component
FROM (VALUES (1, 2, 'comp1'), (1, 2, 'comp2'), (1, 5, 'comp1')) AS f(machine_id, hour, component)
CROSS JOIN ref_window;

CREATE TABLE fact_maintenance AS
SELECT maintenance_id, machine_id, window_start + hour * INTERVAL 1 HOUR AS datetime, component
FROM (VALUES (1, 1, -1, 'comp2'), (2, 1, 2, 'comp1'), (3, 1, 2, 'comp2'),
             (4, 1, 5, 'comp1'), (5, 2, 7, 'comp1'), (6, 2, 24, 'comp2'))
AS m(maintenance_id, machine_id, hour, component)
CROSS JOIN ref_window;
