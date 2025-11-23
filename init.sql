-- init.sql
-- Runs automatically on the first Postgres startup.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================
-- Drone measurements table
-- =========================
CREATE TABLE IF NOT EXISTS drone_measurements (
  id                         BIGSERIAL PRIMARY KEY,
  drone_time_utc             TIMESTAMPTZ NOT NULL,  -- from Drone_Time(UTC+RFC3339)
  drone_time_pst             TIMESTAMPTZ,           -- Drone_Time(PST) localized to America/Vancouver, stored as UTC
  update_time_local_raw      TEXT,                  -- raw "CUSTOM.updateTime [local]" (e.g., 11:24:29.64 AM)

  -- store directions EXACTLY as in CSV
  wind_direction             TEXT,                  -- from WEATHER.windDirection (verbatim)
  wind_relative_direction    TEXT,                  -- from WEATHER.windRelativeDirection (verbatim)

  wind_speed_mph             NUMERIC,
  max_wind_speed_mph         NUMERIC,
  wind_strength              TEXT,                  -- e.g., Calm / Light / Moderate...
  is_facing_wind             TEXT,                  -- store raw CSV string (e.g., "True"/"False")
  is_flying_into_wind        TEXT,                  -- store raw CSV string (e.g., "True"/"False")
  drone_direction_deg        NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_drone_measurements_time ON drone_measurements (drone_time_utc);

-- =============================
-- Anemometer measurements table
-- =============================
CREATE TABLE IF NOT EXISTS anemometer_measurements (
  id            BIGSERIAL PRIMARY KEY,
  ts_utc        TIMESTAMPTZ NOT NULL,  -- from ts
  raw_ts        TEXT,                  -- raw clock-like stamp "23:11:01:17:39:22.316"
  u             NUMERIC,
  v             NUMERIC,
  temperature_c NUMERIC,               -- from T
  battery_pct   NUMERIC,
  batt_v        NUMERIC,
  batt_c        NUMERIC,
  vector_mag    NUMERIC,
  vector_dir_deg NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_anemo_time ON anemometer_measurements (ts_utc);
