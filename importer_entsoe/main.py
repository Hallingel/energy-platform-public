import os
import time
import requests
import psycopg2
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
ENTSOE_URL_TEMPLATE = os.getenv("ENTSOE_SOLAR_WIND_API")

NS = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}

PSR_MAP = {
    "B01": "WIND",
    "B03": "SOLAR"
}

def wait_for_db():
    while True:
        try:
            conn = psycopg2.connect(DB_URL)
            conn.close()
            print("DB READY")
            return
        except Exception as e:
            print("DB not ready, retrying…", str(e))
            time.sleep(2)

def build_time_interval():
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    start = yesterday.strftime("%Y-%m-%dT00:00Z")
    end = today.strftime("%Y-%m-%dT00:00Z")
    return start, end

def fetch_entsoe_xml(url):
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print("ENTSOE ERROR:", r.text)
        return None
    return r.text

def parse_entsoe(xml_text):
    if xml_text is None:
        return []

    root = ET.fromstring(xml_text)
    rows = []

    for ts in root.findall("ns:TimeSeries", NS):
        psr = ts.find("ns:MktPSRType/ns:psrType", NS)
        if psr is None:
            continue

        psr_code = psr.text
        if psr_code not in PSR_MAP:
            continue

        source = PSR_MAP[psr_code]

        period = ts.find("ns:Period", NS)
        if period is None:
            continue

        start = period.find("ns:timeInterval/ns:start", NS).text
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))

        for point in period.findall("ns:Point", NS):
            pos = int(point.find("ns:position", NS).text)
            qty = float(point.find("ns:quantity", NS).text)
            ts_point = start_dt + timedelta(minutes=15 * (pos - 1))
            rows.append((ts_point, qty, source))

    return rows

def insert_rows(rows):
    if not rows:
        print("No rows to insert")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    for r in rows:
        cur.execute("""
            INSERT INTO entsoe_solar_wind_15min (ts, production_mw, source)
            VALUES (%s, %s, %s)
            ON CONFLICT (ts, source) DO UPDATE
            SET production_mw = EXCLUDED.production_mw;
        """, r)

    conn.commit()
    cur.close()
    conn.close()
    print("Inserted rows:", len(rows))

def main():
    wait_for_db()

    start, end = build_time_interval()
    url = ENTSOE_URL_TEMPLATE.format(START=start, END=end)

    xml_text = fetch_entsoe_xml(url)
    rows = parse_entsoe(xml_text)

    print("Fetched rows:", len(rows))
    insert_rows(rows)

if __name__ == "__main__":
    main()