import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time

# Inställningar
st.set_page_config(page_title="Ruttplanerare Göteborg", layout="wide")
st.title("🚛 Smart Ruttplanerare (Göteborg)")

# Fixa geokodning (för att hitta adresser på kartan)
geolocator = Nominatim(user_agent="textilia_gbg_app")

# --- 1. Fordonsinställningar ---
st.sidebar.header("🚚 Dina Fordon")
antal_bilar = st.sidebar.number_input("Antal bilar", 1, 10, 2)
fordons_data = []
for i in range(int(antal_bilar)):
    cap = st.sidebar.number_input(f"Kapacitet bil {i+1}", 1, 50, 10, key=f"c_{i}")
    fordons_data.append({"id": i+1, "cap": cap})

# --- 2. Inmatning ---
st.subheader("📍 Skriv eller klistra in adresser")
st.info("Skriv adressen först. Om du vill ha fler än 1 vagn, avsluta med ett bindestreck och siffra. \n\n**Exempel:** \n* Västra Hamngatan 20, Göteborg \n* Drottninggatan 5, Göteborg - 4")

bulk_input = st.text_area("Adresslista (en per rad)", height=150)

if st.button("🚀 Beräkna rutter och visa karta", type="primary"):
    if bulk_input:
        stopp = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, rad in enumerate(rader):
            status_text.text(f"Hittar adress {idx+1} av {len(rader)}...")
            
            # Smart parsing: Kolla om det finns ett antal sist (t.ex. - 5)
            namn = rad
            vagnar = 1
            if " - " in rad:
                try:
                    delar = rad.split(" - ")
                    namn = delar[0].strip()
                    vagnar = int(delar[1].strip())
                except: pass

            try:
                # Sök efter adressen på kartan
                # Vi lägger till "Göteborg" automatiskt om det saknas för bättre träffar
                sok_term = namn if "göteborg" in namn.lower() else f"{namn}, Göteborg"
                location = geolocator.geocode(sok_term, timeout=10)
                
                if location:
                    stopp.append({
                        "namn": namn,
                        "vagnar": vagnar,
                        "lat": location.latitude,
                        "lon": location.longitude
                    })
                else:
                    st.error(f"Kunde inte hitta adressen på kartan: {namn}")
                
                # Nominatim kräver en liten paus mellan sökningar (viktigt!)
                time.sleep(1) 
            except Exception as e:
                st.error(f"Fel vid sökning av {namn}: {e}")
            
            progress_bar.progress((idx + 1) / len(rader))

        if stopp:
            # --- Ruttlogik (Enkel sortering baserat på avstånd) ---
            sorterade_stopp = stopp.copy()
            rutter = {f"Bil {f['id']}": [] for f in fordons_data}
            
            for bil in fordons_data:
                nuvarande_last = 0
                while sorterade_stopp:
                    nasta = sorterade_stopp[0]
                    if nuvarande_last + nasta['vagnar'] <= bil['cap']:
                        rutter[f"Bil {bil['id']}"].append(nasta)
                        nuvarande_last += nasta['vagnar']
                        sorterade_stopp.pop(0)
                    else:
                        break
            
            # --- Visa Karta ---
            st.subheader("🗺️ Körschema på karta")
            map_points = []
            for bil_namn, s_lista in rutter.items():
                for s in s_lista:
                    map_points.append({"lat": s['lat'], "lon": s['lon'], "Bil": bil_namn})
            
            if map_points:
                st.map(pd.DataFrame(map_points))

            # --- Visa Körlistor ---
            st.subheader("📋 Körlistor till chaufförer")
            cols = st.columns(len(rutter))
            for i, (bil_namn, s_lista) in enumerate(rutter.items()):
                with cols[i]:
                    st.success(f"**{bil_namn.upper()}** (Max {fordons_data[i]['cap']} vagnar)")
                    if not s_lista:
                        st.write("Inga stopp.")
                    else:
                        for j, s in enumerate(s_lista):
                            st.write(f"{j+1}. **{s['namn']}** ({s['vagnar']} st)")
                        
                        txt = f"KÖRNING {bil_namn}:\n" + "\n".join([f"{j+1}. {s['namn']} ({s['vagnar']} st)" for j, s in enumerate(s_lista)])
                        st.text_area("Kopiera till SMS:", txt, height=100, key=f"c_{i}")

            if sorterade_stopp:
                st.warning(f"⚠️ {len(sorterade_stopp)} adresser fick inte plats. Du behöver fler bilar!")
    else:
        st.warning("Skriv in minst en adress!")
