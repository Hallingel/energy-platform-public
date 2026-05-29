import os
import requests
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
WEATHER_API_URL = os.getenv("WEATHER_API_URL")


def ensure_columns():
    """Lisab shortwave_radiation veeru, kui seda pole."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        ALTER TABLE weather_15min
        ADD COLUMN IF NOT EXISTS shortwave_radiation DOUBLE PRECISION;
    """)

    conn.commit()
    cur.close()
    conn.close()


def fetch_weather():
    """Laeb Open-Meteo API andmed."""
    r = requests.get(WEATHER_API_URL, timeout=10)
    if r.status_code != 200:
        print("WEATHER API ERROR:", r.text)
        return None
    return r.json()


def parse_weather(data):
    """Parsib Open-Meteo JSON-i."""
    if data is None:
        return []

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    wind = hourly.get("wind_speed_10m", [])
    radiation = hourly.get("shortwave_radiation", [])

    rows = []
    for i in range(len(times)):
        ts = datetime.fromisoformat(times[i])
        ws = wind[i] if i < len(wind) else None
        rad = radiation[i] if i < len(radiation) else None
        rows.append((ts, ws, rad))

    return rows


def insert_rows(rows):
    """Salvestab andmed PostgreSQL-i."""
    if not rows:
        print("No weather rows to insert")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    for r in rows:
        cur.execute("""
            INSERT INTO weather_15min (ts, wind_speed_ms, shortwave_radiation)
            VALUES (%s, %s, %s)
            ON CONFLICT (ts) DO UPDATE
            SET wind_speed_ms = EXCLUDED.wind_speed_ms,
                shortwave_radiation = EXCLUDED.shortwave_radiation;
        """, r)

    conn.commit()
    cur.close()
    conn.close()
    print("Inserted weather rows:", len(rows))


def main():
    ensure_columns()
    data = fetch_weather()
    rows = parse_weather(data)
    insert_rows(rows)


if __name__ == "__main__":
    main()