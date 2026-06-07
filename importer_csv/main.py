import os
import csv
import shutil
import psycopg2
from datetime import datetime
import hashlib

DATA_DIR = "/data"

DATE_CANDIDATES = ["periood", "kuup", "date", "timestamp", "aeg"]
CONSUMPTION_CANDIDATES = ["tarb", "kogus", "kwh", "energia", "consum"]
SERVICE_CANDIDATES = ["teenus", "service", "liik", "type"]

DB = {
    "host": os.getenv("DB_HOST", "energy_db"),
    "dbname": os.getenv("DB_NAME", "energy"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

def detect_column(header, candidates):
    header_lower = [h.lower().strip() for h in header]
    for c in candidates:
        for i, h in enumerate(header_lower):
            if c in h:
                return i
    return None

def parse_date(value):
    value = value.strip()
    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H.%M",
        "%d.%m.%Y %H-%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d.%m.%y %H:%M",
        "%d.%m.%y",
    ]
    for f in formats:
        try:
            return datetime.strptime(value, f)
        except:
            pass
    return None

def make_uniqkey(ts, service, kwh):
    raw = f"{ts.isoformat()}|{service}|{kwh}"
    return hashlib.md5(raw.encode()).hexdigest()

def connect_db():
    return psycopg2.connect(
        host=DB["host"],
        dbname=DB["dbname"],
        user=DB["user"],
        password=DB["password"]
    )

def process_csv_file(path):
    print(f"[INFO] Processing file: {os.path.basename(path)}")

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        print("[ERROR] Empty CSV")
        return

    header = rows[0]
    data = rows[1:]

    date_idx = detect_column(header, DATE_CANDIDATES)
    cons_idx = detect_column(header, CONSUMPTION_CANDIDATES)
    serv_idx = detect_column(header, SERVICE_CANDIDATES)

    if date_idx is None or cons_idx is None:
        print("[ERROR] Could not detect required columns")
        print(header)
        return

    if serv_idx is None:
        serv_idx = -1

    conn = connect_db()
    cur = conn.cursor()

    for row in data:
        if len(row) <= max(date_idx, cons_idx, serv_idx if serv_idx != -1 else 0):
            continue

        ts = parse_date(row[date_idx])
        if not ts:
            continue

        try:
            kwh = float(row[cons_idx].replace(",", "."))
        except:
            continue

        service = row[serv_idx] if serv_idx != -1 else "elekter"
        uniqkey = make_uniqkey(ts, service, kwh)

        cur.execute("""
            INSERT INTO raw_consumption (ts, kwh, teenus, uniqkey, source_file)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (uniqkey) DO NOTHING;
        """, (ts, kwh, service, uniqkey, os.path.basename(path)))

    conn.commit()
    cur.close()
    conn.close()

    print("[OK] Import complete")

def update_consumption_15min():
    print("[INFO] Updating consumption_15min...")

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO consumption_15min (ts, teenus, kwh)
        SELECT 
            date_trunc('minute', ts) AS ts,
            teenus,
            SUM(kwh) AS kwh
        FROM raw_consumption
        GROUP BY 1, 2
        ORDER BY 1
        ON CONFLICT (ts, teenus) DO UPDATE SET kwh = EXCLUDED.kwh;
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("[OK] consumption_15min updated")

def move_to_processed(path):
    processed_dir = os.path.join(DATA_DIR, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    dest = os.path.join(processed_dir, os.path.basename(path))
    shutil.move(path, dest)
    print(f"[OK] Moved to processed: {dest}")

def main():
    print("[INFO] CSV importer started")

    for file in os.listdir(DATA_DIR):
        if file.lower().endswith(".csv"):
            full_path = os.path.join(DATA_DIR, file)
            process_csv_file(full_path)
            move_to_processed(full_path)

    update_consumption_15min()

if __name__ == "__main__":
    main()