CREATE OR REPLACE VIEW iss_daily_summary AS
SELECT
    date_trunc('day', observed_at)        AS day,
    count(*)                              AS readings,
    round(avg(velocity_kmh)::numeric, 1)  AS avg_velocity_kmh,
    max(altitude_km)                      AS max_altitude_km
FROM raw_iss_positions
GROUP BY 1;
