import os
import requests
import psycopg2
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

DB_URL = os.getenv("DATABASE_URL")
ENTSOE_URL_TEMPLATE = os.getenv("ENTSOE_SOLAR_WIND_API")

NS = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}

PSR_MAP = {
    "B01": "WIND",
    "B03": "SOLAR"
}

def build_time_interval():
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    start = yesterday.strftime("%Y-%m-%dT00:00Z")
    end = today.strftime("%Y-%m-%dT00:00Z")

    return start, end

def fetch_entsoe_xml(url):
    print(f"ENTSO-E päring: {url}")
    r = requests.get(url)
    print("HTTP status:", r.status_code)
    if r.status_code != 200:
        print(r.text)
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
            continue  # ignore non-solar/wind

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

    print("Leitud ridu:", len(rows))
    return rows

def insert_rows(rows):
    if not rows:
        print("Pole ridu, mida sisestada.")
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

    print("Kirjutasin ENTSO-E ridu:", len(rows))

def main():
    start, end = build_time_interval()
    url = ENTSOE_URL_TEMPLATE.format(START=start, END=end)

    xml_text = fetch_entsoe_xml(url)
    rows = parse_entsoe(xml_text)
    insert_rows(rows)

if __name__ == "__main__":
    main()