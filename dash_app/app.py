import os
import pandas as pd
from sqlalchemy import create_engine
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- Teenuse värvikaart ---
SERVICE_COLORS = {
    f"elekter_{i}": px.colors.qualitative.Plotly[i % 10]
    for i in range(1, 21)
}
SERVICE_COLORS["elekter"] = "blue"
SERVICE_COLORS["default"] = "gray"

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

    html.H1("Energia Dashboard – PUBLIC (5 graafikut)", style={"textAlign": "center"}),

    # --- Perioodi filter ---
    html.Div([
        dcc.Dropdown(
            id="period-type",
            options=[
                {"label": "Vaba", "value": "free"},
                {"label": "Päev", "value": "day"},
                {"label": "Kuu", "value": "month"},
                {"label": "Aasta", "value": "year"},
            ],
            value="free",
            clearable=False,
            style={"width": "200px", "display": "inline-block", "marginRight": "10px"}
        ),

        dcc.Input(
            id="period-n",
            type="number",
            value=1,
            min=1,
            step=1,
            style={"width": "80px", "display": "inline-block"}
        ),

        dcc.Store(id="period-range")
    ], style={"marginBottom": "20px"}),

    dcc.Graph(id="g_weather"),          # 1) Tuule kiirus
    dcc.Graph(id="g_elering_solar"),    # 2) Elering tootmine
    dcc.Graph(id="g_price"),            # 3) Börsihind
    dcc.Graph(id="g_consumption"),      # 4) Tarbimine teenuste kaupa
    dcc.Graph(id="g_cons_vs_solar"),    # 5) Tarbimine vs Päike (JOIN)

    dcc.Interval(id="interval", interval=60 * 1000, n_intervals=0)
])

# --- Perioodi arvutamine ---
@app.callback(
    Output("period-range", "data"),
    Input("period-type", "value"),
    Input("period-n", "value")
)
def compute_period(period_type, n):
    now = datetime.utcnow()

    if period_type == "free":
        return {"start": None, "end": None}

    if period_type == "day":
        start = now - timedelta(days=n)
    elif period_type == "month":
        start = now - relativedelta(months=n)
    elif period_type == "year":
        start = now - relativedelta(years=n)
    else:
        start = None

    return {
        "start": start.isoformat(),
        "end": now.isoformat()
    }

# --- Graafikute uuendamine ---
@app.callback(
    [
        Output("g_weather", "figure"),
        Output("g_elering_solar", "figure"),
        Output("g_price", "figure"),
        Output("g_consumption", "figure"),
        Output("g_cons_vs_solar", "figure"),
    ],
    [
        Input("interval", "n_intervals"),
        Input("period-range", "data")
    ]
)
def update(_, period):

    # --- Perioodi SQL helper ---
    def period_sql(base_sql):
        if period and period["start"]:
            return f"""
                {base_sql}
                WHERE ts BETWEEN '{period["start"]}' AND '{period["end"]}'
                ORDER BY ts ASC;
            """
        else:
            return f"""
                {base_sql}
                ORDER BY ts ASC
                LIMIT 2000;
            """

    # 1) Ilm (weather_15min)
    df_weather = safe_load(period_sql("""
        SELECT ts, wind_speed_ms
        FROM weather_15min
    """))

    # 2) Elering päikese tootmine
    df_elering = safe_load(period_sql("""
        SELECT ts, production_mw
        FROM solar_elering_15min
    """))

    # 3) Börsihind
    df_price = safe_load(period_sql("""
        SELECT ts, price_eur_mwh
        FROM price_hour
    """))

    # 4) Tarbimine teenuste kaupa
    df_cons = safe_load(period_sql("""
        SELECT ts, teenus, kwh
        FROM consumption_15min
    """))

    # 5) Tarbimine vs Päike (JOIN)
    df_cons_solar = safe_load(period_sql("""
        SELECT 
            c.ts,
            c.teenus,
            c.kwh,
            e.production_mw
        FROM consumption_15min c
        LEFT JOIN solar_elering_15min e
            ON c.ts = e.ts
    """))

    # --- Graafikud ---
    # 1) Ilm
    if df_weather.empty:
        fig_weather = go.Figure()
        fig_weather.update_layout(title="Tuule kiirus – andmeid pole")
    else:
        fig_weather = px.line(df_weather, x="ts", y="wind_speed_ms", title="Tuule kiirus (m/s)")

    # 2) Elering päike
    if df_elering.empty:
        fig_elering = go.Figure()
        fig_elering.update_layout(title="Elering päikese tootmine – andmeid pole")
    else:
        fig_elering = px.line(df_elering, x="ts", y="production_mw", title="Elering: Päikese tootlus (MW)")

    # 3) Börsihind
    if df_price.empty:
        fig_price = go.Figure()
        fig_price.update_layout(title="Börsihind – andmeid pole")
    else:
        fig_price = px.line(df_price, x="ts", y="price_eur_mwh", title="Börsihind (€/MWh)")

    # 4) Tarbimine teenuste kaupa
    if df_cons.empty:
        fig_cons = go.Figure()
        fig_cons.update_layout(title="Tarbimine – andmeid pole")
    else:
        fig_cons = go.Figure()
        for teenus in df_cons["teenus"].unique():
            df_t = df_cons[df_cons["teenus"] == teenus]
            color = SERVICE_COLORS.get(teenus, SERVICE_COLORS["default"])
            fig_cons.add_trace(go.Scatter(
                x=df_t["ts"],
                y=df_t["kwh"],
                mode="lines",
                name=teenus,
                line=dict(color=color)
            ))
        fig_cons.update_layout(title="Tarbimine teenuste kaupa (kWh)")

    # 5) Tarbimine vs Päike
    if df_cons_solar.empty:
        fig_cons_solar = go.Figure()
        fig_cons_solar.update_layout(title="Tarbimine vs Päike – andmeid pole")
    else:
        fig_cons_solar = go.Figure()

        # Tarbimine
        for teenus in df_cons_solar["teenus"].unique():
            df_t = df_cons_solar[df_cons_solar["teenus"] == teenus]
            color = SERVICE_COLORS.get(teenus, SERVICE_COLORS["default"])
            fig_cons_solar.add_trace(go.Scatter(
                x=df_t["ts"],
                y=df_t["kwh"],
                mode="lines",
                name=f"Tarbimine – {teenus}",
                yaxis="y1",
                line=dict(color=color)
            ))

        # Päike
        fig_cons_solar.add_trace(go.Scatter(
            x=df_cons_solar["ts"],
            y=df_cons_solar["production_mw"],
            mode="lines",
            name="Päikese tootmine (MW)",
            yaxis="y2",
            line=dict(color="orange", dash="dot")
        ))

        fig_cons_solar.update_layout(
            title="Tarbimine vs Päikese tootmine",
            xaxis=dict(title="Aeg"),
            yaxis=dict(title="Tarbimine (kWh)"),
            yaxis2=dict(
                title="Päikese tootmine (MW)",
                overlaying="y",
                side="right"
            )
        )

    return (
        fig_weather,
        fig_elering,
        fig_price,
        fig_cons,
        fig_cons_solar
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)