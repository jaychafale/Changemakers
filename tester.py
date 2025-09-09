import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import base64
from io import BytesIO
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
from streamlit_option_menu import option_menu
import torch
import urllib.parse
import time 
import math
import google.generativeai as genai

# Streamlit page configuration
st.set_page_config(
    page_title="CO₂ Saver - Green Receipt",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------
# CSS for Nature-Themed UI
# -------------------------
st.markdown("""
<style>
/* Global UI Enhancements */
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    font-size: 16px;
    color: #2c3e50;
    background: linear-gradient(135deg, #f5f9e9 0%, #d8f3dc 50%, #b7e4c7 100%);
    background-attachment: fixed;
    margin: 0;
    padding: 0;
}

/* Main container */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Headings */
h1, h2, h3 {
    color: #1b4332;
    font-weight: 700;
    margin-top: 0.5em;
    margin-bottom: 0.3em;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}

h1 {
    color: #1b4332; /* Updated to ensure consistent color */
    padding-bottom: 10px;
    border-bottom: 2px solid #d8f3dc;
}

h1.breathe-easy {
    color: #1b4332; /* Already set to requested color */
    text-shadow: 0 0 0px rgba(255,255,255,0.4);
    font-weight: 800;
    font-size: 3rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%);
    border-right: 1px solid #40916c;
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

[data-testid="stSidebar"] .stSelectbox, 
[data-testid="stSidebar"] .stNumberInput,
[data-testid="stSidebar"] .stTextInput {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 8px;
}
/* Buttons */
/* Make Home page buttons look like "Log Your Trip" card */
.stButton > button {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    color: #1b4332;
    font-weight: 600;
    font-size: 16px;
    transition: all 0.3s ease;
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

.stButton > button:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 25px rgba(0,0,0,0.15);
    background: rgba(255, 255, 255, 0.9);
}


/* Cards */
.card {
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    border: 1px solid rgba(255, 255, 255, 0.5);
    margin-bottom: 20px;
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 25px rgba(0,0,0,0.15);
}

/* Metrics */
[data-testid="stMetricValue"] {
    font-size: 24px;
    color: #1b4332;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    font-size: 14px;
    color: #40916c;
    font-weight: 600;
}

[data-testid="stMetricDelta"] {
    font-size: 16px;
    font-weight: 600;
}

/* Input Fields */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > select {
    border-radius: 12px;
    border: 2px solid #d8f3dc;
    padding: 10px;
    background-color: rgba(255, 255, 255, 0.8);
    color: #1b4332 !important;
}

.stTextInput > div > div > input::placeholder,
.stNumberInput > div > div > input::placeholder,
.stSelectbox > div > div > select option {
    color: #40916c !important;   /* ✅ Softer green placeholder */
}

/* Data Frames */
.dataframe {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Chart Containers */
.element-container:has(.stPlotlyChart), 
.element-container:has(.stImage) {
    padding: 15px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.7);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    backdrop-filter: blur(5px);
}

/* Navigation */
.st-emotion-cache-1avcm0n {
    background: linear-gradient(90deg, #1b4332 0%, #2d6a4f 100%);
}

/* Custom Classes */
.nature-bg {
    position: relative;
    background-image: url("https://images.unsplash.com/photo-1418065460487-3e41a6c84dc5?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1920&q=80");
    background-size: cover;
    background-position: center;
    padding: 30px;
    border-radius: 20px;
    color: white;
    text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
    overflow: hidden;
}
/*
.nature-bg::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.4); /* white overlay = lighten */
    border-radius: 20px;
    z-index: 0;
}*/

.nature-bg * {
    position: relative;
    z-index: 1; /* keep text above overlay */
}


            
.breathing-space {
    padding: 40px;
    text-align: center;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 20px;
    margin: 20px 0;
    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}

.breathing-space h2 {
    color: #2d6a4f;
    font-size: 28px;
    margin-bottom: 20px;
}

.breathing-space p {
    font-size: 18px;
    line-height: 1.6;
    color: #40916c;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.stApp {
    animation: fadeIn 1s ease-out;
}

/* Responsive Design */
@media (max-width: 768px) {
    .card {
        padding: 15px;
    }
    
    h1 {
        font-size: 28px;
    }
    
    h2 {
        font-size: 22px;
    }
}
</style>
""", unsafe_allow_html=True)

# Add custom fonts
st.markdown("""
<link href='https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap' rel='stylesheet'>
""", unsafe_allow_html=True)

# API Key for OpenRouteService (replace with your actual key)
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImFlZjcxNWEyZDFiMDQ3NDlhMjI0ZTNmMDJjYWRjODA1IiwiaCI6Im11cm11cjY0In0="


# -------------------------
# Practicality Rules & Helpers
# -------------------------
PRACTICAL_LIMITS_KM = {
    "Walk": 2.0,
    "Cycle": 10.0,
}

def is_practical(mode: str, distance_km: float) -> bool:
    lim = PRACTICAL_LIMITS_KM.get(mode)
    return True if lim is None else distance_km <= lim

def score_to_stars(percent_improvement: float) -> float:
    stars = 1.0 + 4.0 * (max(0.0, min(100.0, percent_improvement)) / 100.0)
    return round(stars, 2)

# -------------------------
# Receipt Generation
# -------------------------
def _pick_baseline_mode(current_mode: str, factors: dict) -> str:
    for k in ["Car", "Petrol Car", "Gasoline Car", "Diesel Car"]:
        if k in factors:
            return k
    return max(factors.items(), key=lambda kv: kv[1])[0]

def generate_receipt_image(user_name, mode, distance, co2_emitted, co2_saved,
                          percent_improvement, best_mode, trees_saved):
    stars_value = score_to_stars(percent_improvement)
    full_stars = int(stars_value)
    empty_stars = 5 - full_stars
    stars_str = "★" * full_stars + "☆" * empty_stars

    if best_mode and not is_practical(best_mode, float(distance)):
        best_mode = None

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
          <div class="chip">🍃 <small>Make it </small>carbon neutral</div>
        </div>
        {"<div class='hint'>✨ Try next time: <b>"+best_mode+"</b></div>" if best_mode else ""}
        {tips_html}
      </div>
    </body>
    </html>
    """

    st.markdown(html_receipt, unsafe_allow_html=True)

    hti = Html2Image(output_path=tempfile.gettempdir())
    temp_html = os.path.join(tempfile.gettempdir(), "receipt.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_receipt)

    output_png = os.path.join(tempfile.gettempdir(), "receipt.png")
    hti.screenshot(html_file=temp_html, save_as="receipt.png", size=(1280, 900))

    with open(output_png, "rb") as f:
        img_bytes = f.read()

    return img_bytes

# -------------------------
# Cost Savings Dashboard
# -------------------------
def cost_dashboard():
    st.subheader("💰 Cost Savings Dashboard")
    fuel_price = 105
    km_per_litre = 15
    petrol_cost_per_km = fuel_price / km_per_litre
    
    trips = get_all_trips()
    if trips.empty:
        st.info("Log some trips to see your cost savings!")
        return

    cost_factors = {
        "Petrol Car": petrol_cost_per_km,
        "Diesel Car": 100/18,
        "CNG Auto": 3,
        "Bus": 0.5,
        "Metro": 1,
        "EV Car": 1.5,
        "Cycle": 0,
        "Walk": 0
    }

    trips["baseline_cost"] = trips["distance"] * petrol_cost_per_km
    trips["actual_cost"] = trips.apply(lambda row: row["distance"]*cost_factors.get(row["mode"],0), axis=1)
    trips["money_saved"] = trips["baseline_cost"] - trips["actual_cost"]

    st.metric("💵 Total ₹ Saved vs Petrol Car", f"₹{trips['money_saved'].sum():.0f}")

    savings_by_mode = trips.groupby("mode")[["baseline_cost","actual_cost","money_saved"]].sum().reset_index()

    fig = go.Figure(data=[
        go.Bar(name="Baseline Petrol Car", x=savings_by_mode["mode"], y=savings_by_mode["baseline_cost"]),
        go.Bar(name="Actual Cost", x=savings_by_mode["mode"], y=savings_by_mode["actual_cost"]),
        go.Bar(name="Money Saved", x=savings_by_mode["mode"], y=savings_by_mode["money_saved"])
    ])
    fig.update_layout(barmode='group', title="Cost Comparison by Transport Mode")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Map Feature - Fixed Version
# -------------------------
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import time
import math  # Added for distance calculation

# -------------------------
# Map Feature - Fixed Version
# -------------------------

def geocode_place(place_name):
    """Geocode place name with error handling and caching"""
    if not place_name:
        return None
    
    if 'geocode_cache' not in st.session_state:
        st.session_state.geocode_cache = {}
    
    place_name = place_name.strip().lower()  # Normalize input
    if place_name in st.session_state.geocode_cache:
        return st.session_state.geocode_cache[place_name]
    
    try:
        geolocator = Nominatim(user_agent="green_map_app")
        location = geolocator.geocode(place_name, timeout=10)
        if location:
            result = (location.latitude, location.longitude)
            st.session_state.geocode_cache[place_name] = result
            return result
        else:
            st.error(f"Could not find location: {place_name}. Try a more specific name (e.g., 'Mumbai, India').")
    except Exception as e:
        st.error(f"Geocoding error for {place_name}: {str(e)}")
    return None

def get_route_coords(start_coords, end_coords):
    """Get route coordinates using OpenRouteService API"""
    if not start_coords or not end_coords:
        return []
    
    # Check cache first
    cache_key = f"{start_coords[0]},{start_coords[1]}_{end_coords[0]},{end_coords[1]}"
    if 'route_cache' in st.session_state and cache_key in st.session_state.route_cache:
        return st.session_state.route_cache[cache_key]
    
    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
        body = {
            "coordinates": [
                [start_coords[1], start_coords[0]],
                [end_coords[1], end_coords[0]]
            ]
        }
        r = requests.post(url, json=body, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            coords = [(lat, lon) for lon, lat in data["features"][0]["geometry"]["coordinates"]]
            # Cache the route
            if 'route_cache' not in st.session_state:
                st.session_state.route_cache = {}
            st.session_state.route_cache[cache_key] = coords
            return coords
        else:
            st.error(f"Route API Error: {r.status_code} - Check your API key or network.")
    except Exception as e:
        st.error(f"Route fetching error: {str(e)}")
    
    # Fallback to a straight-line route
    num_points = 20
    lat_step = (end_coords[0] - start_coords[0]) / num_points
    lon_step = (end_coords[1] - start_coords[1]) / num_points
    demo_route = [(start_coords[0] + lat_step * i, start_coords[1] + lon_step * i) for i in range(num_points + 1)]
    st.warning("Using demo route due to API failure.")
    if 'route_cache' not in st.session_state:
        st.session_state.route_cache = {}
    st.session_state.route_cache[cache_key] = demo_route
    return demo_route

def calculate_distance(coords):
    """Calculate distance between coordinates in km using Haversine formula"""
    if not coords or len(coords) < 2:
        return 0
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    total_distance = 0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        total_distance += haversine(lat1, lon1, lat2, lon2)
    
    return total_distance

def green_map():
    st.markdown("""
    <div class="card">
        <h1>
            <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f5fa.png" 
                alt="Map" width="32" style="vertical-align: middle; margin-right: 8px;">
            Green Map
        </h1>
        <p>Find and explore sustainable locations near you</p>
    </div>
    """, unsafe_allow_html=True)

    
    # Initialize session state for map persistence
    if 'map_created' not in st.session_state:
        st.session_state.map_created = False
    if 'current_map' not in st.session_state:
        st.session_state.current_map = None
    if 'map_results' not in st.session_state:
        st.session_state.map_results = None
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        start_place = st.text_input("📍 Start Location", "Mumbai", help="Where your journey begins")
        end_place = st.text_input("🎯 Destination", "Pune", help="Where you want to go")
        
        transport_options = st.multiselect(
            "🚴 Preferred Transport Modes",
            ["Walking", "Cycling", "Public Transport", "Electric Vehicle"],
            default=["Public Transport", "Cycling"],
            help="Select your preferred eco-friendly transport options"
        )
        
        if st.button("🗺️ Find Green Route", use_container_width=True):
            with st.spinner("Finding the greenest route..."):
                start_coords = geocode_place(start_place)
                end_coords = geocode_place(end_place)

                if not start_coords or not end_coords:
                    st.error("Could not find one or both locations. Please try different names.")
                    return

                route_coords = get_route_coords(start_coords, end_coords)
                
                # Create map with stable settings
                m = folium.Map(
                    location=start_coords, 
                    zoom_start=10, 
                    tiles='CartoDB positron',
                    zoom_control=True,
                    scrollWheelZoom=True,
                    dragging=True
                )
                
                folium.Marker(
                    start_coords, 
                    popup=f"Start: {start_place}",
                    icon=folium.Icon(color='green', icon='map-marker', prefix='fa')
                ).add_to(m)
                
                folium.Marker(
                    end_coords, 
                    popup=f"Destination: {end_place}",
                    icon=folium.Icon(color='darkgreen', icon='flag', prefix='fa')
                ).add_to(m)

                if route_coords:
                    folium.PolyLine(
                        route_coords, 
                        color="#2d6a4f", 
                        weight=6,
                        opacity=0.8,
                        popup="Eco-friendly Route",
                        tooltip="Recommended green path"
                    ).add_to(m)
                    
                    for i, coord in enumerate(route_coords[::max(1, len(route_coords)//5)]):
                        folium.CircleMarker(
                            location=coord,
                            radius=4,
                            color="#52b788",
                            fill=True,
                            fill_color="#40916c",
                            popup=f"Eco-point {i+1}"
                        ).add_to(m)

                # Store the map object and data in session state
                st.session_state.current_map = m
                st.session_state.map_created = True
                
                # Calculate distance and CO2 savings
                distance_km = calculate_distance(route_coords) or 150
                co2_saved = distance_km * 0.15
                
                st.session_state.map_results = {
                    'message': f"🗺️ Green route found! Approximate distance: {distance_km:.1f} km, Saves ~{co2_saved:.1f} kg CO₂!",
                    'distance_km': distance_km,
                    'co2_saved': co2_saved
                }
                
                st.success(st.session_state.map_results['message'])

    with col2:
        # Always show a map - either the calculated one or a default one
        if st.session_state.map_created and st.session_state.current_map:
            # Use a unique key based on the route to prevent re-rendering
            map_key = f"route_map_{hash(str(st.session_state.map_results)) if st.session_state.map_results else 'default'}"
            
            # Render the map
            map_interaction = st_folium(
                st.session_state.current_map, 
                width=700, 
                height=500,
                key=map_key,
                returned_objects=[]
            )
            
            st.markdown("""
            <div style="background: #e8f5e8; padding: 15px; border-radius: 10px; margin-top: 20px; border-left: 4px solid #2d6a4f;">
                <h4 style="color: #2d6a4f; margin: 0;">💡 Eco Travel Tips</h4>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Combine multiple errands into one trip</li>
                    <li>Consider public transport for longer distances</li>
                    <li>Walk or cycle for short trips under 3km</li>
                    <li>Car pool with colleagues or friends</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show default map
            initial_map = folium.Map(
                location=[19.0760, 72.8777],  # Mumbai coordinates
                zoom_start=10,
                tiles='CartoDB positron'
            )
            st_folium(initial_map, width=700, height=500, key="initial_map")
            st.info("👆 Enter locations and click 'Find Green Route' to see your eco-friendly path!")
# -------------------------
# Database Functions
# -------------------------
def init_db():
    conn = sqlite3.connect('co2_saver.db')
    c = conn.cursor()
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS emission_factors
                 (mode TEXT PRIMARY KEY,
                  factor REAL,
                  unit TEXT)''')
    
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

def get_emission_factors():
    conn = sqlite3.connect('co2_saver.db')
    factors = pd.read_sql("SELECT * FROM emission_factors", conn)
    conn.close()
    return factors.set_index('mode')['factor'].to_dict()

def calculate_co2(mode, distance, occupancy=1):
    factors = get_emission_factors()
    
    if mode not in factors:
        return 0, 0, 0, 0
    
    if mode in ['Bus', 'Metro']:
        co2_emitted = factors[mode] * distance
    else:
        co2_emitted = factors[mode] * distance / max(1, occupancy)
    
    baseline_co2 = factors['Petrol Car'] * distance
    
    co2_saved = max(0, baseline_co2 - co2_emitted)
    percent_improvement = (co2_saved / baseline_co2) * 100 if baseline_co2 > 0 else 0
    
    trees_saved = co2_saved / 0.06
    
    return co2_emitted, co2_saved, percent_improvement, trees_saved

def suggest_better_mode(distance, current_mode):
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

    if savings < 0.25:
        return None, 0

    return best_mode, savings

def save_trip(user_name, mode, distance, occupancy):
    co2_emitted, co2_saved, percent_improvement, trees_saved = calculate_co2(mode, distance, occupancy)
    best_mode, _ = suggest_better_mode(distance, mode)
    
    conn = sqlite3.connect('co2_saver.db')
    c = conn.cursor()
    
    factors = get_emission_factors()
    emission_factor = factors.get(mode, 0)
    
    baseline_co2 = factors.get('Petrol Car', 0.192) * distance
    
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

def get_all_trips():
    try:
        conn = sqlite3.connect('co2_saver.db')
        trips = pd.read_sql("SELECT * FROM trips ORDER BY date DESC", conn)
        conn.close()
        return trips
    except Exception as e:
        st.error(f"Error loading trips: {e}")
        return pd.DataFrame()

def get_dashboard_summary():
    conn = sqlite3.connect('co2_saver.db')
    
    try:
        total_emitted = pd.read_sql("SELECT COALESCE(SUM(co2_emitted), 0) as total FROM trips", conn).iloc[0,0]
        total_saved = pd.read_sql("SELECT COALESCE(SUM(co2_saved), 0) as total FROM trips", conn).iloc[0,0]
        total_trips = pd.read_sql("SELECT COUNT(*) as count FROM trips", conn).iloc[0,0]
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

def predict_savings(current_mode, new_mode, trips_per_week, distance_per_trip):
    factors = get_emission_factors()
    
    if current_mode not in factors or new_mode not in factors:
        return 0, 0, 0
    
    current_co2 = factors[current_mode] * distance_per_trip * trips_per_week
    new_co2 = factors[new_mode] * distance_per_trip * trips_per_week
    weekly_savings = max(0, current_co2 - new_co2)
    annual_savings = weekly_savings * 52
    trees_saved = annual_savings / (0.06 * 365)
    
    return weekly_savings, annual_savings, trees_saved

def admin_page():
    st.markdown("""
    <div class="card">
        <h1>
            <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f527.png" 
                alt="Tools" width="32" style="vertical-align: middle; margin-right: 8px;">
            Admin
        </h1>
        <p>Manage and configure the CO₂ Saver platform</p>
    </div>
    """, unsafe_allow_html=True)

    
    conn = sqlite3.connect('co2_saver.db')
    factors_df = pd.read_sql("SELECT * FROM emission_factors", conn)
    conn.close()
    
    st.info("Update emission factors below. Changes will be saved to the database.")
    
    edited_df = st.data_editor(factors_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Save Changes"):
        try:
            conn = sqlite3.connect('co2_saver.db')
            conn.execute("DELETE FROM emission_factors")
            for _, row in edited_df.iterrows():
                conn.execute("INSERT INTO emission_factors VALUES (?, ?, ?)", 
                           (row['mode'], row['factor'], row['unit']))
            conn.commit()
            conn.close()
            st.success("✅ Emission factors updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving changes: {e}")

def get_last_trip(user_name: str):
    conn = sqlite3.connect('co2_saver.db')
    query = """
        SELECT * FROM trips
        WHERE user_name = ?
        ORDER BY date DESC
        LIMIT 1 OFFSET 1
    """
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

    leaderboard = week_df.groupby("user_name")['co2_saved'].sum().reset_index()
    all_users = df['user_name'].unique()
    leaderboard = leaderboard.set_index("user_name").reindex(all_users, fill_value=0).reset_index()
    leaderboard = leaderboard.sort_values("co2_saved", ascending=False).reset_index(drop=True)
    return leaderboard

def get_leaf_badge(co2_saved_week: float):
    if co2_saved_week >= 20:
        return "🌟 Green Champion", "gold"
    elif co2_saved_week >= 10:
        return "🌿 Silver Saver", "silver"
    elif co2_saved_week >= 5:
        return "🍃 Bronze Beginner", "bronze"
    else:
        return "🌱 Starter Leaf", "starter"

def get_today_stats():
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

import re

# --- This is the NEW chatbot brain ---
def chatbot_response(chat_history):
    """
    Generates a response from the Gemini model based on the chat history.
    """
    # Define the persona and instructions for the model
    system_prompt = """
    You are EcoBot, a friendly and helpful AI assistant for the 'CO₂ Saver' app.
    Your goal is to encourage users to make environmentally friendly travel choices.
    - Be concise and encouraging.
    - Provide practical, actionable tips.
    - If asked about a topic outside of eco-friendly travel, gently guide the conversation back.
    - Use emojis to make the conversation more engaging (e.g., 🌿, 🌍, 🚴, 🚶, 🚌).
    """

    # Format the chat history for the Gemini API
    # The API expects roles 'user' and 'model'
    formatted_history = []
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        formatted_history.append({"role": role, "parts": [msg["content"]]})

    try:
        # Initialize the Gemini model
        # We use gemini-1.5-flash for its speed and capability in chat applications.
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt
        )
        
        # Generate the response
        response = model.generate_content(formatted_history)
        return response.text

    except Exception as e:
        # Handle potential errors (e.g., API key not set, network issues)
        st.error(f"An error occurred with the AI model: {e}")
        return "Sorry, I'm having a little trouble connecting right now. Please try again later."
# -------------------------
# Chatbot UI
# -------------------------

# -------------------------
# Navigation Bar
# -------------------------
def top_nav_bar():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Log Trip", "Dashboard", "History", "Prediction Tool",
                 "Cost Dashboard", "Green Map", "Leaderboard", "Admin"],
        icons=["house", "car-front", "bar-chart", "journal-text", "magic",
               "cash-coin", "map", "trophy", "tools"],
        orientation="horizontal",
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {
                "padding": "10px 20px",
                "background-color": "#1b4332",
                "border-radius": "10px",
                "margin-bottom": "20px",
                "display": "flex",
                "justify-content": "center",
                "align-items": "center",
                "width": "100%",
                "max-width": "1400px",
                "margin-left": "auto",
                "margin-right": "auto",
                "flex-wrap": "nowrap",  # Prevent wrapping to ensure single row
                "overflow-x": "auto",   # Allow horizontal scrolling if needed
                "white-space": "nowrap"
            },
            "nav": {
                "display": "flex",
                "justify-content": "center",
                "align-items": "center",
                "gap": "8px",
                "flex-wrap": "nowrap",  # Prevent wrapping
                "width": "100%"
            },
            "nav-link": {
                "color": "#eee",
                "font-size": "13px",    # Slightly smaller font for better fit
                "font-weight": "bold",
                "padding": "8px 12px",  # Reduced padding for tighter fit
                "white-space": "nowrap",
                "border-radius": "8px",
                "min-width": "auto"
            },
            "nav-link-selected": {
                "background-color": "#40916c",
                "border-radius": "8px"
            },
            "icon": {
                "font-size": "13px",    # Match icon size to text
                "margin-right": "4px"
            }
        }
    )
    st.session_state["app_mode"] = selected
    return selected

# -------------------------
# Main Application
# -------------------------
def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True
        
    if "app_mode" not in st.session_state:
        st.session_state["app_mode"] = "Home"
    if "entered" not in st.session_state:
        st.session_state["entered"] = False

    # Hero section for Home page
    if st.session_state["app_mode"] == "Home":
        st.markdown("""
        <div style="background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80');
                    background-size: cover; background-position: center; padding: 60px 30px; border-radius: 20px; color: white; text-align: center; margin-bottom: 30px; position: relative;">
            <div style="position: relative; z-index: 2;">
                <div style="background: rgba(255,255,255,0.9); padding: 20px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; z-index: 1;">
                    <h1 class="breathe-easy" style="position: relative; z-index: 2; margin: 0;">🌿 Breathe Easy, Travel Green</h1>
                </div>
            </div>
            <p style="font-size: 20px; margin-bottom: 30px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); position: relative; z-index: 2;">Every sustainable journey makes our planet healthier</p>
            <div style="display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; position: relative; z-index: 2;">
                <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <span style="font-size: 24px;">🌳</span>
                    <p>Track Your Impact</p>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <span style="font-size: 24px;">💨</span>
                    <p>Reduce Emissions</p>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <span style="font-size: 24px;">💰</span>
                    <p>Save Money</p>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <span style="font-size: 24px;">🌍</span>
                    <p>Protect Nature</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    app_mode = top_nav_bar()
# --- START: FUNCTIONAL CHATBOT (SIDEBAR VERSION) ---

# Configure the Gemini API key from Streamlit's secrets
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        # This will be triggered if the API key is not set in secrets.toml
        st.error("Please add your Gemini API key to the secrets.toml file.")


    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hi! I'm EcoBot. Ask me anything about sustainable travel! 🌱"
        }]

# Create the chat interface inside the sidebar
    with st.sidebar:
        st.markdown("## EcoBot 🌱")
    
    # Display existing chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Handle new user input at the bottom of the sidebar
        if prompt := st.chat_input("Ask a question..."):
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

        # Generate and display assistant response
            with st.chat_message("assistant"):
                # **MODIFIED LINE:** Pass the entire chat history
                response = chatbot_response(st.session_state.messages) 
                st.markdown(response)
        
        # Add assistant message to history
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to immediately update the chat display
            st.rerun()

# --- END: FUNCTIONAL CHATBOT (SIDEBAR VERSION) ---

    if app_mode == "Home":

        st.markdown("""
        <div class="nature-bg">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f30d.png" 
                    alt="Earth" width="40" style="vertical-align: middle; margin-right: 8px;">
                Welcome to CO₂ Saver
            </h1>
            <h3>Track your carbon footprint and make a difference</h3>
            <p>Every journey counts. Start tracking your trips today and see how much CO₂ you can save!</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🌍 Track Emissions\n\nLog your trips and see your carbon impact in real-time with actionable insights", 
                        use_container_width=True, key="track_emissions"):
                st.session_state["app_mode"] = "Log Trip"
                st.rerun()
        with col2:
            if st.button("💰 Save Money\n\nDiscover how eco-friendly choices can save you money while still being respinsible", 
                        use_container_width=True, key="save_money"):
                st.session_state["app_mode"] = "Cost Dashboard"
                st.rerun()
        with col3:
            if st.button("🏆 Earn Badges\n\nGet recognized for your sustainable transportation choices for a better future", 
                        use_container_width=True, key="earn_badges"):
                st.session_state["app_mode"] = "Leaderboard"
                st.rerun()

    elif app_mode == "Log Trip":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f331.png" 
                    alt="Leaf" width="32" style="vertical-align: middle; margin-right: 8px;">
                Log Your Trip
            </h1>
            <p>Track your transportation and see your CO₂ impact instantly!</p>
        </div>
        """, unsafe_allow_html=True)


        
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
        
        if submitted:
            try:
                co2_emitted, co2_saved, percent_improvement, best_mode, trees_saved = save_trip(
                    user_name, mode, distance, occupancy)
                
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

                st.success("🎉 Here's your Green Receipt!")
                if vs_last_msg:
                    st.info(vs_last_msg)
                
                img_bytes = generate_receipt_image(
                    user_name, mode, distance, co2_emitted, co2_saved, 
                    percent_improvement, best_mode, trees_saved
                )
                
                st.download_button(
                    label="⬇️ Download Receipt as PNG",
                    data=img_bytes,
                    file_name=f"green_receipt_{user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )

                share_text = f"I just saved {co2_saved:.2f} kg CO₂ ({percent_improvement:.1f}% greener) using Green Receipt CO₂ Saver! 🌱🚴‍♂️ #GoGreen"
                encoded_text = urllib.parse.quote(share_text)

                wa_url = f"https://api.whatsapp.com/send?text={encoded_text}"
                twitter_url = f"https://twitter.com/intent/tweet?text={encoded_text}"
                linkedin_url = f"https://www.linkedin.com/shareArticle?mini=true&url=https://example.com&title=Green+Receipt+CO2+Saver&summary={encoded_text}&source=GreenReceipt"

                st.markdown(
                    f"""
                    <h3>Share your achievement:</h3>
                    <div style="display: flex; gap: 20px; align-items: center; margin-top: 15px;">
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
                st.markdown("""
                <div style="background: linear-gradient(rgba(45, 106, 79, 0.1), rgba(45, 106, 79, 0.1)), url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80');
                            background-size: cover; background-position: center; padding: 30px; border-radius: 15px; margin-top: 30px; text-align: center; position: relative;">
                    <div style="background: rgba(255,255,255,0.9); padding: 20px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; z-index: 1;">
                        <h3 style="color: #2d6a4f; margin: 0; position: relative; z-index: 2;">🌍 Every Trip Counts</h3>
                        <p style="position: relative; z-index: 2;">Your sustainable choices today create a greener tomorrow</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                col1.metric("CO₂ Emitted", f"{co2_emitted:.2f} kg", delta=None)
                col2.metric("CO₂ Saved", f"{co2_saved:.2f} kg", delta=f"{percent_improvement:.1f}%")
                col3.metric("Trees Equivalent", f"{trees_saved:.1f} days", delta=None)
                
            except Exception as e:
                st.error(f"Error processing trip: {e}")

    elif app_mode == "Dashboard":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f4ca.png" 
                    alt="Chart" width="32" style="vertical-align: middle; margin-right: 8px;">
                Live Dashboard
            </h1>
            <p>See your environmental impact at a glance</p>
        </div>
        """, unsafe_allow_html=True)

        
        summary = get_dashboard_summary()
        
        if summary['total_trips'] == 0:
            st.info("🚗 No trips recorded yet. Log a trip to see your dashboard!")
            return
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total CO₂ Emitted", f"{summary['total_emitted']:.1f} kg")
        col2.metric("Total CO₂ Saved", f"{summary['total_saved']:.1f} kg")
        col3.metric("Total Trips", summary['total_trips'])
        
        today_emitted, today_saved = get_today_stats()
        trips = get_all_trips()
        if trips.empty:
            user_list = ["Anonymous"]
        else:
            user_list = sorted(trips["user_name"].unique())

        user = st.selectbox("Select a user", user_list)
        weekly_emitted, weekly_saved = get_user_weekly_stats(user)
        badge_name, _ = get_leaf_badge(weekly_saved)

        st.subheader(f"🌿 Weekly Progress for {user}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Today’s CO₂ Emitted", f"{today_emitted:.1f} kg")
        col2.metric("Today’s CO₂ Saved", f"{today_saved:.1f} kg")
        col1.metric("This Week CO₂ Emitted", f"{weekly_emitted:.1f} kg")
        col2.metric("This Week CO₂ Saved", f"{weekly_saved:.1f} kg")
        col3.metric("Your Badge", badge_name)

        st.markdown("""
<div style="display: flex; justify-content: space-between; margin: 30px 0; gap: 20px;">
    <div style="flex: 1; text-align: center;">
        <div style="width: 100%; height: 200px; overflow: hidden; border-radius: 15px; background: #e8f5e8; display: flex; align-items: center; justify-content: center;">
            <img src="data:image/jpeg;base64,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"
                style="width: 100%; height: 100%; object-fit: cover;">
        </div>
        <p style="margin-top: 10px; font-weight: bold; color: #2d6a4f;">🌳 Trees Saved</p>
    </div>
    <div style="flex: 1; text-align: center;">
        <div style="width: 100%; height: 200px; overflow: hidden; border-radius: 15px; background: #e8f5e8; display: flex; align-items: center; justify-content: center;">
            <img src="https://images.ctfassets.net/yixw23k2v6vo/38kQUkLmmbHBSTcNGsie5p/49a9f812f3660f2056d9815bd82ccb4d/iStock-1269532812.jpg" 
                 style="width: 100%; height: 100%; object-fit: cover;">
        </div>
        <p style="margin-top: 10px; font-weight: bold; color: #2d6a4f;">💨 CO₂ Reduced</p>
    </div>
    <div style="flex: 1; text-align: center;">
        <div style="width: 100%; height: 200px; overflow: hidden; border-radius: 15px; background: #e8f5e8; display: flex; align-items: center; justify-content: center;">
            <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRpyYxL8jG_0E775dxrMx9TRqAt9gX05z3XoA&s" 
                 style="width: 100%; height: 100%; object-fit: cover;">
        </div>
        <p style="margin-top: 10px; font-weight: bold; color: #2d6a4f;">🚴 Green Travel</p>
    </div>
</div>
        """, unsafe_allow_html=True)


        goal = 20
        progress = min(100, (weekly_saved / goal) * 100)
        st.progress(progress / 100)
        st.caption(f"Progress to Green Champion: {weekly_saved:.1f} / {goal} kg saved")

        st.subheader("🏆 Global Weekly Leaderboard")
        leaderboard = get_weekly_leaderboard()
        if leaderboard.empty:
            st.info("No trips recorded this week yet!")
        else:
            st.dataframe(leaderboard, use_container_width=True)

        if not summary['mode_dist'].empty:
            st.subheader("🚦 Transport Mode Distribution")
            fig = px.pie(summary['mode_dist'], names='mode', values='count', 
                         title="Breakdown of Transport Modes Used",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)

    elif app_mode == "History":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f4d3.png" 
                    alt="Notebook" width="32" style="vertical-align: middle; margin-right: 8px;">
                History
            </h1>
            <p>View your past trips and saved CO₂ impact records</p>
        </div>
        """, unsafe_allow_html=True)

        
        trips = get_all_trips()
        if trips.empty:
            st.info("No trips recorded yet. Log a trip to see your history!")
        else:
            st.dataframe(trips, use_container_width=True)
            
            fig = px.scatter(trips, x='date', y='co2_saved', color='mode', size='distance',
                             title="CO₂ Savings Over Time", hover_data=['user_name', 'distance'])
            st.plotly_chart(fig, use_container_width=True)

    elif app_mode == "Prediction Tool":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f52e.png" 
                    alt="Crystal Ball" width="32" style="vertical-align: middle; margin-right: 8px;">
                Prediction Tool
            </h1>
            <p>Estimate your future CO₂ footprint and plan ahead</p>
        </div>
        """, unsafe_allow_html=True)

        
        col1, col2 = st.columns(2)
        with col1:
            current_mode = st.selectbox("Current Transport Mode", 
                ["Petrol Car", "Diesel Car", "CNG Auto", "Bus", "Metro", "EV Car", "Cycle", "Walk"])
            new_mode = st.selectbox("New Transport Mode", 
                ["Petrol Car", "Diesel Car", "CNG Auto", "Bus", "Metro", "EV Car", "Cycle", "Walk"])
        with col2:
            trips_per_week = st.number_input("Trips per Week", min_value=1, max_value=50, value=5)
            distance_per_trip = st.number_input("Distance per Trip (km)", min_value=0.1, max_value=1000.0, value=5.0)
        
        if st.button("Calculate Savings", use_container_width=True):
            weekly_savings, annual_savings, trees_saved = predict_savings(
                current_mode, new_mode, trips_per_week, distance_per_trip)
            st.success(f"By switching to {new_mode}, you could save:")
            col1, col2, col3 = st.columns(3)
            col1.metric("Weekly CO₂ Savings", f"{weekly_savings:.2f} kg")
            col2.metric("Annual CO₂ Savings", f"{annual_savings:.2f} kg")
            col3.metric("Trees Saved per Year", f"{trees_saved:.1f}")

    elif app_mode == "Cost Dashboard":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f4b0.png" 
                    alt="Money" width="32" style="vertical-align: middle; margin-right: 8px;">
                Cost Dashboard
            </h1>
            <p>Discover how eco-friendly choices can save you money</p>
        </div>
        """, unsafe_allow_html=True)

        cost_dashboard()

    elif app_mode == "Green Map":

        green_map()

    elif app_mode == "Leaderboard":
        st.markdown("""
        <div class="card">
            <h1>
                <img src="https://twemoji.maxcdn.com/v/latest/72x72/1f3c6.png" 
                    alt="Trophy" width="32" style="vertical-align: middle; margin-right: 8px;">
                Leaderboard
            </h1>
            <p>Get recognized for your sustainable transportation choices</p>
        </div>
        """, unsafe_allow_html=True)

        
        st.subheader("Global Leaderboard")
        global_leaderboard = get_global_leaderboard()
        if global_leaderboard.empty:
            st.info("No trips recorded yet!")
        else:
            st.dataframe(global_leaderboard, use_container_width=True)

    elif app_mode == "Admin":
        admin_page()

if __name__ == "__main__":
    main()