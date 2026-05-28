import os
import requests
import psycopg2
from datetime import datetime, timezone

DB_URL = os.getenv("DATABASE_URL")
WEATHER_API_URL = os.getenv("WEATHER_API_URL")

def fetch_weather():
    print("Pärin Open‑Meteo API...")
    r = requests.get(WEATHER_API_URL)
    print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text)
        return None

    return r.json()

def parse_weather(data):
    if data is None:
        return []

    hourly = data["hourly"]

    timestamps = hourly["time"]
    wind_speed = hourly["wind_speed_10m"]
    wind_gust = hourly["wind_gusts_10m"]
    wind_dir = hourly["wind_direction_10m"]
    temp = hourly["temperature_2m"]

    rows = []

    for i in range(len(timestamps)):
        # Open‑Meteo annab Eesti aja → teisendame UTC‑ks
        ts_local = datetime.fromisoformat(timestamps[i])
        ts_utc = ts_local.astimezone(timezone.utc)

        rows.append((
            ts_utc,
            wind_speed[i],
            wind_gust[i],
            wind_dir[i],
            temp[i]
        ))

    print("Leitud ridu:", len(rows))
    return rows

def insert_rows(rows):
    if not rows:
        print("Pole ridu.")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    for r in rows:
        cur.execute("""
            INSERT INTO weather_15min (ts, wind_speed_ms, wind_gust_ms, wind_direction_deg, temperature_c)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ts) DO UPDATE
            SET wind_speed_ms = EXCLUDED.wind_speed_ms,
                wind_gust_ms = EXCLUDED.wind_gust_ms,
                wind_direction_deg = EXCLUDED.wind_direction_deg,
                temperature_c = EXCLUDED.temperature_c;
        """, r)

    conn.commit()
    cur.close()
    conn.close()

    print("Kirjutasin ridu:", len(rows))

def main():
    data = fetch_weather()
    rows = parse_weather(data)
    insert_rows(rows)

if __name__ == "__main__":
    main()