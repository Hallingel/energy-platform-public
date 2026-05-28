# Energy Analytics Platform

A complete end-to-end energy analytics system built with:

- PostgreSQL (hourly data storage)
- Python importers (wind, solar, weather, price)
- Dash dashboard (visual analytics)
- Docker Compose (full stack orchestration)

The platform collects:
- Wind production (kW)
- Solar production (kW)
- Electricity price (€/MWh)
- Weather data (wind speed, temperature)

And visualizes:
- Total production (kW)
- Solar vs wind comparison
- Price vs production correlation
- Price change speed
- Statistical price forecast

---

## 🚀 Running the platform

docker compose up -d --build


Dashboard:  
http://localhost:8050

Database:  
PostgreSQL 15 on port **5432**

---

## 📁 Project structure

energy-platform/
│
├── docker-compose.yml
│
├── db/
│   └── init/
│       └── 01_schema.sql
│
├── importer_price/
│   ├── Dockerfile
│   └── main.py
│
├── importer_weather/
│   ├── Dockerfile
│   └── main.py
│
├── importer_solar/
│   ├── Dockerfile
│   └── main.py
│
├── importer_daily/
│   ├── Dockerfile
│   └── main.py
│
├── dash_app/
│   ├── Dockerfile
│   └── app.py
│
└── README.md


---

## 🧠 Architecture diagram

+----------------------+
|      Dash App        |
|   (Plotly + Dash)    |
+----------+-----------+
|
| reads
v
+-------------------+   +-----------+   +-------------------+
| importer_weather  |   | importer  |   | importer_solar    |
| (Open-Meteo API)  |   | _price    |   | (Solar radiation) |
+---------+---------+   | (Elering) |   +---------+---------+
|             +-----------+             |
| writes           | writes             | writes
v                  v                   v
+--------------------------------------+
|              PostgreSQL              |
| wind, solar, price, weather tables   |
+--------------------------------------+


---

## 🧪 GitHub Actions CI/CD

Fail: `.github/workflows/docker-build.yml`

name: Build and Test

on:
push:
branches: [ "main" ]
pull_request:
branches: [ "main" ]

jobs:
build:
runs-on: ubuntu-latest

steps:
- name: Checkout repository
uses: actions/checkout@v3

name: Set up Docker Buildx
uses: docker/setup-buildx-action@v2

name: Build Docker images
run: |
docker build -t energy-dash ./dash_app
docker build -t energy-price ./importer_price
docker build -t energy-weather ./importer_weather
docker build -t energy-solar ./importer_solar

name: Run basic tests
run: |
echo "Smoke test: checking Python versions"
docker run --rm energy-dash python --version
docker run --rm energy-price python --version


See workflow:

- buildib kõik konteinerid  
- teeb lihtsa smoke‑testi  
- töötab iga push’i korral  

---
