-- ============================================
--  ENERGY PLATFORM – LÕPLIK INIT.SQL
--  Loob kõik tabelid importeritele ja Dashile
-- ============================================

-- ===========================
-- WEATHER (15 min)
-- ===========================
CREATE TABLE IF NOT EXISTS weather_15min (
    ts timestamptz PRIMARY KEY,
    wind_speed_ms numeric,
    wind_gust_ms numeric,
    wind_direction_deg numeric,
    temperature_c numeric
);

-- ===========================
-- PRICE (1h)
-- ===========================
CREATE TABLE IF NOT EXISTS price_hour (
    ts timestamptz PRIMARY KEY,
    price_eur_mwh numeric
);

-- ===========================
-- ENTSOE SOLAR + WIND (15 min)
-- ===========================
CREATE TABLE IF NOT EXISTS entsoe_solar_wind_15min (
    ts timestamptz NOT NULL,
    source text NOT NULL,
    production_mw numeric,
    PRIMARY KEY (ts, source)
);

-- ===========================
-- SOLAR ELERING (15 min)
-- ===========================
CREATE TABLE IF NOT EXISTS solar_elering_15min (
    ts timestamptz PRIMARY KEY,
    production_mw numeric
);

-- ===========================
-- SOLAR SITE (for solar_eu & solar_radiation)
-- ===========================
CREATE TABLE IF NOT EXISTS solar_site (
    id serial PRIMARY KEY,
    name text,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    is_active boolean DEFAULT TRUE
);

-- ===========================
-- SOLAR EU (direct radiation, 15 min)
-- ===========================
CREATE TABLE IF NOT EXISTS solar_eu_15min (
    solar_site_id integer REFERENCES solar_site(id),
    ts timestamptz NOT NULL,
    direct_wm2 numeric,
    PRIMARY KEY (solar_site_id, ts)
);

-- ===========================
-- SOLAR RADIATION (shortwave, 15 min)
-- ===========================
CREATE TABLE IF NOT EXISTS solar_radiation_15min (
    solar_site_id integer REFERENCES solar_site(id),
    ts timestamptz NOT NULL,
    radiation_wm2 numeric,
    PRIMARY KEY (solar_site_id, ts)
);

-- ============================================
-- DONE
-- ============================================