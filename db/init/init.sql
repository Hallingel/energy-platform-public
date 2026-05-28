-- ============================================
--  ENERGY PLATFORM DATABASE SCHEMA (FINAL, FIXED)
-- ============================================

-- ---------- SOLAR SITES ----------
CREATE TABLE IF NOT EXISTS solar_site (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO solar_site (name, latitude, longitude, is_active)
VALUES ('Default Solar Park', 58.9, 25.0, TRUE)
ON CONFLICT DO NOTHING;


-- ============================================
-- WEATHER (Open-Meteo)
-- importer_weather/main.py expects:
-- ts, wind_speed_ms, wind_gust_ms, wind_direction_deg, temperature_c
-- ============================================
CREATE TABLE IF NOT EXISTS weather_15min (
    ts TIMESTAMPTZ PRIMARY KEY,
    wind_speed_ms DOUBLE PRECISION,
    wind_gust_ms DOUBLE PRECISION,
    wind_direction_deg DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION
);


-- ============================================
-- SOLAR RADIATION (shortwave_radiation)
-- importer_solar_radiation/main.py expects:
-- solar_site_id, ts, radiation_wm2
-- ============================================
CREATE TABLE IF NOT EXISTS solar_radiation_15min (
    solar_site_id INTEGER REFERENCES solar_site(id),
    ts TIMESTAMPTZ,
    radiation_wm2 DOUBLE PRECISION,
    PRIMARY KEY (solar_site_id, ts)
);


-- ============================================
-- SOLAR EU (direct_radiation)
-- importer_solar_eu/main.py expects:
-- solar_site_id, ts, direct_wm2
-- ============================================
CREATE TABLE IF NOT EXISTS solar_eu_15min (
    solar_site_id INTEGER REFERENCES solar_site(id),
    ts TIMESTAMPTZ,
    direct_wm2 DOUBLE PRECISION,
    PRIMARY KEY (solar_site_id, ts)
);


-- ============================================
-- SOLAR ELERING (MW)
-- importer_solar_elering/main.py expects:
-- ts, production_mw
-- ============================================
CREATE TABLE IF NOT EXISTS solar_elering_15min (
    ts TIMESTAMPTZ PRIMARY KEY,
    production_mw DOUBLE PRECISION
);


-- ============================================
-- PRICE (€/MWh)
-- importer_price/main.py expects:
-- ts, price_eur_mwh
-- ============================================
CREATE TABLE IF NOT EXISTS price_hour (
    ts TIMESTAMPTZ PRIMARY KEY,
    price_eur_mwh DOUBLE PRECISION
);


-- ============================================
-- DAILY SUMMARY (optional)
-- ============================================
CREATE TABLE IF NOT EXISTS daily_summary (
    day DATE PRIMARY KEY,
    solar_elering_mwh DOUBLE PRECISION,
    solar_radiation_avg DOUBLE PRECISION,
    solar_direct_avg DOUBLE PRECISION,
    avg_price_eur_mwh DOUBLE PRECISION
);


-- ============================================
-- ENTSO-E SOLAR + WIND FORECAST (15-min)
-- importer_entsoe/main.py expects:
-- ts, production_mw, source
-- ============================================
CREATE TABLE IF NOT EXISTS entsoe_solar_wind_15min (
    ts TIMESTAMPTZ NOT NULL,
    production_mw DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,  -- SOLAR / WIND
    PRIMARY KEY (ts, source)
);

-- Views for convenience
CREATE OR REPLACE VIEW entsoe_solar_15min AS
SELECT ts, production_mw
FROM entsoe_solar_wind_15min
WHERE source = 'SOLAR';

CREATE OR REPLACE VIEW entsoe_wind_15min AS
SELECT ts, production_mw
FROM entsoe_solar_wind_15min
WHERE source = 'WIND';
