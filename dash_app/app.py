import os
import pandas as pd
from sqlalchemy import create_engine

from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# --- Andmebaasi ühendus ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def load_df(sql):
    df = pd.read_sql(sql, engine)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.floor("15min")
    return df


# --- Dash rakendus ---
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Energia Dashboard – Päikesejaamad", style={"textAlign": "center"}),

    dcc.Graph(id="graph_weather"),
    dcc.Graph(id="graph_el_price"),
    dcc.Graph(id="graph_el_solar"),
    dcc.Graph(id="graph_entsoe_solar"),
    dcc.Graph(id="graph_solar_all"),

    dcc.Interval(id="interval", interval=60 * 1000, n_intervals=0)
])


@app.callback(
    [
        Output("graph_weather", "figure"),
        Output("graph_el_price", "figure"),
        Output("graph_el_solar", "figure"),
        Output("graph_entsoe_solar", "figure"),
        Output("graph_solar_all", "figure"),
    ],
    [Input("interval", "n_intervals")]
)
def update_graphs(_):

    # --- Open‑Meteo ---
    df_weather = load_df("""
        SELECT ts, wind_speed_ms
        FROM weather_15min
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # --- Elering hind ---
    df_price = load_df("""
        SELECT ts, price_eur_mwh
        FROM price_hour
        ORDER BY ts DESC
        LIMIT 200;
    """)

    # --- Elering päikese tootmine ---
    df_se = load_df("""
        SELECT ts, production_mw
        FROM solar_elering_15min
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # --- ENTSO‑E päikese tootmine ---
    df_entsoe = load_df("""
        SELECT ts, production_mw
        FROM entsoe_solar_15min
        ORDER BY ts DESC
        LIMIT 500;
    """)

    # --- 1) Ilm ---
    fig_weather = px.line(
        df_weather,
        x="ts",
        y="wind_speed_ms",
        title="Open‑Meteo: Tuule kiirus (m/s)"
    )

    # --- 2) Hind ---
    fig_el_price = px.line(
        df_price,
        x="ts",
        y="price_eur_mwh",
        title="Elering: Börsihind (€/MWh)"
    )

    # --- 3) Elering päikese tootmine ---
    fig_el_solar = px.line(
        df_se,
        x="ts",
        y="production_mw",
        title="Elering: Päikesejaamade tootmine (MW)"
    )

    # --- 4) ENTSO‑E päikese tootmine ---
    fig_entsoe_solar = px.line(
        df_entsoe,
        x="ts",
        y="production_mw",
        title="ENTSO‑E: Päikesejaamade tootmine (MW)"
    )

    # --- 5) Koondgraafik ---
    df_solar_all = (
        df_entsoe.rename(columns={"production_mw": "entsoe_mw"})
        .merge(df_se.rename(columns={"production_mw": "elering_mw"}), on="ts", how="outer")
        .merge(df_price, on="ts", how="outer")
        .sort_values("ts")
    )

    fig_solar_all = px.line(
        df_solar_all,
        x="ts",
        y=["entsoe_mw", "elering_mw", "price_eur_mwh"],
        title="Päikeseparkide koondgraafik (ENTSO‑E, Elering, hind)"
    )

    return (
        fig_weather,
        fig_el_price,
        fig_el_solar,
        fig_entsoe_solar,
        fig_solar_all
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)