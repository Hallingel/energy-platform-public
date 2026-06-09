🌞 ENERGY PLATFORM — Päikesejaamade analüütika
Postgres + Python importerid + Dash dashboard

See projekt koondab päikeseenergia tootmise, ilmaandmete ja elektrihinna info ühtsesse analüütikaplatvormi.
Kõik komponendid töötavad Docker Compose’i all ning andmed salvestatakse PostgreSQL andmebaasi.

🚀 Funktsionaalsus
✔ Päikesepaneelide tootlus
Elering (reaalne tootmine 15‑min intervalliga)

ENTSO‑E (päikesepaneelide tootlus 15‑min intervalliga)

✔ Ilmaandmed
Open‑Meteo (tuule kiirus, tuule puhangud, temperatuur)

✔ Elektrihind
Elering Nord Pool hind (€/MWh)

✔ Dash dashboard
Päikesepaneelide tootmise graafikud (Elering + ENTSO‑E)

Börsihinna graafik

Tuule kiiruse graafik

Koondgraafik: päikesepaneelide tootlus + hind

energy-platform/
│
├── dash_app/
│   ├── app.py
│   └── requirements.txt
│
├── importer_weather/
│   ├── main.py
│   └── requirements.txt
│
├── importer_price/
│   ├── main.py
│   └── requirements.txt
│
├── importer_solar_elering/
│   ├── main.py
│   └── requirements.txt
│
├── importer_entsoe/
│   ├── main.py
│   └── requirements.txt
│
├── db/
│   └── init/
│       └── init.sql
│
├── docker-compose.yml
└── .env

🔧 .env fail
Fail peab olema UTF‑8 ilma BOM‑ita.

DATABASE_URL=postgresql://postgres:postgres@energy_db:5432/energy

ENTSOE_SOLAR_WIND_API=https://web-api.tp.entsoe.eu/api?documentType=A75&processType=A16&in_Domain=10Y1001A1001A39I&out_Domain=10Y1001A1001A39I&timeInterval={START}/{END}&securityToken=YOUR_TOKEN

PRICE_API=https://dashboard.elering.ee/api/nps/price?start={START_ISO}&end={END_ISO}&region=ee
SOLAR_ELERING_API=https://dashboard.elering.ee/api/system?start={START_ISO}&end={END_ISO}
WEATHER_API_URL=https://api.open-meteo.com/v1/forecast?latitude=59.3&longitude=24.5&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m&interval=15_minute&timezone=auto

🐳 Käivitamine
1. Ehita ja käivita kogu platvorm
docker compose up -d --build

2. Kontrolli, et kõik konteinerid töötavad
docker ps

3. Ava dashboard
👉 http://localhost:8050

📊 Dashboardi graafikud
✔ Open‑Meteo tuule kiirus
15‑min intervalliga tuule kiirus (m/s)

✔ Open‑Meteo päikese kiirgus
shortwave_radiation (W/m²)

✔ Elering päikese tootmine
Reaalne tootmine (MW)

✔ ENTSO‑E päikese tootmine
Euroopa süsteemiandmed (MW)

✔ Elering börsihind
€/MWh

✔ Koondgraafik
ENTSO‑E päike
Elering päike
Börsihind

🗄 Andmebaasi tabelid
weather_15min
| ts (UTC) | wind_speed_ms | wind_gust_ms | wind_direction_deg | temperature_c |

price_hour
| ts | price_eur_mwh |

solar_elering_15min
| ts | production_mw |

entsoe_solar_wind_15min
| ts | production_mw | source |

Vaated:

entsoe_solar_15min → ainult päike
entsoe_wind_15min → (hetkel ei kasutata)

🔄 Importerite tööloogika
Kõik importerid:

🔄 Importer_CSV tööloogika
csv fail päis peab olema : Periood, Tarbimine, Teenus
järjekord pole oluline, faili nimi pole oluline,
Veerg teenus täita oma elektrimüüja nimega,
Näit. "elering" , kõikidele ridadele.
Tühje ridu olla ei tohi

arvutavad automaatselt eelmise päeva ajavahemiku
pärivad API‑st
salvestavad andmed PostgreSQL‑i
uuendavad olemasolevaid ridu ON CONFLICT abil
töötavad 15‑min või 1‑h resolutsiooniga

🎓 Miks see projekt on kasulik?
Õpetab API‑de kasutamist
Õpetab andmete normaliseerimist (UTC, 15‑min intervall)
Õpetab Docker Compose’i
Õpetab Dash graafikuid
Loob päris analüütikaplatvormi päikeseenergia uurimiseks
