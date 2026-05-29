import os, requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

API = "https://dashboard.elering.ee/api/system?start={start}&end={end}"


def conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def fetch():
    end = datetime.utcnow()
    start = end - timedelta(days=2)

    url = API.format(
        start=start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end=end.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()["data"]

    rows = []
    for row in data:
        if row["solar_energy_production"] is None:
            continue
        ts = datetime.utcfromtimestamp(row["timestamp"])
        rows.append((ts, row["solar_energy_production"]))

    return rows


def insert(c, rows):
    with c.cursor() as cur:
        for ts, prod in rows:
            cur.execute("""
                INSERT INTO solar_elering_15min (ts, production_mw)
                VALUES (%s, %s)
                ON CONFLICT (ts) DO UPDATE SET
                    production_mw = EXCLUDED.production_mw;
            """, (ts, prod))
    c.commit()


def main():
    try:
        c = conn()
        rows = fetch()
        insert(c, rows)
        print("solar_elering rows:", len(rows))
        c.close()
    except Exception as e:
        print("solar_elering ERROR:", e)


if __name__ == "__main__":
    main()