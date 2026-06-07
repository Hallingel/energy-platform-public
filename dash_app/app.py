import os
import pandas as pd
from sqlalchemy import create_engine
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

# --- Teenuse värvikaart ---
SERVICE_COLORS = {
    "elekter": "blue",
    "elering": "green",
    "gaas": "red",
    "vesi": "purple",
    "default": "gray"
}

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
    html.H1("Energia Dashboard – 5 graafikut", style={"textAlign": "center"}),

    dcc.Graph(id="g_weather"),          # 1) Tuule kiirus
    dcc.Graph(id="g_om_solar"),         # 2) Päikese kiirgus
    dcc.Graph(id="g_elering_solar"),    # 3) Elering tootmine
    dcc.Graph(id="g_price"),            # 4) Hind
    dcc.Graph(id="g_csv_solar"),        # 5) Tarbimine CSV -> Päikese kiirgus

    dcc.Interval(id="interval", interval=60 * 1000, n_intervals=0)
])

@app.callback(
    [
        Output("g_weather", "figure"),
        Output("g_om_solar", "figure"),
        Output("g_elering_solar", "figure"),
        Output("g_price", "figure"),
        Output("g_csv_solar", "figure"),
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

    # 4) CSV tarbimine + päikese kiirgus JOIN
    df_csv_solar = safe_load("""
        SELECT 
            c.ts,
            c.teenus,
            c.kwh,
            w.shortwave_radiation
        FROM consumption_15min c
        LEFT JOIN weather_15min w
            ON c.ts = w.ts
        ORDER BY c.ts ASC
        LIMIT 2000;
    """)

    # --- Graafikud ---

    fig_weather = px.line(
        df_weather,
        x="ts",
        y="wind_speed_ms",
        title="Open‑Meteo: Tuule kiirus (m/s)"
    )

    fig_om_solar = px.line(
        df_weather,
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

    fig_price = px.line(
        df_price,
        x="ts",
        y="price_eur_mwh",
        title="Elering: Börsihind (€/MWh)"
    )

    # 5) Tarbimine (iga teenus oma värviga) + päikese kiirgus teisel teljel
    if df_csv_solar.empty:
        fig_csv_solar = go.Figure()
        fig_csv_solar.update_layout(
            title="Tarbimine (CSV) vs Päikese kiirgus (W/m²) – andmeid pole"
        )
    else:
        fig_csv_solar = go.Figure()

        # Iga teenus oma värviga
        for teenus in df_csv_solar["teenus"].dropna().unique():
            df_t = df_csv_solar[df_csv_solar["teenus"] == teenus]

            color = SERVICE_COLORS.get(teenus, SERVICE_COLORS["default"])

            fig_csv_solar.add_trace(
                go.Scatter(
                    x=df_t["ts"],
                    y=df_t["kwh"],
                    mode="lines",
                    name=f"Tarbimine – {teenus}",
                    yaxis="y1",
                    line=dict(color=color)
                )
            )

        # Päikese kiirgus teisel teljel
        if "shortwave_radiation" in df_csv_solar.columns:
            fig_csv_solar.add_trace(
                go.Scatter(
                    x=df_csv_solar["ts"],
                    y=df_csv_solar["shortwave_radiation"],
                    mode="lines",
                    name="Päikese kiirgus (W/m²)",
                    yaxis="y2",
                    line=dict(color="orange", dash="dot")
                )
            )

        fig_csv_solar.update_layout(
            title="Tarbimine (CSV) ja Päikese kiirgus (W/m²)",
            xaxis=dict(title="Aeg"),
            yaxis=dict(title="Tarbimine (kWh)"),
            yaxis2=dict(
                title="Päikese kiirgus (W/m²)",
                overlaying="y",
                side="right"
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )

    return (
        fig_weather,
        fig_om_solar,
        fig_elering,
        fig_price,
        fig_csv_solar
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)