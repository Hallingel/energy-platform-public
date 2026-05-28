import os
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

API = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&hourly=direct_radiation"
    "&timezone=auto"
)


def db_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_active_sites(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, latitude, longitude
            FROM solar_site
            WHERE is_active = TRUE;
        """)
        return cur.fetchall()


def fetch_direct_radiation(lat, lon):
    url = API.format(lat=lat, lon=lon)
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    j = r.json()

    times = j["hourly"]["time"]
    vals = j["hourly"]["direct_radiation"]

    rows = []
    for ts, val in zip(times, vals):
        # Tagame korrektse timestamptz formaadi
        ts = ts.replace("Z", "+00:00")
        rows.append((ts, val))

    return rows


def insert_rows(conn, site_id, rows):
    with conn.cursor() as cur:
        for ts, val in rows:
            cur.execute("""
                INSERT INTO solar_eu_15min (solar_site_id, ts, direct_wm2)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (site_id, ts, val))
    conn.commit()


def main():
    while True:
        try:
            conn = db_conn()
            sites = get_active_sites(conn)

            for site in sites:
                rows = fetch_direct_radiation(site["latitude"], site["longitude"])
                insert_rows(conn, site["id"], rows)
                print(f"solar_eu: site={site['id']} rows={len(rows)}")

            conn.close()

        except Exception as e:
            print("solar_eu ERROR:", e)

        time.sleep(3600)  # 1h intervall


if __name__ == "__main__":
    main()
