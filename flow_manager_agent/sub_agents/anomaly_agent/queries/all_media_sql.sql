-- -- כל המדיה סורסים, לפי שעה, בין 24–26/10/2025

-- WITH hourly_clicks AS (
--   SELECT
--     TIMESTAMP_TRUNC(event_time, HOUR) AS event_hour,
--     media_source,
--     SUM(total_events) AS clicks
--   FROM `practicode-2025.clicks_data_prac.partial_encoded_clicks_part`
--   WHERE DATE(event_time) BETWEEN '2025-10-24' AND '2025-10-26'
--   GROUP BY event_hour, media_source
-- )

-- SELECT
--   event_hour,
--   media_source,
--   clicks
-- FROM hourly_clicks
-- ORDER BY event_hour, media_source;

