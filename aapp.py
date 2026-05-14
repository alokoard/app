import streamlit as st
import pandas as pd
import numpy as np

# --- Sidinställningar ---
st.set_page_config(page_title="Ruttplanerare Pro - Tvätteri", layout="wide")
st.title("🚛 Ruttplanerare Pro: Massplanering & Karta")

# --- Logik för ruttberäkning ---
def calculate_routes(stops, vehicle_caps):
    remaining = stops.copy()
    all_routes = []
    
    for cap in vehicle_caps:
        if not remaining: break
        current_route = []
        current_load = 0
        # Startposition (Tvätteriet - Göteborg Centrum ca)
        curr_lat, curr_lon = 57.7089, 11.9746 
        
        while remaining:
            # Hitta närmsta stopp
            dists = [np.sqrt((s['lat']-curr_lat)**2 + (s['lon']-curr_lon)**2) for s in remaining]
            nearest_idx = np.argmin(dists)
            nearest_stop = remaining[nearest_idx]
            
            if current_load + nearest_stop['demand'] <= cap:
                current_route.append(nearest_stop)
                current_load += nearest_stop['demand']
                curr_lat, curr_lon = nearest_stop['lat'], nearest_stop['lon']
                remaining.pop(nearest_idx)
            else:
                break
        all_routes.append(current_route)
    return all_routes, remaining

# --- Sidebar: Fordon ---
st.sidebar.header("🚚 Fordonsflotta")
stora = st.sidebar.number_input("Lastbilar (12 vagnar)", 0, 10, 2)
sma = st.sidebar.number_input("Lätta lastbilar (6 vagnar)", 0, 10, 1)
v_caps = ([12] * stora) + ([6] * sma)

# --- Huvudfönster: Massinmatning ---
st.subheader("1. Klistra in adresser")
st.info("Format: Namn, Ut, In (en per rad). Exempel: Hotell Gothia, 5, 5")
bulk_input = st.text_area("Adresslista", height=200, placeholder="Gothia Towers, 5, 5\nRestaurang Linné, 2, 2\nSahlgrenska, 10, 8")

if st.button("🚀 Planera och optimera rutter", type="primary"):
    if bulk_input:
        processed_stops = []
        lines = bulk_input.split('\n')
        
        for i, line in enumerate(lines):
            if ',' in line:
                parts = line.split(',')
                try:
                    name = parts[0].strip()
                    out_v = int(parts[1].strip())
                    in_v = int(parts[2].strip())
                    # Slumpa koordinater runt Gbg för kartan
                    lat = 57.70 + np.random.uniform(-0.05, 0.05)
                    lon = 11.97 + np.random.uniform(-0.05, 0.05)
                    processed_stops.append({"name": name, "demand": max(out_v, in_v), "lat": lat, "lon": lon})
                except:
                    st.error(f"Kunde inte läsa rad: {line}")

        if processed_stops:
            routes, left_over = calculate_routes(processed_stops, v_caps)
            
            # --- VISUALISERING: KARTA ---
            st.subheader("2. Kartöversikt")
            map_data = []
            for i, r in enumerate(routes):
                for stop in r:
                    map_data.append({"lat": stop['lat'], "lon": stop['lon'], "Bil": f"Bil {i+1}"})
            
            if map_data:
                df_map = pd.DataFrame(map_data)
                st.map(df_map, color="#FF4B4B" if len(routes) > 0 else "#000000")
            
            # --- KÖRLISTOR ---
            st.subheader("3. Färdiga Körlistor")
            cols = st.columns(len([r for r in routes if r]))
            
            for i, r in enumerate(routes):
                if not r: continue
                with cols[i % len(cols)]:
                    st.success(f"**BIL {i+1} ({'Stor' if v_caps[i]==12 else 'Liten'})**")
                    st.write("📍 *Start: Tvätteriet*")
                    for j, s in enumerate(r):
                        st.write(f"{j+1}. **{s['name']}** ({s['demand']} vagn)")
                    st.write("🏁 *Mål: Tvätteriet*")
                    
                    # SMS-knapp/text
                    sms_list = [s['name'] for s in r]
                    st.text_area(f"Kopiera SMS Bil {i+1}", f"RUTT BIL {i+1}: Start -> " + " -> ".join(sms_list) + " -> Mål", height=100)
            
            if left_over:
                st.warning(f"⚠️ {len(left_over)} stopp fick inte plats! Lägg till fler bilar.")
    else:
        st.error("Klistra in adresser först!")

# --- VIKTIGT FÖR ATT DET SKA FUNKA ---
# Se till att din requirements.txt bara innehåller:
# streamlit
# pandas
# numpy
