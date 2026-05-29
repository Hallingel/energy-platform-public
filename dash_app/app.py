import os
import pandas as pd
from sqlalchemy import create_engine
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# --- Andmebaasi ühendus ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def safe_load(sql):
    try:
        df = pd.read_sql(sql, engine)
        if "ts" in df.columns:
            df = df.sort_values("ts")
        return df
    except Exception as e:
        print("SQL ERROR:", e)
        return pd.DataFrame()

# --- Dash rakendus ---
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Energia Dashboard – 6 graafikut", style={"textAlign": "center"}),

    dcc.Graph(id="g_weather"),        # 1) Tuule kiirus
    dcc.Graph(id="g_om_solar"),       # 2) Päikese kiirgus
    dcc.Graph(id="g_elering_solar"),  # 3) Elering tootmine
    dcc.Graph(id="g_entsoe_solar"),   # 4) ENTSO-E tootmine
    dcc.Graph(id="g_price"),          # 5) Hind
    dcc.Graph(id="g_all"),            # 6) Koondgraafik

    dcc.Interval(id="interval", interval=60 * 1000, n_intervals=0)
])

@app.callback(
    [
        Output("g_weather", "figure"),
        Output("g_om_solar", "figure"),
        Output("g_elering_solar", "figure"),
        Output("g_entsoe_solar", "figure"),
        Output("g_price", "figure"),
        Output("g_all", "figure"),
    ],
    [Input("interval", "n_intervals")]
)
def update(_):

    # 1) Ilm (tuule kiirus + päikese kiirgus)
    df_weather = safe_load("""
        SELECT ts, wind_speed_ms, shortwave_radiation
        FROM weather_15min
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # 2) Hind
    df_price = safe_load("""
        SELECT ts, price_eur_mwh
        FROM price_hour
        ORDER BY ts DESC
        LIMIT 200;
    """)

    # 3) Elering päikese tootmine
    df_elering = safe_load("""
        SELECT ts, production_mw
        FROM solar_elering_15min
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # 4) ENTSO‑E päikese tootmine
    df_entsoe = safe_load("""
        SELECT ts, production_mw
        FROM entsoe_solar_wind_15min
        WHERE source = 'SOLAR'
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # 5) Open‑Meteo päikese kiirgus
    df_om_solar = df_weather[["ts", "shortwave_radiation"]].dropna()

    # --- Graafikud ---

    fig_weather = px.line(
        df_weather,
        x="ts",
        y="wind_speed_ms",
        title="Open‑Meteo: Tuule kiirus (m/s)"
    )

    fig_om_solar = px.line(
        df_om_solar,
        x="ts",
        y="shortwave_radiation",
        title="Open‑Meteo: Päikese kiirgus (W/m²)"
    )

    fig_elering = px.line(
        df_elering,
        x="ts",
        y="production_mw",
        title="Elering: Päikeseparkide tootlus (MW)"
    )

    fig_entsoe = px.line(
        df_entsoe,
        x="ts",
        y="production_mw",
        title="ENTSO‑E: Päikeseparkide tootlus (MW)"
    )

    fig_price = px.line(
        df_price,
        x="ts",
        y="price_eur_mwh",
        title="Elering: Börsihind (€/MWh)"
    )

    # 6) Koondgraafik
    df_all = (
        df_entsoe.rename(columns={"production_mw": "entsoe_mw"})
        .merge(df_elering.rename(columns={"production_mw": "elering_mw"}), on="ts", how="outer")
        .merge(df_price, on="ts", how="outer")
        .sort_values("ts")
    )

    for col in ["entsoe_mw", "elering_mw", "price_eur_mwh"]:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

    fig_all = px.line(
        df_all,
        x="ts",
        y=["entsoe_mw", "elering_mw", "price_eur_mwh"],
        title="Koondgraafik: ENTSO‑E (SOLAR) + Elering + hind"
    )

    return (
        fig_weather,
        fig_om_solar,
        fig_elering,
        fig_entsoe,
        fig_price,
        fig_all
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)