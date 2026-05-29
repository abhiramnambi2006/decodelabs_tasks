import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import paho.mqtt.client as mqtt
import json
import time
import os
from datetime import datetime
import queue
import numpy as np

# --- NETWORK CONFIGURATION ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "decodelabs/abhiram/telemetry"
LOG_FILE = "telemetry_history.csv"

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Facility Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SESSION STATE DEFAULTS ──────────────────────────────────────────────────────
# NEW: initialise controls so they persist across reruns
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "live_updates" not in st.session_state:
    st.session_state.live_updates = True
if "max_data_points" not in st.session_state:
    st.session_state.max_data_points = 100
if "clear_requested" not in st.session_state:
    st.session_state.clear_requested = False

# ─── SIDEBAR CONTROLS ───────────────────────────────────────────────────────────
# NEW: all three feature controls live here; nothing below this block is touched
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Controls")
    st.divider()

    # ── Feature 1: Theme selector ─────────────────────────────────────────────
    # Using key= so Streamlit owns the state — avoids theme reset on other widget changes
    st.markdown("**🎨 Display Theme**")
    st.selectbox(
        "Theme",
        options=["Dark", "Light", "Bright / High Contrast"],
        key="theme",
        label_visibility="collapsed",
    )
    st.divider()

    # ── Feature 3: Live Updates toggle ───────────────────────────────────────
    st.markdown("**🔄 Live Updates**")
    st.toggle(
        "Enable auto-refresh",
        key="live_updates",
    )
    if not st.session_state.live_updates:
        st.caption("⏸ Updates paused — graphs are static.")
    st.divider()

    # ── Feature 2a: Max Data Points slider ───────────────────────────────────
    st.markdown("**📊 Max Data Points**")
    st.slider(
        "Max Data Points",
        min_value=10,
        max_value=100,
        step=10,
        key="max_data_points",
        label_visibility="collapsed",
    )
    st.divider()

    # ── Feature 2b: Clear Graph Data button ──────────────────────────────────
    st.markdown("**🗑️ Reset Graph Data**")
    if st.button("Clear Graph Data", use_container_width=True, type="secondary"):
        # Set a flag — actual clearing happens at the top of the main flow,
        # avoiding conflicts with the live-update rerun cycle
        st.session_state.clear_requested = True

# ─── THEME DEFINITIONS ──────────────────────────────────────────────────────────
# NEW: one dict per theme; T is the active palette used throughout the file
THEMES = {
    "Dark": {
        "bg":             "#0D1117",
        "card_bg":        "#161B22",
        "border":         "#21262D",
        "text":           "#E6EDF3",
        "muted":          "#8B949E",
        "accent":         "#58A6FF",
        "grid":           "#21262D",
        "plot_bg":        "#0D1117",
        "hover_bg":       "#161B22",
        "header_bg":      "#21262D",
        "badge_bg":       "#1F6FEB22",
        "badge_border":   "#1F6FEB55",
        "section_border": "#58A6FF44",
    },
    "Light": {
        "bg":             "#F6F8FA",
        "card_bg":        "#FFFFFF",
        "border":         "#D0D7DE",
        "text":           "#1F2328",
        "muted":          "#57606A",
        "accent":         "#0969DA",
        "grid":           "#D0D7DE",
        "plot_bg":        "#FFFFFF",
        "hover_bg":       "#FFFFFF",
        "header_bg":      "#EEF1F4",
        "badge_bg":       "#0969DA22",
        "badge_border":   "#0969DA55",
        "section_border": "#0969DA44",
    },
    "Bright / High Contrast": {
        "bg":             "#0A0A0A",
        "card_bg":        "#141414",
        "border":         "#FFFF00",
        "text":           "#FFFFFF",
        "muted":          "#CCCCCC",
        "accent":         "#FFFF00",
        "grid":           "#2A2A2A",
        "plot_bg":        "#0A0A0A",
        "hover_bg":       "#141414",
        "header_bg":      "#1C1C00",
        "badge_bg":       "#FFFF0022",
        "badge_border":   "#FFFF0088",
        "section_border": "#FFFF0077",
    },
}

T = THEMES[st.session_state.theme]   # active palette shorthand

# ─── DYNAMIC GLOBAL CSS ─────────────────────────────────────────────────────────
# NEW: was a static string; now an f-string so every colour token responds to T
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&display=swap');

/* ── Root ── */
html, body {{
    font-family: 'Roboto', sans-serif;
    background-color: {T['bg']} !important;
    color: {T['text']} !important;
}}

/* ── Main app containers ── */
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main {{
    background-color: {T['bg']} !important;
    color: {T['text']} !important;
    font-family: 'Roboto', sans-serif;
}}

/* ── Force sidebar permanently open and visible ── */
section[data-testid="stSidebar"] {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    transform: none !important;
    min-width: 270px !important;
    max-width: 320px !important;
    background-color: {T['card_bg']} !important;
    border-right: 1px solid {T['border']} !important;
    transition: none !important;
}}
section[data-testid="stSidebar"] > div {{
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}}
/* Hide the collapse button so it can never be accidentally closed */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{
    display: none !important;
}}

/* ── Sidebar inner text & widget colours ── */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span:not([data-baseweb]),
section[data-testid="stSidebar"] .stMarkdown {{
    color: {T['text']} !important;
}}
section[data-testid="stSidebar"] hr {{
    border-color: {T['border']} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background-color: {T['bg']} !important;
    border-color: {T['border']} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] [data-baseweb="select"] span {{
    color: {T['text']} !important;
    background-color: transparent !important;
}}

/* ── Header ── */
.dash-header {{
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid {T['border']};
    margin-bottom: 2rem;
}}
.dash-title {{
    font-family: 'Roboto', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: 0.01em;
    color: {T['accent']};
    text-transform: none;
    margin: 0;
}}
.dash-subtitle {{
    color: {T['muted']};
    font-family: 'Roboto', sans-serif;
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 0.02em;
    text-transform: none;
    margin-top: 0.4rem;
}}
.live-badge {{
    display: inline-block;
    background: {T['badge_bg']};
    border: 1px solid {T['badge_border']};
    color: {T['accent']};
    font-size: 0.78rem;
    font-family: 'Roboto', sans-serif;
    font-weight: 500;
    letter-spacing: 0.04em;
    padding: 3px 12px;
    border-radius: 20px;
    margin-top: 0.6rem;
}}
.live-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    background: #3FB950;
    border-radius: 50%;
    margin-right: 6px;
    animation: blink 1.4s infinite;
}}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}

/* ── KPI Cards ── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 1.5rem;
}}
.kpi-card {{
    background: {T['card_bg']};
    border: 1px solid {T['border']};
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}}
.kpi-card:hover {{ border-color: {T['accent']}55; }}
.kpi-accent {{
    position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 12px 0 0 12px;
}}
.kpi-label {{
    font-family: 'Roboto', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {T['muted']};
    font-weight: 500;
    margin-bottom: 0.5rem;
}}
.kpi-value {{
    font-family: 'Roboto', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.3rem;
}}
.kpi-sub {{
    font-family: 'Roboto', sans-serif;
    font-size: 0.82rem;
    color: {T['muted']};
}}

/* ── Alert Banner ── */
.alert-danger {{
    background: #3D0D0D;
    border: 1px solid #F8514966;
    border-left: 5px solid #F85149;
    border-radius: 10px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.5rem;
}}
.alert-safe {{
    background: #0D2D1A;
    border: 1px solid #3FB95066;
    border-left: 5px solid #3FB950;
    border-radius: 10px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.5rem;
}}
.alert-title {{ font-family: 'Roboto', sans-serif; font-size: 1.05rem; font-weight: 700; margin: 0; }}
.alert-sub   {{ font-size: 0.83rem; margin: 4px 0 0; opacity: 0.75; }}

/* ── Section headers ── */
.section-header {{
    font-family: 'Roboto', sans-serif;
    font-size: 1.05rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 900;
    color: {T['text']};
    border-bottom: 2px solid {T['section_border']};
    padding-bottom: 0.6rem;
    margin-bottom: 1.2rem;
}}

/* ── Summary bar ── */
.summary-bar {{
    background: {T['card_bg']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 0.9rem 1.6rem;
    display: flex;
    justify-content: center;
    gap: 2.5rem;
    margin-top: 1.5rem;
    font-family: 'Roboto', sans-serif;
    font-size: 0.88rem;
    color: {T['muted']};
}}
.summary-bar b {{ color: {T['text']}; font-weight: 700; }}

/* ── Analysis cards (pure HTML, no st widgets inside) ── */
.analysis-card {{
    background: {T['card_bg']};
    border: 1px solid {T['border']};
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
}}
.analysis-card-header {{
    font-family: 'Roboto', sans-serif;
    font-size: 0.88rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T['text']};
    background: {T['header_bg']};
    border-bottom: 1px solid {T['border']};
    padding: 0.85rem 1.3rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.analysis-card-body {{
    padding: 1.1rem 1.3rem;
    font-family: 'Roboto', sans-serif;
    font-size: 0.95rem;
    font-weight: 400;
    line-height: 1.6;
}}
/* Status boxes inside analysis cards */
.status-error {{
    background: #3D0D0D;
    border: 1px solid #F8514966;
    border-left: 4px solid #F85149;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    color: #FF7B72;
    font-size: 0.92rem;
}}
.status-success {{
    background: #0D2D1A;
    border: 1px solid #3FB95066;
    border-left: 4px solid #3FB950;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    color: #56D364;
    font-size: 0.92rem;
}}
.status-warning {{
    background: #2D1F00;
    border: 1px solid #E3B34166;
    border-left: 4px solid #E3B341;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    color: #E3B341;
    font-size: 0.92rem;
}}
.status-info {{
    background: #0D1F2D;
    border: 1px solid #388BFD66;
    border-left: 4px solid #388BFD;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    color: #79C0FF;
    font-size: 0.92rem;
}}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 2rem !important; }}
[data-testid="stMetric"] {{ display: none; }}

/* ── Plotly chart border ── */
.stPlotlyChart {{ border-radius: 10px; overflow: hidden; }}


</style>
""", unsafe_allow_html=True)

# ─── CLEAR DATA (flag set by sidebar button) ────────────────────────────────────
if st.session_state.get("clear_requested", False):
    st.session_state.iot_dataframe = pd.DataFrame(
        columns=["Timestamp", "Temperature", "Humidity", "Light_Level", "Motion"]
    )
    try:
        os.remove(LOG_FILE)
    except FileNotFoundError:
        pass
    st.session_state.clear_requested = False   # reset flag immediately

# ─── DATA STORAGE ───────────────────────────────────────────────────────────────
if "iot_dataframe" not in st.session_state:
    try:
        st.session_state.iot_dataframe = pd.read_csv(LOG_FILE)
    except FileNotFoundError:
        st.session_state.iot_dataframe = pd.DataFrame(
            columns=["Timestamp", "Temperature", "Humidity", "Light_Level", "Motion"]
        )

# ─── MQTT PIPELINE ──────────────────────────────────────────────────────────────
@st.cache_resource
def setup_mqtt_pipeline():
    data_queue = queue.Queue()

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if payload.get("status") == "SUCCESS":
                data_queue.put(payload)
        except Exception as e:
            print(f"Parse Error: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return client, data_queue

mqtt_client, msg_queue = setup_mqtt_pipeline()

# ─── INGEST NEW RECORDS ─────────────────────────────────────────────────────────
# NEW: cap uses the sidebar slider value instead of the hardcoded 100
max_pts = st.session_state.max_data_points
new_records = []
while not msg_queue.empty():
    payload = msg_queue.get()
    new_records.append({
        "Timestamp": datetime.now().strftime("%H:%M:%S"),
        "Temperature": float(payload["temperature"]),
        "Humidity":    float(payload["humidity"]),
        "Light_Level": float(payload["light_level"]),
        "Motion":      int(payload["motion"]),
    })

if new_records:
    df = st.session_state.iot_dataframe
    df = pd.concat([df, pd.DataFrame(new_records)], ignore_index=True)
    if len(df) > max_pts:                  # NEW: was hardcoded 100
        df = df.iloc[-max_pts:]
    st.session_state.iot_dataframe = df
    df.to_csv(LOG_FILE, index=False)

# ─── HEADER ─────────────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%d %b %Y  ·  %H:%M:%S")
st.markdown(f"""
<div class="dash-header">
    <div class="dash-title">⬡ Smart Facility Monitor</div>
    <div class="dash-subtitle">Industrial IoT Analytics &amp; Security Automation</div>
    <div class="live-badge"><span class="live-dot"></span>LIVE STREAM &nbsp;·&nbsp; {now_str}</div>
</div>
""", unsafe_allow_html=True)

df = st.session_state.iot_dataframe

# ─── WAITING STATE ──────────────────────────────────────────────────────────────
if df.empty:
    st.markdown("""
    <div style='text-align:center; padding: 4rem 0; color:#8B949E;'>
        <div style='font-size:3rem; margin-bottom:1rem;'>📡</div>
        <div style='font-size:1rem; color:#58A6FF; font-weight:700;'>AWAITING PIPELINE SYNC</div>
        <div style='font-size:0.85rem; margin-top:0.5rem;'>
            Launch your Wokwi simulation node to begin streaming live telemetry packets.
        </div>
    </div>
    """, unsafe_allow_html=True)
    # NEW: only rerun if live updates are enabled
    if st.session_state.live_updates:
        time.sleep(2)
        st.rerun()

else:
    latest     = df.iloc[-1]
    avg_temp   = df["Temperature"].mean()
    avg_hum    = df["Humidity"].mean()
    avg_light  = df["Light_Level"].mean()
    motion_cnt = int(df["Motion"].sum())

    # ── Shared chart layout ────────────────────────────────────────────────────
    # NEW: plot_bgcolor, gridcolor, font colour, and hoverlabel colours now use T
    CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=T['plot_bg'],
        font=dict(family="Roboto, sans-serif", color=T['muted'], size=12),
        margin=dict(l=10, r=10, t=55, b=20),
        height=360,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickmode='auto',
            nticks=6,
            tickfont=dict(size=11, color=T['muted']),
            title=dict(text="Reading No.", font=dict(size=11)),
        ),
        yaxis=dict(
            gridcolor=T['grid'],
            zeroline=False,
            tickfont=dict(size=11, color=T['muted']),
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=T['hover_bg'], bordercolor=T['border'], font_family="Roboto, sans-serif"),
    )

    x_idx = list(range(1, len(df) + 1))

    def sparse_text(series):
        vals = list(series)
        n = len(vals)
        # Dynamically scale label density so max ~10 labels show at once
        if n <= 10:
            every = 1        # ≤10 readings  → show every reading
        elif n <= 25:
            every = 2        # ≤25 readings  → every 2nd
        elif n <= 50:
            every = 5        # ≤50 readings  → every 5th
        elif n <= 80:
            every = 8        # ≤80 readings  → every 8th
        else:
            every = 10       # >80 readings  → every 10th
        texts = []
        for i, v in enumerate(vals):
            # Always show the label if it falls on the interval OR is the last point
            if i % every == 0 or i == n - 1:
                texts.append(f"{v:.2f}")
            else:
                texts.append("")
        return texts

    def add_latest_annotation(fig, x_vals, y_vals, color):
        if len(x_vals) > 0:
            fig.add_annotation(
                x=x_vals[-1], y=y_vals.iloc[-1],
                text=f"{y_vals.iloc[-1]:.1f}",
                showarrow=True, arrowhead=2, arrowsize=1,
                arrowwidth=2, arrowcolor=color,
                ax=0, ay=-30,
                bgcolor=T['card_bg'], bordercolor=color, borderwidth=1,   # NEW: uses T
                font=dict(color=color, size=10, family="Roboto, sans-serif")
            )

    # ── SECURITY ALERT ────────────────────────────────────────────────────────
    if latest["Motion"] == 1:
        st.markdown("""
        <div class="alert-danger">
            <div class="alert-title" style="color:#F85149;">🚨 BREACH DETECTED — ACTIVE MOTION IN SECTOR</div>
            <div class="alert-sub" style="color:#F85149;">Immediate review of optical sensors recommended. Security protocol engaged.</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-safe">
            <div class="alert-title" style="color:#3FB950;">✅ SECTOR CLEAR — NO MOTION DETECTED</div>
            <div class="alert-sub" style="color:#3FB950;">All systems nominal. Continuous monitoring active.</div>
        </div>""", unsafe_allow_html=True)

    # ── KPI CARDS ─────────────────────────────────────────────────────────────
    def delta_arrow(series):
        if len(series) < 2:
            return ""
        d = series.iloc[-1] - series.iloc[-2]
        return f"{'▲' if d > 0 else '▼'} {abs(d):.2f}" if d != 0 else "— Stable"

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-accent" style="background:#EF4444;"></div>
            <div class="kpi-label">🌡️ Temperature</div>
            <div class="kpi-value" style="color:#EF4444;">{latest['Temperature']:.1f}<span style="font-size:1rem;"> °C</span></div>
            <div class="kpi-sub">{delta_arrow(df['Temperature'])}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-accent" style="background:#3B82F6;"></div>
            <div class="kpi-label">💧 Humidity</div>
            <div class="kpi-value" style="color:#3B82F6;">{latest['Humidity']:.1f}<span style="font-size:1rem;"> %</span></div>
            <div class="kpi-sub">{delta_arrow(df['Humidity'])}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-accent" style="background:#F59E0B;"></div>
            <div class="kpi-label">☀️ Light Level</div>
            <div class="kpi-value" style="color:#F59E0B;">{latest['Light_Level']:.1f}<span style="font-size:1rem;"> lux</span></div>
            <div class="kpi-sub">{delta_arrow(df['Light_Level'])}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-accent" style="background:{'#F85149' if latest['Motion']==1 else '#3FB950'};"></div>
            <div class="kpi-label">🚨 Motion Events</div>
            <div class="kpi-value" style="color:{'#F85149' if latest['Motion']==1 else '#3FB950'};">{motion_cnt}</div>
            <div class="kpi-sub">{'ACTIVE NOW' if latest['Motion']==1 else 'No recent activity'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CHARTS ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📈 Telemetry History</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    # — Temperature —
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_idx, y=df["Temperature"],
            fill="tozeroy", fillcolor="rgba(239,68,68,0.1)",
            line=dict(color="#EF4444", width=3),
            mode="lines+markers+text",
            marker=dict(symbol="circle", size=9, color="#EF4444",
                        line=dict(color=T['bg'], width=1.5)),       # NEW: marker outline uses T
            text=sparse_text(df["Temperature"]),
            textposition="top center",
            textfont=dict(size=12, color="#EF4444", family="Roboto, sans-serif"),
            name="Temp (°C)",
            hovertemplate="<b>%{y:.2f} °C</b><extra></extra>",
        ))
        add_latest_annotation(fig, x_idx, df["Temperature"], "#EF4444")
        fig.update_layout(**CHART_LAYOUT,
            title=dict(text="<b>Temperature</b>  (°C)",
                       font=dict(size=15, color=T['text'], family="Roboto, sans-serif"), x=0.02))
        st.plotly_chart(fig, use_container_width=True)

    # — Humidity —
    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_idx, y=df["Humidity"],
            fill="tozeroy", fillcolor="rgba(59,130,246,0.1)",
            line=dict(color="#3B82F6", width=3),
            mode="lines+markers+text",
            marker=dict(symbol="square", size=9, color="#3B82F6",
                        line=dict(color=T['bg'], width=1.5)),       # NEW: marker outline uses T
            text=sparse_text(df["Humidity"]),
            textposition="top center",
            textfont=dict(size=12, color="#3B82F6", family="Roboto, sans-serif"),
            name="Humidity (%)",
            hovertemplate="<b>%{y:.2f} %%</b><extra></extra>",
        ))
        add_latest_annotation(fig, x_idx, df["Humidity"], "#3B82F6")
        fig.update_layout(**CHART_LAYOUT,
            title=dict(text="<b>Humidity</b>  (%)",
                       font=dict(size=15, color=T['text'], family="Roboto, sans-serif"), x=0.02))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    # — Light Intensity —
    with c3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_idx, y=df["Light_Level"],
            fill="tozeroy", fillcolor="rgba(245,158,11,0.1)",
            line=dict(color="#F59E0B", width=3),
            mode="lines+markers+text",
            marker=dict(symbol="triangle-up", size=10, color="#F59E0B",
                        line=dict(color=T['bg'], width=1.5)),       # NEW: marker outline uses T
            text=sparse_text(df["Light_Level"]),
            textposition="top center",
            textfont=dict(size=12, color="#F59E0B", family="Roboto, sans-serif"),
            name="Light (lux)",
            hovertemplate="<b>%{y:.2f} lux</b><extra></extra>",
        ))
        add_latest_annotation(fig, x_idx, df["Light_Level"], "#F59E0B")
        fig.update_layout(**CHART_LAYOUT,
            title=dict(text="<b>Light Intensity</b>  (lux)",
                       font=dict(size=15, color=T['text'], family="Roboto, sans-serif"), x=0.02))
        st.plotly_chart(fig, use_container_width=True)

    # — Motion Detection —
    with c4:
        # NEW: inactive bars use T['border'] so they're visible on all themes
        colors = ["#F85149" if m == 1 else T['border'] for m in df["Motion"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_idx, y=df["Motion"],
            marker_color=colors,
            marker_line=dict(color=T['bg'], width=1),              # NEW: uses T
            text=["YES" if m == 1 else "NO" for m in df["Motion"]],
            textposition="outside",
            textfont=dict(size=12, color=["#F85149" if m == 1 else T['muted'] for m in df["Motion"]],
                          family="Roboto, sans-serif"),
            name="Motion",
            hovertemplate="<b>Reading %{x}</b>: %{customdata}<extra></extra>",
            customdata=["DETECTED" if m == 1 else "CLEAR" for m in df["Motion"]],
        ))
        fig.update_layout(**CHART_LAYOUT,
            title=dict(text="<b>Motion Detection</b>  (0/1)",
                       font=dict(size=15, color=T['text'], family="Roboto, sans-serif"), x=0.02),
            bargap=0.3,
        )
        fig.update_yaxes(
            tickvals=[0, 1],
            ticktext=["No Motion", "Detected"],
            gridcolor=T['grid'],                                    # NEW: uses T
            range=[-0.15, 1.75],
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── SUMMARY BAR ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="summary-bar">
        <div>Avg Temp &nbsp;<b>{avg_temp:.1f} °C</b></div>
        <div style="color:{T['border']};">|</div>
        <div>Avg Humidity &nbsp;<b>{avg_hum:.1f} %</b></div>
        <div style="color:{T['border']};">|</div>
        <div>Avg Light &nbsp;<b>{avg_light:.1f} lux</b></div>
        <div style="color:{T['border']};">|</div>
        <div>Motion Events &nbsp;<b>{motion_cnt}</b></div>
        <div style="color:{T['border']};">|</div>
        <div>Readings &nbsp;<b>{len(df)}</b></div>
    </div>
    """, unsafe_allow_html=True)

    # ── AUTOMATED ANALYTICS  (pure HTML — no st widgets, no ghost boxes) ──────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🧠 Automated Intelligence</div>', unsafe_allow_html=True)

    # Build environment card content
    if 20.0 <= avg_temp <= 26.0 and 30.0 <= avg_hum <= 60.0:
        env_html = f"""
        <div class="status-success">
            ✅ &nbsp;<strong>Optimal Stability</strong> —
            Mean Temp: {avg_temp:.1f} °C &nbsp;·&nbsp; Mean Humidity: {avg_hum:.1f} %
        </div>"""
    else:
        env_html = f"""
        <div class="status-error">
            ⚠️ &nbsp;<strong>Atmospheric Warning</strong> —
            Mean Temp: {avg_temp:.1f} °C &nbsp;·&nbsp; Mean Humidity: {avg_hum:.1f} %
            <br><span style="font-size:0.85rem; opacity:0.85;">Values deviate from safe thresholds (20–26 °C, 30–60 %).</span>
        </div>"""

    # Build energy card content
    if avg_light > 60.0 and motion_cnt == 0:
        energy_html = f"""
        <div class="status-warning">
            💡 &nbsp;<strong>Energy Inefficiency Detected</strong> —
            High luminosity ({avg_light:.1f} lux) with zero occupancy.
            <br><span style="font-size:0.85rem; opacity:0.85;">Recommend shutting down lighting systems.</span>
        </div>"""
    elif avg_light < 20.0 and motion_cnt > 0:
        energy_html = f"""
        <div class="status-info">
            👤 &nbsp;<strong>Occupancy in Low-Light</strong> —
            {motion_cnt} motion event(s) at {avg_light:.1f} lux.
            <br><span style="font-size:0.85rem; opacity:0.85;">Activate safety lighting immediately.</span>
        </div>"""
    else:
        energy_html = """
        <div class="status-success">
            ✅ &nbsp;<strong>Energy Profile Stable</strong> —
            Lighting levels match current occupancy conditions.
        </div>"""

    ac1, ac2 = st.columns(2)

    with ac1:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="analysis-card-header">🌿 Environmental Health Matrix</div>
            <div class="analysis-card-body">{env_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with ac2:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="analysis-card-header">⚡ Operational Energy Audit</div>
            <div class="analysis-card-body">{energy_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── AUTO-REFRESH ──────────────────────────────────────────────────────────
    # NEW: was unconditional; now gated on the live_updates toggle
    if st.session_state.live_updates:
        time.sleep(2)
        st.rerun()
