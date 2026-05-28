import os, time, requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

API = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=shortwave_radiation&timezone=auto"


def conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_sites(c):
    with c.cursor() as cur:
        cur.execute("SELECT id, latitude, longitude FROM solar_site WHERE is_active=TRUE;")
        return cur.fetchall()


def fetch(lat, lon):
    url = API.format(lat=lat, lon=lon)
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    j = r.json()
    return list(zip(j["hourly"]["time"], j["hourly"]["shortwave_radiation"]))


def insert(c, site_id, rows):
    with c.cursor() as cur:
        for ts, val in rows:
            cur.execute("""
                INSERT INTO solar_radiation_15min (solar_site_id, ts, radiation_wm2)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (site_id, ts, val))
    c.commit()


def main():
    while True:
        try:
            c = conn()
            for s in get_sites(c):
                rows = fetch(s["latitude"], s["longitude"])
                insert(c, s["id"], rows)
                print("solar_radiation:", s["id"], "rows:", len(rows))
            c.close()
        except Exception as e:
            print("solar_radiation ERROR:", e)
        time.sleep(3600)


if __name__ == "__main__":
    main()
