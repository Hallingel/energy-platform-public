Write-Host "=== ENERGY PLATFORM STRUCTURE CHECK ===" -ForegroundColor Cyan

# ------------------------------------------------------------
# 1) Failistruktuuri kontroll
# ------------------------------------------------------------

$paths = @(
    ".env",
    "docker-compose.yml",

    "dash_app/app.py",
    "dash_app/requirements.txt",
    "dash_app/Dockerfile",

    "importer_csv/main.py",
    "importer_csv/requirements.txt",
    "importer_csv/Dockerfile",

    "importer_weather/main.py",
    "importer_weather/requirements.txt",
    "importer_weather/Dockerfile",

    "importer_price/main.py",
    "importer_price/requirements.txt",
    "importer_price/Dockerfile",

    "importer_solar_elering/main.py",
    "importer_solar_elering/requirements.txt",
    "importer_solar_elering/Dockerfile",

    "importer_solar_radiation/main.py",
    "importer_solar_radiation/requirements.txt",
    "importer_solar_radiation/Dockerfile",

    "scheduler/scheduler.py",
    "scheduler/Dockerfile",

    "db/init/00_init.sql",
    "db/init/01_merge.sql",
    "db/init/02_cleanup.sql",
    "db/init/03_views.sql"
)

Write-Host "`n=== FILE STRUCTURE ===" -ForegroundColor Cyan

foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "[OK]       $p" -ForegroundColor Green
    } else {
        Write-Host "[MISSING]  $p" -ForegroundColor Red
    }
}

# ------------------------------------------------------------
# 2) .env PostgreSQL võtmete kontroll
# ------------------------------------------------------------

Write-Host "`n=== .ENV CHECK ===" -ForegroundColor Cyan

if (-Not (Test-Path ".env")) {
    Write-Host "[FAIL] .env puudub" -ForegroundColor Red
} else {
    $envContent = Get-Content ".env"

    $requiredEnv = @(
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DATABASE_URL"
    )

    foreach ($e in $requiredEnv) {
        if ($envContent -match $e) {
            Write-Host "[OK] .env sisaldab $e" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] .env EI sisalda $e" -ForegroundColor Red
        }
    }
}

# ------------------------------------------------------------
# 3) PostgreSQL konteineri kontroll
# ------------------------------------------------------------

Write-Host "`n=== POSTGRESQL CONTAINER CHECK ===" -ForegroundColor Cyan

$psqlRunning = docker ps --format "{{.Names}}" | Select-String "energy_db" -Quiet

if ($psqlRunning) {
    Write-Host "[OK] PostgreSQL konteiner töötab (energy_db)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] PostgreSQL konteiner EI tööta" -ForegroundColor Red
}

# ------------------------------------------------------------
# 4) Tabelite ja vaadete kontroll (AKTIIVNE SKEEM)
# ------------------------------------------------------------

Write-Host "`n=== TABLE + VIEW CHECK ===" -ForegroundColor Cyan

$tables = @(
    # RAW
    "raw_consumption",
    "raw_price",
    "raw_weather",
    "raw_solar_elering",
    "raw_solar_radiation",

    # CLEAN
    "consumption_15min",
    "price_hour",
    "weather_hour",
    "solar_elering_15min",
    "solar_radiation_15min"
)

foreach ($t in $tables) {
    $result = docker exec energy_db psql -U postgres -d energy -t -c "SELECT to_regclass('$t');" 2>$null
    if ($result -match $t) {
        Write-Host "[OK] Table exists: $t" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing table: $t" -ForegroundColor Red
    }
}

$views = @(
    "v_consumption_day",
    "v_consumption_month",
    "v_consumption_year",
    "v_price_day",
    "v_weather_day",
    "v_solar_elering_day",
    "v_solar_radiation_day",
    "v_consumption_price",
    "v_consumption_solar",
    "v_consumption_weather",
    "v_energy_full"
)

foreach ($v in $views) {
    $result = docker exec energy_db psql -U postgres -d energy -t -c "SELECT to_regclass('$v');" 2>$null
    if ($result -match $v) {
        Write-Host "[OK] View exists: $v" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing view: $v" -ForegroundColor Red
    }
}

# ------------------------------------------------------------
# 5) Importerite DB ühenduse test
# ------------------------------------------------------------

Write-Host "`n=== IMPORTER DB CONNECTION TEST ===" -ForegroundColor Cyan

$importers = @(
    "importer_csv",
    "importer_weather",
    "importer_price",
    "importer_solar_elering",
    "importer_solar_radiation"
)

foreach ($imp in $importers) {
    Write-Host "Testing $imp ..." -ForegroundColor Yellow

    $test = docker exec $imp python - << 'EOF'
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.close()
    print("OK")
except:
    print("FAIL")
EOF

    if ($test -match "OK") {
        Write-Host "[OK] $imp saab DB-ga ühenduse" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $imp EI saa DB-ga ühendust" -ForegroundColor Red
    }
}

Write-Host "`n=== CHECK COMPLETE ===" -ForegroundColor Cyan