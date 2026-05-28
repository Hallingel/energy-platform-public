import os, time, requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

API = "https://dashboard.elering.ee/api/nps/price?start={start}&end={end}&region=ee"


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
    data = r.json()["data"]["ee"]

    rows = []
    for row in data:
        ts = datetime.utcfromtimestamp(row["timestamp"])
        rows.append((ts, row["price"]))

    return rows


def insert(c, rows):
    with c.cursor() as cur:
        for ts, price in rows:
            cur.execute("""
                INSERT INTO price_hour (ts, price_eur_mwh)
                VALUES (%s, %s)
                ON CONFLICT (ts) DO UPDATE SET
                    price_eur_mwh = EXCLUDED.price_eur_mwh;
            """, (ts, price))
    c.commit()


def main():
    while True:
        try:
            c = conn()
            rows = fetch()
            insert(c, rows)
            print("price rows:", len(rows))
            c.close()
        except Exception as e:
            print("price ERROR:", e)
        time.sleep(3600)


if __name__ == "__main__":
    main()
