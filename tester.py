import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from transformers import pipeline
from geopy.geocoders import Nominatim
import requests
from html2image import Html2Image
import tempfile
import os
#import qrcode
from io import BytesIO
from streamlit_option_menu import option_menu
import torch

st.set_page_config(
    page_title="CO₂ Saver - Green Receipt",
    layout="wide"
)

# -------------------------
# BEAUTIFUL UI SETUP
# -------------------------
# 🔥 Custom CSS for sidebar
st.markdown("""
<style>
/* ========== GLOBAL UI ENHANCEMENTS ========== */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
    font-size: 16px;
    color: #e4e4e4;
    background-color: #121212;
}

/* ========== SIDEBAR ========== */
[data-testid="stSidebar"] {
    background-color: #1a1a2e;
    border-right: 1px solid #292942;
}
[data-testid="stSidebar"] * {
    color: #ffffff;
}

/* ========== BUTTONS ========== */
button[kind="primary"] {
    background-color: #7B3FE4;
    color: white;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: bold;
    transition: all 0.2s ease-in-out;
}
button[kind="primary"]:hover {
    background-color: #9f5cf1;
    transform: scale(1.03);
}

/* ========== HEADINGS ========== */
h1, h2, h3 {
    color: #ffffff;
    font-weight: 700;
    margin-top: 0.5em;
    margin-bottom: 0.3em;
}

/* ========== INPUTS ========== */
input, textarea {
    border-radius: 8px !important;
    background-color: #222 !important;
    color: #eee !important;
    border: 1px solid #555 !important;
    padding: 8px !important;
}

/* ========== CHART CONTAINERS ========== */
.element-container:has(.stPlotlyChart), .element-container:has(.stImage) {
    padding: 10px;
    border-radius: 15px;
    background-color: #1e1e2f;
    box-shadow: 0 0 12px rgba(0,0,0,0.5);
    margin-bottom: 1rem;
}

/* ========== FLOATING CHAT BUTTON ========== */
.chat-button {
    transition: all 0.3s ease;
}
.chat-button:hover {
    background-color: #9f5cf1 !important;
    transform: scale(1.08);
    box-shadow: 0 0 15px #9f5cf1;
}

/* ========== BADGE CARDS / RECEIPT ========== */
.badge-card, .receipt-box {
    border-radius: 12px;
    padding: 15px;
    background: linear-gradient(to right, #20202a, #181822);
    box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    margin-bottom: 1rem;
    transition: all 0.3s ease-in-out;
}
.badge-card:hover, .receipt-box:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.5);
}

/* ========== TOOLTIP / SMALL TEXT ========== */
.tooltip {
    font-size: 13px;
    color: #aaaaaa;
}

/* ========== SMOOTH ELEMENT FADE ========== */
.element-container {
    transition: all 0.3s ease-in-out;
}
</style>
""", unsafe_allow_html=True)



ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImFlZjcxNWEyZDFiMDQ3NDlhMjI0ZTNmMDJjYWRjODA1IiwiaCI6Im11cm11cjY0In0="

# ---------- Practicality rules & helpers ----------
PRACTICAL_LIMITS_KM = {
    "Walk": 2.0,
    "Cycle": 10.0,        # tweak if you want
    # Add more if needed, e.g. "CNG Auto": None
}

def is_practical(mode: str, distance_km: float) -> bool:
    lim = PRACTICAL_LIMITS_KM.get(mode)
    return True if lim is None else distance_km <= lim

def score_to_stars(percent_improvement: float) -> float:
    # Map 0%→1★, 100%→5★ (clamped)
    stars = 1.0 + 4.0 * (max(0.0, min(100.0, percent_improvement)) / 100.0)
    return round(stars, 2)

# -------------------------
# RECEIPT GENERATION
# -------------------------



def _pick_baseline_mode(current_mode: str, factors: dict) -> str:
    # Prefer an obvious baseline if present
    for k in ["Car", "Petrol Car", "Gasoline Car", "Diesel Car"]:
        if k in factors: return k
    # Otherwise, pick the dirtiest for contrast
    return max(factors.items(), key=lambda kv: kv[1])[0]

def generate_premium_receipt(
    user_name: str,
    route_text: str,             # e.g., "Mumbai → Pune"
    mode: str,                   # current mode used
    distance_km: float,
    co2_emitted: float,
    co2_saved: float,
    percent_improvement: float,  # 0–100
    best_mode: str | None,
    trees_saved_days: float,
    share_url: str | None = None,  # for QR; can be your app URL or trip URL
    canvas_size: tuple[int, int] = (1240, 1754),  # ~A4 @ ~150 DPI
):
    """
    Renders a premium HTML eco-receipt in Streamlit and returns a PNG bytes
    that matches exactly (WYSIWYG) using html2image.
    """
    # Defensive checks
    if best_mode and not is_practical(best_mode, float(distance_km)):
        best_mode = None

    stars_value = score_to_stars(percent_improvement)
    full_stars = int(stars_value)
    empty_stars = 5 - full_stars
    stars_str = "★" * full_stars + "☆" * empty_stars

    factors = get_emission_factors()
    baseline_mode = _pick_baseline_mode(mode, factors)
    baseline_emission = factors.get(baseline_mode, max(factors.values()) if factors else 0) * float(distance_km)
    actual_emission = float(co2_emitted)
    saved_vs_baseline = max(0.0, baseline_emission - actual_emission)

    # Progress bar width (clamp 0–100)
    prog = max(0.0, min(100.0, percent_improvement))

    # Nice impact statement variants
    # Rough, friendly equivalences
    bulbs_day = max(1, int(round(actual_emission / 0.06)))   # ~60W bulb per day ~0.06 kg CO2 (approx)
    showers = max(1, int(round(co2_saved / 0.5)))            # ~0.5 kg CO2 saved ~ one short shower avoided (very rough)
    impact_line = f"This trip saved about {showers} hot showers worth of energy."

    # QR code (data URI)
    #qr_uri = _qr_data_uri(share_url or "https://co2-saver.streamlit.app/")

    # Subtle bg pattern (SVG as data URI)
    bg_svg = """
    <svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'>
      <g fill='none' stroke='#e8f5ee' stroke-width='1'>
        <path d='M0 20h40M20 0v40'/>
      </g>
    </svg>
    """.strip()
    bg_b64 = base64.b64encode(bg_svg.encode("utf-8")).decode("utf-8")
    bg_uri = f"data:image/svg+xml;base64,{bg_b64}"

    # HTML
    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        :root {{
          --brand:#17a673; --brand-dark:#118a60; --ink:#2c3e50; --muted:#51606d;
          --card:#ffffff; --line:#dfeee3; --chip:#f6fff9; --warn:#f1c40f;
          --bg:#f9fdfb;
        }}
        * {{ box-sizing:border-box; -webkit-font-smoothing:antialiased; }}
        body {{
          margin:0; padding:24px; background: var(--bg) url("{bg_uri}");
          font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          color: var(--ink);
        }}
        .paper {{
          max-width: 900px; margin: 0 auto; background: var(--card);
          border:1px solid var(--line); border-radius: 20px;
          box-shadow: 0 12px 32px rgba(0,0,0,0.06);
          overflow: hidden;
        }}
        .header {{
          display:flex; align-items:center; justify-content:space-between;
          padding: 28px 30px; background: linear-gradient(180deg, #f4fffa, #ffffff);
          border-bottom:1px solid var(--line);
        }}
        .brand {{
          display:flex; align-items:center; gap:12px;
        }}
        .brand-badge {{
          background: var(--brand); color:#fff; font-weight:800; font-size:20px;
          padding:10px 14px; border-radius: 14px;
        }}
        .sub {{
          font-size:14px; color: var(--muted);
        }}
        .route {{
          font-size:16px; font-weight:700; color: var(--brand-dark);
        }}
        .section {{ padding: 24px 30px; }}

        /* Score row */
        .score-row {{ display:flex; flex-wrap:wrap; gap:16px; align-items:center; }}
        .stars {{ font-size:28px; color: var(--warn); letter-spacing:2px; }}
        .score-val {{ font-weight:800; font-size:26px; }}

        /* Chips */
        .chips {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:14px; }}
        .chip {{
          border:1px solid var(--line); background: var(--chip); color: var(--ink);
          padding:10px 14px; border-radius:14px; font-weight:600; display:flex; gap:10px; align-items:center;
        }}
        .chip small {{ opacity:.7; }}

        /* Progress */
        .progress-wrap {{ margin-top:18px; }}
        .progress-label {{ font-size:13px; color: var(--muted); margin-bottom:6px; }}
        .progress {{
          width:100%; height:14px; background:#eef8f3; border-radius:999px; overflow:hidden; border:1px solid var(--line);
        }}
        .progress > div {{
          width:{prog}%; height:100%; background: linear-gradient(90deg, var(--brand), #28c08c);
        }}

        /* Compare panel */
        .compare {{
          margin-top:22px; border:1px solid var(--line); border-radius:16px; overflow:hidden;
        }}
        .compare-head {{
          background:#f3fcf7; padding:12px 16px; font-weight:800; color: var(--brand-dark);
          border-bottom:1px solid var(--line);
        }}
        .compare-grid {{
          display:grid; grid-template-columns: 1fr 1fr 1fr; gap:0; text-align:center;
        }}
        .cell {{
          padding:16px; border-right:1px solid var(--line);
        }}
        .cell:last-child {{ border-right:none; }}
        .cell .big {{ font-weight:800; font-size:20px; }}
        .cell .small {{ font-size:13px; color: var(--muted); }}

        /* Two-column body */
        .cols {{ display:grid; grid-template-columns: 1.4fr 1fr; gap:20px; margin-top:22px; }}
        .panel {{ border:1px solid var(--line); border-radius:16px; padding:16px; background:#fff; }}
        .panel h3 {{ margin:0 0 10px; font-size:18px; color:var(--brand-dark) }}

        /* Tips */
        .tips ul {{ margin:8px 0 0 18px; padding:0; }}
        .tips li {{ margin:6px 0; }}

        /* Footer */
        .footer {{
          display:flex; align-items:center; justify-content:space-between;
          padding: 16px 30px; border-top:1px solid var(--line); background:#fbfffd;
        }}
        .cta {{
          background: var(--brand); color:#fff; padding:10px 14px; font-weight:800;
          border-radius:12px; display:inline-block;
        }}
        .muted {{ color:var(--muted); font-size:12px; }}
        .qr {{ width:94px; height:94px; border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
        .qr img {{ width:100%; height:100%; display:block; }}
      </style>
    </head>
    <body>
      <div class="paper">

        <div class="header">
          <div class="brand">
            <div class="brand-badge">CO₂ Saver</div>
            <div>
              <div class="route">{route_text}</div>
              <div class="sub">Generated for {user_name} • {datetime.now().strftime('%d %b %Y, %I:%M %p')}</div>
            </div>
          </div>
          <div class="score">
            <div class="stars">{stars_str}</div>
            <div class="score-val">{percent_improvement:.0f}% greener</div>
          </div>
        </div>

        <div class="section">
          <div class="chips">
            <div class="chip">💨 <small>CO₂ emitted</small> {co2_emitted:.2f} kg</div>
            <div class="chip">💚 <small>CO₂ saved</small> {co2_saved:.2f} kg</div>
            <div class="chip">🌳 <small>Trees eq.</small> {trees_saved_days:.1f} days</div>
            <div class="chip">🚘 <small>Mode</small> {mode} • {distance_km:g} km</div>
            {"<div class='chip'>✨ <small>Try next time</small> "+best_mode+"</div>" if best_mode else ""}
          </div>

          <div class="progress-wrap">
            <div class="progress-label">Progress to a carbon‑neutral trip</div>
            <div class="progress"><div></div></div>
          </div>

          <div class="compare">
            <div class="compare-head">What if you had taken {baseline_mode} instead?</div>
            <div class="compare-grid">
              <div class="cell">
                <div class="small">Baseline ({baseline_mode})</div>
                <div class="big">{baseline_emission:.2f} kg</div>
              </div>
              <div class="cell">
                <div class="small">Your choice</div>
                <div class="big">{actual_emission:.2f} kg</div>
              </div>
              <div class="cell">
                <div class="small">You saved</div>
                <div class="big">−{saved_vs_baseline:.2f} kg</div>
              </div>
            </div>
          </div>

          <div class="cols">
            <div class="panel">
              <h3>Impact statement</h3>
              <div>{impact_line}</div>
              <div class="muted" style="margin-top:8px">Star score: {stars_str} ({stars_value:.2f})</div>
            </div>
            <div class="panel tips">
              <h3>💡 Suggestions</h3>
              <ul>
                <li>For trips under 10 km, try cycling or public transport.</li>
                <li>Group errands to reduce cold starts and idling.</li>
                <li>Choose off‑peak hours to avoid congestion.</li>
                <li>If available, consider EVs for daily commutes.</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="footer">
          <div class="muted">Receipt ID: {datetime.now().strftime('%Y%m%d%H%M%S')} • Share this report</div>
          <div class="qr"><img src="{qr_uri}" alt="QR"></div>
          <div class="cta">Make it carbon neutral</div>
        </div>
      </div>
    </body>
    </html>
    """

    # Show in Streamlit exactly as it will download
    st.markdown(html, unsafe_allow_html=True)

    # HTML → PNG (exact WYSIWYG)
    from html2image import Html2Image
    hti = Html2Image(output_path=tempfile.gettempdir())
    temp_html = os.path.join(tempfile.gettempdir(), "eco_receipt.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    out_name = "eco_receipt.png"
    hti.screenshot(html_file=temp_html, save_as=out_name, size=canvas_size)
    with open(os.path.join(tempfile.gettempdir(), out_name), "rb") as f:
        return f.read()

def generate_receipt_image(user_name, mode, distance, co2_emitted, co2_saved,
                           percent_improvement, best_mode, trees_saved):
    """
    Generates a full-page styled HTML receipt with tips, converts to PNG for download.
    """
    stars_value = score_to_stars(percent_improvement)
    full_stars = int(stars_value)
    empty_stars = 5 - full_stars
    stars_str = "★" * full_stars + "☆" * empty_stars

    if best_mode and not is_practical(best_mode, float(distance)):
        best_mode = None

    # Extra suggestions to fill space
    tips_html = """
    <div class="tips">
      <h3>💡 Suggestions for a Greener Future</h3>
      <ul>
        <li>Carpool with friends or colleagues to cut emissions.</li>
        <li>Choose public transport for medium-long distances.</li>
        <li>Walk or cycle for short trips whenever possible.</li>
        <li>Switch to electric or hybrid vehicles for daily commutes.</li>
        <li>Plan routes to avoid traffic jams and save fuel.</li>
      </ul>
    </div>
    """

    html_receipt = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ background: white; font-family: Arial, sans-serif; padding: 30px; }}
        .green-card{{background:#fff;border:1px solid #dfeee3;border-radius:18px;
        padding:30px; max-width:1100px; margin:auto; font-family:Arial,sans-serif;}}
        .brand{{color:#1c9e6b;font-weight:800;font-size:36px;letter-spacing:0.2px;}}
        .headline{{color:#2c3e50;font-weight:700;font-size:28px;margin-top:12px;}}
        .score-row{{display:flex;align-items:center;gap:12px;margin-top:12px}}
        .stars{{font-size:32px; color:#f1c40f; letter-spacing:2px}}
        .score-val{{font-size:28px;color:#2c3e50;font-weight:700}}
        .chips{{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap}}
        .chip{{border:1px solid #cbead5;border-radius:14px;padding:12px 16px;
        background:#f6fff9;color:#2c3e50;font-weight:600; font-size:18px;}}
        .chip small{{opacity:0.75}}
        .hint{{margin-top:14px;color:#1f6f54;font-weight:600; font-size:18px}}
        .cta{{margin-top:20px;background:#17a673;color:#fff;text-align:center;
        padding:14px;border-radius:14px;font-weight:700; font-size:20px}}
        .tips{{margin-top:40px; background:#f9fdfb; border:1px solid #dfeee3; padding:20px; border-radius:12px}}
        .tips h3{{margin-top:0; color:#1c9e6b;}}
        .tips ul{{padding-left:20px; font-size:16px; color:#2c3e50}}
    </style>
    </head>
    <body>
      <div class="green-card">
        <div class="brand">CO₂ Saver</div>
        <div class="headline">Your trip score</div>
        <div class="score-row">
          <div class="stars">{stars_str}</div>
          <div class="score-val">{stars_value:.2f}</div>
        </div>
        <div class="chips">
          <div class="chip">💨 <small>CO₂ emitted</small> {co2_emitted:.2f} kg</div>
          <div class="chip">💚 <small>CO₂ saved</small> {co2_saved:.2f} kg</div>
          <div class="chip">🌳 <small>Trees eq.</small> {trees_saved:.1f} days</div>
          <div class="chip">🚘 <small>Mode</small> {mode} • {distance:g} km</div>
        </div>
        {"<div class='hint'>✨ Try next time: <b>"+best_mode+"</b></div>" if best_mode else ""}
        <div class="cta">Make it carbon neutral</div>
        {tips_html}
      </div>
    </body>
    </html>
    """

    # Show HTML in Streamlit
    st.markdown(html_receipt, unsafe_allow_html=True)

    # Convert to PNG with bigger size
    from html2image import Html2Image
    import tempfile, os

    hti = Html2Image(output_path=tempfile.gettempdir())
    temp_html = os.path.join(tempfile.gettempdir(), "receipt.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_receipt)

    output_png = os.path.join(tempfile.gettempdir(), "receipt.png")
    hti.screenshot(html_file=temp_html, save_as="receipt.png", size=(1280, 900))  # Larger canvas

    with open(output_png, "rb") as f:
        img_bytes = f.read()

    return img_bytes



# -------------------------
# COST SAVINGS DASHBOARD
# -------------------------
def cost_dashboard():
    st.subheader("💰 Cost Savings Dashboard")
    fuel_price = 105  # Rs/litre petrol
    km_per_litre = 15
    petrol_cost_per_km = fuel_price / km_per_litre
    
    trips = get_all_trips()
    if trips.empty:
        st.info("Log some trips to see your cost savings!")
        return

    # Cost assumptions
    cost_factors = {
        "Petrol Car": petrol_cost_per_km,
        "Diesel Car": 100/18,   # Example
        "CNG Auto": 3,          # ₹/km
        "Bus": 0.5,             # ₹/km
        "Metro": 1,             # ₹/km
        "EV Car": 1.5,          # ₹/km
        "Cycle": 0,
        "Walk": 0
    }

    trips["baseline_cost"] = trips["distance"] * petrol_cost_per_km
    trips["actual_cost"] = trips.apply(lambda row: row["distance"]*cost_factors.get(row["mode"],0), axis=1)
    trips["money_saved"] = trips["baseline_cost"] - trips["actual_cost"]

    st.metric("💵 Total ₹ Saved vs Petrol Car", f"₹{trips['money_saved'].sum():.0f}")

    # Group by mode
    savings_by_mode = trips.groupby("mode")[["baseline_cost","actual_cost","money_saved"]].sum().reset_index()

    fig = go.Figure(data=[
        go.Bar(name="Baseline Petrol Car", x=savings_by_mode["mode"], y=savings_by_mode["baseline_cost"]),
        go.Bar(name="Actual Cost", x=savings_by_mode["mode"], y=savings_by_mode["actual_cost"]),
        go.Bar(name="Money Saved", x=savings_by_mode["mode"], y=savings_by_mode["money_saved"])
    ])
    fig.update_layout(barmode='group', title="Cost Comparison by Transport Mode")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# MAP FEATURE
# -------------------------
def geocode_place(place_name):
    geolocator = Nominatim(user_agent="green_map_app")
    location = geolocator.geocode(place_name)
    if location:
        return (location.latitude, location.longitude)
    return None

def get_route_coords(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    params = {
        "start": f"{start_coords[1]},{start_coords[0]}",
        "end": f"{end_coords[1]},{end_coords[0]}"
    }
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        data = r.json()
        coords = [(lat, lon) for lon, lat in data["features"][0]["geometry"]["coordinates"]]
        return coords
    else:
        st.error(f"Route API Error: {r.status_code} - {r.text}")
        return []

def green_map():
    st.subheader("🗺️ Green Path Finder")
    start_place = st.text_input("Start Location", "Mumbai")
    end_place = st.text_input("Destination", "Pune")

    if st.button("Show Green Route"):
        start_coords = geocode_place(start_place)
        end_coords = geocode_place(end_place)

        if not start_coords or not end_coords:
            st.error("Could not find one or both locations.")
            return

        route_coords = get_route_coords(start_coords, end_coords)
        m = folium.Map(location=start_coords, zoom_start=7)
        folium.Marker(start_coords, tooltip=f"Start: {start_place}").add_to(m)
        folium.Marker(end_coords, tooltip=f"End: {end_place}").add_to(m)

        if route_coords:
            folium.PolyLine(route_coords, color="green", weight=5).add_to(m)

        # Store map in session_state so it persists
        st.session_state.green_map = m

    # Show stored map if available
    if "green_map" in st.session_state:
        st_folium(st.session_state.green_map, width=700, height=500)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('co2_saver.db')
    c = conn.cursor()
    
    # Create trips table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS trips
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_name TEXT,
                  date TEXT,
                  mode TEXT,
                  distance REAL,
                  occupancy INTEGER,
                  emission_factor REAL,
                  co2_emitted REAL,
                  baseline_co2 REAL,
                  co2_saved REAL,
                  percent_improvement REAL,
                  suggested_mode TEXT,
                  trees_saved REAL)''')
    
    # Create emission factors table
    c.execute('''CREATE TABLE IF NOT EXISTS emission_factors
                 (mode TEXT PRIMARY KEY,
                  factor REAL,
                  unit TEXT)''')
    
    # Insert default emission factors if table is empty
    c.execute("SELECT COUNT(*) FROM emission_factors")
    if c.fetchone()[0] == 0:
        default_factors = [
            ('Petrol Car', 0.192, 'kg/km'),
            ('Diesel Car', 0.171, 'kg/km'),
            ('CNG Auto', 0.075, 'kg/km'),
            ('Bus', 0.082, 'kg/pkm'),
            ('Metro', 0.040, 'kg/pkm'),
            ('EV Car', 0.070, 'kg/km'),
            ('Cycle', 0.0, 'kg/km'),
            ('Walk', 0.0, 'kg/km')
        ]
        c.executemany("INSERT INTO emission_factors VALUES (?, ?, ?)", default_factors)
    
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Emission factors (will be loaded from DB)
def get_emission_factors():
    conn = sqlite3.connect('co2_saver.db')
    factors = pd.read_sql("SELECT * FROM emission_factors", conn)
    conn.close()
    return factors.set_index('mode')['factor'].to_dict()

# Calculate CO2 emissions
def calculate_co2(mode, distance, occupancy=1):
    factors = get_emission_factors()
    
    if mode not in factors:
        return 0, 0, 0, 0
    
    # For public transport, occupancy is already accounted for in per-passenger-km factors
    if mode in ['Bus', 'Metro']:
        co2_emitted = factors[mode] * distance
    else:
        # For personal vehicles, divide by occupancy
        co2_emitted = factors[mode] * distance / max(1, occupancy)
    
    # Baseline is petrol car solo
    baseline_co2 = factors['Petrol Car'] * distance
    
    # CO2 saved compared to baseline
    co2_saved = max(0, baseline_co2 - co2_emitted)
    percent_improvement = (co2_saved / baseline_co2) * 100 if baseline_co2 > 0 else 0
    
    # Trees equivalent (assuming 1 tree absorbs ~21.77 kg CO2 per year, ~0.06 kg/day)
    trees_saved = co2_saved / 0.06
    
    return co2_emitted, co2_saved, percent_improvement, trees_saved

# Find better alternative mode
def suggest_better_mode(distance, current_mode):
    """
    Suggest a greener but practical alternative.
    - Applies PRACTICAL_LIMITS_KM so we never suggest Cycle/Walk for very long trips.
    - Ignores tiny savings (<0.25 kg).
    """
    factors = get_emission_factors()
    if current_mode not in factors:
        return None, 0

    current_emission = factors[current_mode] * distance
    candidates = []

    for mode, factor in factors.items():
        if mode == current_mode:
            continue
        if not is_practical(mode, float(distance)):
            continue
        mode_emission = factor * distance
        if mode_emission < current_emission:
            candidates.append((mode, mode_emission))

    if not candidates:
        return None, 0

    best_mode, best_emission = min(candidates, key=lambda x: x[1])
    savings = current_emission - best_emission

    # Ignore negligible savings
    if savings < 0.25:
        return None, 0

    return best_mode, savings

# Save trip to database
def save_trip(user_name, mode, distance, occupancy):
    co2_emitted, co2_saved, percent_improvement, trees_saved = calculate_co2(mode, distance, occupancy)
    best_mode, _ = suggest_better_mode(distance, mode)
    
    conn = sqlite3.connect('co2_saver.db')
    c = conn.cursor()
    
    # Get emission factor for this mode
    factors = get_emission_factors()
    emission_factor = factors.get(mode, 0)
    
    # Calculate baseline CO2
    baseline_co2 = factors.get('Petrol Car', 0.192) * distance
    
    # Insert trip
    c.execute('''INSERT INTO trips 
                 (user_name, date, mode, distance, occupancy, emission_factor, 
                  co2_emitted, baseline_co2, co2_saved, percent_improvement, 
                  suggested_mode, trees_saved)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mode, distance, occupancy, emission_factor,
               co2_emitted, baseline_co2, co2_saved, percent_improvement,
               best_mode, trees_saved))
    
    conn.commit()
    conn.close()
    
    return co2_emitted, co2_saved, percent_improvement, best_mode, trees_saved

# Get all trips
def get_all_trips():
    try:
        conn = sqlite3.connect('co2_saver.db')
        trips = pd.read_sql("SELECT * FROM trips ORDER BY date DESC", conn)
        conn.close()
        return trips
    except Exception as e:
        st.error(f"Error loading trips: {e}")
        return pd.DataFrame()

# Get dashboard summary
def get_dashboard_summary():
    conn = sqlite3.connect('co2_saver.db')
    
    try:
        # Total CO2 emitted
        total_emitted = pd.read_sql("SELECT COALESCE(SUM(co2_emitted), 0) as total FROM trips", conn).iloc[0,0]
        
        # Total CO2 saved
        total_saved = pd.read_sql("SELECT COALESCE(SUM(co2_saved), 0) as total FROM trips", conn).iloc[0,0]
        
        # Total trips
        total_trips = pd.read_sql("SELECT COUNT(*) as count FROM trips", conn).iloc[0,0]
        
        # Mode distribution
        mode_dist = pd.read_sql("SELECT mode, COUNT(*) as count FROM trips GROUP BY mode", conn)
        
    except Exception as e:
        st.error(f"Error loading dashboard data: {e}")
        total_emitted = total_saved = total_trips = 0
        mode_dist = pd.DataFrame()
    
    conn.close()
    
    return {
        'total_emitted': total_emitted,
        'total_saved': total_saved,
        'total_trips': total_trips,
        'mode_dist': mode_dist
    }

# Prediction tool
def predict_savings(current_mode, new_mode, trips_per_week, distance_per_trip):
    factors = get_emission_factors()
    
    if current_mode not in factors or new_mode not in factors:
        return 0, 0, 0
    
    # Weekly CO2 for current mode
    current_co2 = factors[current_mode] * distance_per_trip * trips_per_week
    
    # Weekly CO2 for new mode
    new_co2 = factors[new_mode] * distance_per_trip * trips_per_week
    
    # Weekly savings
    weekly_savings = max(0, current_co2 - new_co2)
    
    # Annual savings
    annual_savings = weekly_savings * 52
    
    # Trees equivalent
    trees_saved = annual_savings / (0.06 * 365)  # 0.06 kg/day per tree
    
    return weekly_savings, annual_savings, trees_saved

# Admin page for editing emission factors
def admin_page():
    st.title("🔧 Admin - Emission Factors")
    
    conn = sqlite3.connect('co2_saver.db')
    factors_df = pd.read_sql("SELECT * FROM emission_factors", conn)
    conn.close()
    
    st.info("Update emission factors below. Changes will be saved to the database.")
    
    edited_df = st.data_editor(factors_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Save Changes"):
        try:
            conn = sqlite3.connect('co2_saver.db')
            # Clear existing factors
            conn.execute("DELETE FROM emission_factors")
            # Insert updated factors
            for _, row in edited_df.iterrows():
                conn.execute("INSERT INTO emission_factors VALUES (?, ?, ?)", 
                           (row['mode'], row['factor'], row['unit']))
            conn.commit()
            conn.close()
            st.success("✅ Emission factors updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving changes: {e}")

#--------------------------------------
def get_last_trip(user_name: str):
    """Return the most recent previous trip for the user (excluding the current one)."""
    conn = sqlite3.connect('co2_saver.db')
    query = """
        SELECT * FROM trips
        WHERE user_name = ?
        ORDER BY date DESC
        LIMIT 1 OFFSET 1
    """  # OFFSET 1 → skip the *latest* (current) trip
    last_trip = pd.read_sql(query, conn, params=(user_name,))
    conn.close()
    return last_trip.iloc[0] if not last_trip.empty else None



def get_user_weekly_stats(user_name: str):
    conn = sqlite3.connect('co2_saver.db')
    df = pd.read_sql("SELECT user_name, date, co2_saved, co2_emitted FROM trips", conn)
    conn.close()

    if df.empty:
        return 0, 0

    df['date'] = pd.to_datetime(df['date'])
    start_of_week = pd.Timestamp.now().normalize() - pd.to_timedelta(pd.Timestamp.now().weekday(), unit="D")
    user_df = df[(df['date'] >= start_of_week) & (df['user_name'] == user_name)]

    return user_df['co2_emitted'].sum(), user_df['co2_saved'].sum()

def get_weekly_leaderboard():
    conn = sqlite3.connect('co2_saver.db')
    df = pd.read_sql("SELECT user_name, date, co2_saved FROM trips", conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df['date'])
    start_of_week = pd.Timestamp.now().normalize() - pd.to_timedelta(pd.Timestamp.now().weekday(), unit="D")
    week_df = df[df['date'] >= start_of_week]

    # Weekly totals for active users
    leaderboard = week_df.groupby("user_name")['co2_saved'].sum().reset_index()

    # ✅ Ensure ALL users appear (with 0 if no trips this week)
    all_users = df['user_name'].unique()
    leaderboard = leaderboard.set_index("user_name").reindex(all_users, fill_value=0).reset_index()

    # Sort by saved CO₂
    leaderboard = leaderboard.sort_values("co2_saved", ascending=False).reset_index(drop=True)
    return leaderboard





def get_leaf_badge(co2_saved_week: float):
    """Return badge name and emoji based on weekly CO₂ saved."""
    if co2_saved_week >= 20:
        return "🌟 Green Champion", "gold"
    elif co2_saved_week >= 10:
        return "🌿 Silver Saver", "silver"
    elif co2_saved_week >= 5:
        return "🍃 Bronze Beginner", "bronze"
    else:
        return "🌱 Starter Leaf", "starter"


def get_today_stats():
    """Return today's CO₂ emitted and saved totals."""
    conn = sqlite3.connect('co2_saver.db')
    df = pd.read_sql("SELECT date, co2_emitted, co2_saved FROM trips", conn)
    conn.close()

    if df.empty:
        return 0, 0

    df['date'] = pd.to_datetime(df['date'])
    today = pd.Timestamp.now().normalize()
    today_df = df[df['date'].dt.date == today.date()]

    return today_df['co2_emitted'].sum(), today_df['co2_saved'].sum()


def get_global_leaderboard():
    """Return leaderboard of all users' total CO₂ saved (all-time)."""
    conn = sqlite3.connect('co2_saver.db')
    df = pd.read_sql("SELECT user_name, co2_saved FROM trips", conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    leaderboard = (
        df.groupby("user_name")["co2_saved"]
        .sum()
        .reset_index()
        .sort_values("co2_saved", ascending=False)
    )
    return leaderboard

def top_nav_bar():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Log Trip", "Dashboard", "History", "Prediction Tool",
                 "Cost Dashboard", "Green Map", "Leaderboard", "Admin"],
        icons=["house", "car-front", "bar-chart", "journal-text", "magic",
               "cash-coin", "map", "trophy", "tools"],
        orientation="horizontal",
        styles={
            "container": {"padding": "10px", "background-color": "#1c1c1c"},
            "nav-link": {"color": "#eee", "font-size": "14px", "margin": "0px"},
            "nav-link-selected": {"background-color": "#7c4dff"},
        }
    )
    st.session_state["app_mode"] = selected
    return selected



def chatbot_ui():
    st.title("🤖 Eco Chatbot - Ask me anything!")
    st.markdown("Get eco-friendly travel & CO₂ saving tips 🌱")
    
    # User input
    user_input = st.text_input("💬 Ask your question (e.g., 'How can I reduce emissions on my commute?')")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if user_input:
        try:
            # Use a pre-trained question-answering model
            qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
            
            # Provide a detailed, professional-grade context. This is the key.
            context = """
            What are some eco-friendly alternatives to driving a car?
            Eco-friendly travel options include walking, cycling, and using public transport like buses or the metro. These modes emit significantly less CO2 than private vehicles and are often more cost-effective.

            How can I reduce emissions on my commute?
            To reduce your carbon footprint when traveling, consider using public transportation, such as buses or the metro, which are more energy-efficient than private vehicles. For longer distances, carpooling or switching to an electric vehicle (EV) significantly lowers per-person emissions. Planning your trips efficiently by combining multiple errands into one journey helps reduce short, emission-heavy 'cold start' drives. You can also save fuel by avoiding heavy traffic, maintaining a steady speed, and ensuring your vehicle is well-maintained with properly inflated tires.

            How does cycling help the environment?
            Cycling is a zero-emission activity that directly helps reduce air pollution and reliance on fossil fuels. It requires no fuel and produces no greenhouse gases, making it one of the most sustainable forms of transport. Additionally, it helps reduce traffic congestion in urban areas.

            What's the best way to save energy at home?
            To save energy at home, focus on improving efficiency. Simple changes include switching to energy-efficient appliances, using LED light bulbs, and unplugging electronics when not in use. You can also lower your heating and cooling costs by properly insulating your home, using a smart thermostat, and sealing air leaks around windows and doors. Another effective method is to use solar power for electricity generation.
            """
            
            # Get the answer from the model using the detailed context
            result = qa_pipeline(question=user_input, context=context)
            response = result['answer']
            
            # Save conversation
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))
            
        except Exception as e:
            st.error(f"Chatbot error: {e}")
            
    # Display chat history
    for role, msg in st.session_state.chat_history[-6:]:
        if role == "You":
            st.markdown(f"🧑 *You:* {msg}")
        else:
            st.markdown(f"🤖 *Bot:* {msg}")

#--------------------------------------

def chatbot_floating_ui():
    st.markdown("""
        <style>
        /* Floating chat button */
        .chat-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #7c4dff;
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            z-index: 1000;
        }
        .chat-button:hover {
            background-color: #6a3de0;
        }

        /* Chat window */
        .chat-popup {
            display: none;
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 350px;
            max-height: 500px;
            background: #1c1c1c;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            overflow: hidden;
            z-index: 1000;
        }
        .chat-header {
            background: #7c4dff;
            padding: 12px;
            color: white;
            font-weight: bold;
            text-align: center;
        }
        .chat-body {
            padding: 12px;
            height: 350px;
            overflow-y: auto;
            color: #eee;
            font-size: 14px;
        }
        .chat-footer {
            padding: 10px;
            background: #111;
        }
        .chat-footer input {
            width: 75%;
            padding: 8px;
            border: none;
            border-radius: 10px;
        }
        .chat-footer button {
            padding: 8px 12px;
            background: #7c4dff;
            color: white;
            border: none;
            border-radius: 10px;
            margin-left: 5px;
            cursor: pointer;
        }
        </style>

        <div class="chat-button" onclick="toggleChat()">💬</div>

        <div id="chatPopup" class="chat-popup">
            <div class="chat-header">EcoBot 🌱</div>
            <div class="chat-body" id="chatBody">
                <p><b>EcoBot:</b> Hi! I’m here to help you reduce your CO₂ footprint 🌍💡</p>
            </div>
            <div class="chat-footer">
                <input type="text" id="userInput" placeholder="Type a message..." />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>

        <script>
        function toggleChat() {
            var popup = document.getElementById("chatPopup");
            if (popup.style.display === "block") {
                popup.style.display = "none";
            } else {
                popup.style.display = "block";
            }
        }

        function sendMessage() {
            var input = document.getElementById("userInput");
            var body = document.getElementById("chatBody");
            var userMsg = input.value.trim();
            if(userMsg) {
                body.innerHTML += "<p><b>You:</b> " + userMsg + "</p>";
                body.scrollTop = body.scrollHeight;
                input.value = "";

                // Dummy bot response
                setTimeout(function() {
                    body.innerHTML += "<p><b>EcoBot:</b> I'm still learning 🌱 but I heard you!</p>";
                    body.scrollTop = body.scrollHeight;
                }, 800);
            }
        }
        </script>
    """, unsafe_allow_html=True)

#------------------------------------------------------------------------------------

#-----------------QR GENERATOR--------------------------------
from PIL import Image


#--------------------------------------------------------

# Main app
def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True
        
        
    if "app_mode" not in st.session_state:
        st.session_state["app_mode"] = "🏠 Home"
    if "entered" not in st.session_state:
        st.session_state["entered"] = False
        



    # --- Session State ---
    if "app_mode" not in st.session_state:
        st.session_state["app_mode"] = "🏠 Home"

    # ---------------- HOME PAGE ----------------

    # ---------------- MAIN UI ----------------
    app_mode = top_nav_bar()

    # Floating chatbot
    chatbot_floating_ui()

    # ---------------- Floating Chatbot Button ----------------
    st.markdown("""
        <style>
        .chat-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #7B3FE4;
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 28px;
            text-align: center;
            line-height: 60px;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 9999;
        }
        </style>
        <div class="chat-button" onclick="window.parent.document.querySelector('details').open = true">💬</div>
    """, unsafe_allow_html=True)

    

    # ---------------- ROUTING ----------------
    if app_mode == "Home":
        chatbot_floating_ui()
        st.title("🌱 Welcome to CO₂ Saver")
        st.markdown("Use the sidebar to navigate 🚀")

    elif app_mode == "Log Trip":
        # your existing Log Trip code
        st.title("🌱 Log Your Trip")
        st.markdown("Track your transportation and see your CO₂ impact instantly!")
        
        # Form for input
        with st.form("trip_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                user_name = st.text_input("Your Name", "Anonymous")
                mode = st.selectbox("Mode of Transport", 
                    ["Petrol Car", "Diesel Car", "CNG Auto", "Bus", "Metro", "EV Car", "Cycle", "Walk"])
            
            with col2:
                distance = st.number_input("Distance (km)", min_value=0.1, max_value=1000.0, value=5.0)
                occupancy = st.number_input("Occupancy (for personal vehicles)", min_value=1, max_value=8, value=1)
            
            submitted = st.form_submit_button("🌟 Generate Green Receipt", use_container_width=True)
        
        # Processing and display outside the form
        if submitted:
            try:
                co2_emitted, co2_saved, percent_improvement, best_mode, trees_saved = save_trip(
                    user_name, mode, distance, occupancy)
                

                # Fetch the user’s last trip (before this one)
                last_trip = get_last_trip(user_name)

                vs_last_msg = ""
                if last_trip is not None:
                    prev_emission = last_trip["co2_emitted"]
                    delta = prev_emission - co2_emitted
                    if delta > 0:
                        vs_last_msg = f"🌱 You saved {delta:.2f} kg CO₂ compared to your last trip!"
                    elif delta < 0:
                        vs_last_msg = f"⚠️ You emitted {abs(delta):.2f} kg more CO₂ than your last trip."
                    else:
                        vs_last_msg = "➖ Same CO₂ emissions as your last trip."

                # Display receipt
                st.success("🎉 Here's your Green Receipt!")
                if vs_last_msg:
                  st.info(vs_last_msg)

                
                # Generate and display the receipt
                img_bytes = generate_receipt_image(
                    user_name, mode, distance, co2_emitted, co2_saved, 
                    percent_improvement, best_mode, trees_saved
                )
                
                # Download button
                st.download_button(
                    label="⬇️ Download Receipt as PNG",
                    data=img_bytes,
                    file_name=f"green_receipt_{user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )

               # --- Social Share Buttons with Icons ---
                import urllib.parse

                # Text to prefill in share box
                share_text = f"I just saved {co2_saved:.2f} kg CO₂ ({percent_improvement:.1f}% greener) using Green Receipt CO₂ Saver! 🌱🚴‍♂️ #GoGreen"
                encoded_text = urllib.parse.quote(share_text)

                # --- Social Media URLs ---
                # WhatsApp
                wa_url = f"https://api.whatsapp.com/send?text={encoded_text}"

                # Twitter (X)
                twitter_url = f"https://twitter.com/intent/tweet?text={encoded_text}"

                # LinkedIn (supports prefilled text in 'summary')
                linkedin_url = f"https://www.linkedin.com/shareArticle?mini=true&url=https://example.com&title=Green+Receipt+CO2+Saver&summary={encoded_text}&source=GreenReceipt"

                # --- Icons Row ---
                # --- Icons Row ---
                # --- Icons Row ---
               # --- Icons Row ---
                st.markdown(
                    f"""
                    <h3>Share your achievement:</h3>
                    <div style="display: flex; gap: 250px; align-items: center; margin-top: 15px;">
                        <a href="{wa_url}" target="_blank">
                            <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" width="40" height="40" style="margin: 5px;">
                        </a>
                        <a href="{twitter_url}" target="_blank">
                            <img src="https://cdn-icons-png.flaticon.com/512/733/733579.png" width="40" height="40" style="margin: 5px;">
                        </a>
                        <a href="{linkedin_url}" target="_blank">
                            <img src="https://cdn-icons-png.flaticon.com/512/733/733561.png" width="40" height="40" style="margin: 5px;">
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)


                
                # Show some quick stats
                col1, col2, col3 = st.columns(3)
                col1.metric("CO₂ Emitted", f"{co2_emitted:.2f} kg", delta=None)
                col2.metric("CO₂ Saved", f"{co2_saved:.2f} kg", delta=f"{percent_improvement:.1f}%")
                col3.metric("Trees Equivalent", f"{trees_saved:.1f} days", delta=None)
                
            except Exception as e:
                st.error(f"Error processing trip: {e}")

    elif app_mode == "Dashboard":
        st.title("📊 Live Dashboard")
        
        # Get dashboard data
        summary = get_dashboard_summary()
        
        if summary['total_trips'] == 0:
            st.info("🚗 No trips recorded yet. Log a trip to see your dashboard!")
            return
        
        # Display KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Total CO₂ Emitted", f"{summary['total_emitted']:.1f} kg")
        col2.metric("Total CO₂ Saved", f"{summary['total_saved']:.1f} kg")
        col3.metric("Total Trips", summary['total_trips'])
        
        # --- Individual Weekly Badge ---
        # Ask user to pick their name (or detect if logged in later)
        # --- INDIVIDUAL BADGE ---
        # Dynamically extract user names from the leaderboard
        today_emitted, today_saved = get_today_stats()

        # ✅ Get all users from full trip history
        trips = get_all_trips()
        if trips.empty:
            user_list = ["Anonymous"]
        else:
            user_list = sorted(trips["user_name"].unique())

        # Dropdown to select a user
        user = st.selectbox("Select a user", user_list)


        #user = st.session_state.get("current_user", "Anonymous")  # fallback if no login system
        weekly_emitted, weekly_saved = get_user_weekly_stats(user)
        badge_name, _ = get_leaf_badge(weekly_saved)

        st.subheader(f"🌿 Weekly Progress for {user}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Today’s CO₂ Emitted", f"{today_emitted:.1f} kg")
        col2.metric("Today’s CO₂ Saved", f"{today_saved:.1f} kg")
        col1.metric("This Week CO₂ Emitted", f"{weekly_emitted:.1f} kg")
        col2.metric("This Week CO₂ Saved", f"{weekly_saved:.1f} kg")
        col3.metric("Your Badge", badge_name)

        goal = 20
        progress = min(100, (weekly_saved / goal) * 100)
        st.progress(progress / 100)
        st.caption(f"Progress to Green Champion: {weekly_saved:.1f} / {goal} kg saved")

        # --- GLOBAL LEADERBOARD ---
        st.subheader("🏆 Global Weekly Leaderboard")
        leaderboard = get_weekly_leaderboard()
        if leaderboard.empty:
            st.info("No trips recorded this week yet!")
        else:
            st.dataframe(leaderboard, use_container_width=True)




        # Mode distribution chart
        if not summary['mode_dist'].empty:
            st.subheader("🚦 Transport Mode Distribution")
            fig = px.pie(summary['mode_dist'], names='mode', values='count', 
                         title="Breakdown of Transport Modes Used",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent trips
        st.subheader("📝 Recent Trips")
        trips = get_all_trips()
        if not trips.empty:
            display_trips = trips.head(10)[['user_name', 'date', 'mode', 'distance', 'co2_emitted', 'co2_saved']]
            st.dataframe(display_trips, use_container_width=True)
        

    elif app_mode == "History":
        st.title("📋 Trip History")
        
        trips = get_all_trips()
        
        if trips.empty:
            st.info("📝 No trips recorded yet. Log some trips to see your history!")
            return
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            user_filter = st.selectbox("Filter by user", 
                                     ["All"] + sorted(trips['user_name'].unique().tolist()))
        with col2:
            date_range = st.date_input("Filter by date range", 
                                     [datetime.now().date() - pd.Timedelta(days=7), datetime.now().date()])
        
        # Apply filters
        filtered_trips = trips.copy()
        if user_filter != "All":
            filtered_trips = filtered_trips[filtered_trips['user_name'] == user_filter]
        
        if len(date_range) == 2:
            filtered_trips = filtered_trips[
                (pd.to_datetime(filtered_trips['date']).dt.date >= date_range[0]) &
                (pd.to_datetime(filtered_trips['date']).dt.date <= date_range[1])
            ]
        
        st.dataframe(filtered_trips, use_container_width=True)
        
        # Summary statistics
        if not filtered_trips.empty:
            st.subheader("📈 Summary Statistics")
            total_co2 = filtered_trips['co2_emitted'].sum()
            total_saved = filtered_trips['co2_saved'].sum()
            avg_saving = filtered_trips['percent_improvement'].mean()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total CO₂ Emitted", f"{total_co2:.1f} kg")
            col2.metric("Total CO₂ Saved", f"{total_saved:.1f} kg")
            col3.metric("Average Improvement", f"{avg_saving:.1f}%")

    elif app_mode == "Prediction Tool":
        st.title("🔮 CO₂ Savings Predictor")
        
        st.markdown("""
        🌱 See how much CO₂ you could save by changing your transportation habits.
        """)
        
        with st.form("prediction_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                current_mode = st.selectbox("Your Current Mode", 
                                          ["Petrol Car", "Diesel Car", "CNG Auto", "Bus", "Metro", "EV Car", "Cycle", "Walk"])
            with col2:
                new_mode = st.selectbox("Alternative Mode", 
                                       ["Petrol Car", "Diesel Car", "CNG Auto", "Bus", "Metro", "EV Car", "Cycle", "Walk"])
            
            col3, col4 = st.columns(2)
            with col3:
                trips_per_week = st.slider("Number of trips per week", 1, 20, 5)
            with col4:
                distance_per_trip = st.number_input("Average distance per trip (km)", min_value=0.1, max_value=100.0, value=5.0)
            
            submitted = st.form_submit_button("🔍 Calculate Savings")
            
            if submitted:
                weekly_savings, annual_savings, trees_saved = predict_savings(
                    current_mode, new_mode, trips_per_week, distance_per_trip)
                
                st.success(f"""
                **🎯 Potential Savings:**
                
                - **📅 Weekly CO₂ Savings:** {weekly_savings:.2f} kg
                - **📆 Annual CO₂ Savings:** {annual_savings:.2f} kg
                - **🌳 Equivalent to saving {trees_saved:.1f} trees for a year**
                """)
                
                # Visualization
                factors = get_emission_factors()
                weekly_current = factors[current_mode] * distance_per_trip * trips_per_week
                weekly_new = factors[new_mode] * distance_per_trip * trips_per_week
                
                fig = go.Figure(data=[
                    go.Bar(name='Current Mode', x=[current_mode], y=[weekly_current], marker_color='#ff6b6b'),
                    go.Bar(name='New Mode', x=[new_mode], y=[weekly_new], marker_color='#4ecdc4')
                ])
                fig.update_layout(title='Weekly CO₂ Emissions Comparison', yaxis_title='CO₂ Emissions (kg)')
                st.plotly_chart(fig, use_container_width=True)

    elif app_mode == "Cost Dashboard":
        cost_dashboard()

    elif app_mode == "Green Map":
        green_map()

    elif app_mode == "Leaderboard":
        st.title("🏆 Global CO₂ Saver Leaderboard")
        
        leaderboard = get_global_leaderboard()
        
        if leaderboard.empty:
          st.info("No trips logged yet.")
        else:
          # Show top savers
          st.subheader("🌍 Top Savers (All Time)")
          st.dataframe(leaderboard, use_container_width=True)

          # Bar chart for better visualization
          fig = px.bar(
              leaderboard.head(10), 
              x="user_name", 
              y="co2_saved", 
              title="Top 10 CO₂ Savers",
              labels={"user_name": "User", "co2_saved": "CO₂ Saved (kg)"},
              color="co2_saved",
              color_continuous_scale="Greens"
          )
          st.plotly_chart(fig, use_container_width=True)

          # Auto-refresh every 30 sec (good for booth mode)
          #st.caption("⏳ Auto-refresh enabled every 30 seconds for live booth display.")
          #st.rerun()


    elif app_mode == "Admin":
        admin_page()
        
    
    if st.session_state["app_mode"] != "Home":
        chatbot_floating_ui()


if __name__ == "__main__":
    main()


# Handle floating chat button state
query_params = st.query_params
if "open_chat" in query_params:
    st.session_state["chat_open"] = True
elif "chat_open" not in st.session_state:
    st.session_state["chat_open"] = False

# Render floating chat button
st.markdown("""
    <style>
    .chat-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #7B3FE4;
        color: white;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 28px;
        text-align: center;
        line-height: 60px;
        cursor: pointer;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        z-index: 9999;
    }
    </style>
    <a href="?open_chat=1">
        <div class="chat-button">💬</div>
    </a>
""", unsafe_allow_html=True)

# Display chatbot when opened
if st.session_state.get("chat_open"):
    chatbot_ui()
