import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time

# Inställningar
st.set_page_config(page_title="Ruttplanerare Pro", layout="wide")
st.title("🚛 Ruttplanerare med Prioritering")

# Fixa geokodning
geolocator = Nominatim(user_agent="textilia_gbg_v2")

# --- 1. Fordonsinställningar ---
st.sidebar.header("🚚 Dina Fordon")
antal_bilar = st.sidebar.number_input("Antal bilar", 1, 10, 2)
fordons_data = []
for i in range(int(antal_bilar)):
    # Unikt ID för varje input-ruta (fixar DuplicateElementKey)
    cap = st.sidebar.number_input(f"Kapacitet bil {i+1}", 1, 100, 10, key=f"bil_cap_input_{i}")
    fordons_data.append({"id": i+1, "cap": cap})

# --- 2. Inmatning ---
st.subheader("📍 Adresslista")
st.info("""
**Format:** Adress - Antal  
**Prioritera:** Lägg till ett **!** först på raden för att sätta stoppet först i kön.
*Exempel:* `! Västra Hamngatan 20 - 5` (Körs först)  
`Drottninggatan 5 - 2` (Körs efter prio)
""")

bulk_input = st.text_area("Klistra in adresser här", height=200)

if st.button("🚀 Planera rutter", type="primary"):
    if bulk_input:
        stopp = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        
        progress_bar = st.progress(0)
        
        for idx, rad in enumerate(rader):
            # Kolla prioritering
            is_prio = False
            rensad_rad = rad
            if rad.startswith('!'):
                is_prio = True
                rensad_rad = rad.replace('!', '').strip()
            
            # Parsing av antal
            namn = rensad_rad
            vagnar = 1
            if " - " in rensad_rad:
                try:
                    delar = rensad_rad.split(" - ")
                    namn = delar[0].strip()
                    vagnar = int(delar[1].strip())
                except: pass

            try:
                # Geokodning
                sok_term = namn if "göteborg" in namn.lower() else f"{namn}, Göteborg"
                location = geolocator.geocode(sok_term, timeout=10)
                
                if location:
                    stopp.append({
                        "namn": namn,
                        "vagnar": vagnar,
                        "prio": is_prio,
                        "lat": location.latitude,
                        "lon": location.longitude
                    })
                else:
                    st.error(f"Hittade inte: {namn}")
                
                time.sleep(0.8) # Paus för att inte bli blockerad av karttjänsten
            except Exception as e:
                st.error(f"Fel vid {namn}: {e}")
            
            progress_bar.progress((idx + 1) / len(rader))

        if stopp:
            # --- RUTT-LOGIK MED PRIORITERING ---
            # Vi sorterar så att alla med prio=True kommer först
            sorterade_stopp = sorted(stopp, key=lambda x: x['prio'], reverse=True)
            
            rutter = {f"Bil {f['id']}": [] for f in fordons_data}
            
            for bil in fordons_data:
                nuvarande_last = 0
                temp_stopp = sorterade_stopp.copy()
                for s in temp_stopp:
                    if nuvarande_last + s['vagnar'] <= bil['cap']:
                        rutter[f"Bil {bil['id']}"].append(s)
                        nuvarande_last += s['vagnar']
                        sorterade_stopp.remove(s)
            
            # --- Visa Karta ---
            st.subheader("🗺️ Kartöversikt")
            map_points = []
            for bil_namn, s_lista in rutter.items():
                for s in s_lista:
                    map_points.append({"lat": s['lat'], "lon": s['lon'], "Bil": bil_namn})
            if map_points:
                st.map(pd.DataFrame(map_points))

            # --- Visa Körlistor ---
            st.subheader("📋 Körlistor")
            cols = st.columns(len(rutter))
            for i, (bil_namn, s_lista) in enumerate(rutter.items()):
                with cols[i]:
                    st.success(f"**{bil_namn.upper()}**")
                    if not s_lista:
                        st.write("Inga stopp.")
                    else:
                        for j, s in enumerate(s_lista):
                            prio_mark = "⭐ **PRIO** -" if s['prio'] else ""
                            st.write(f"{j+1}. {prio_mark} {s['namn']} ({s['vagnar']} st)")
                        
                        # SMS-text (Här är key fixad så den är unik)
                        txt = f"{bil_namn}:\n" + "\n".join([f"{j+1}. {'(PRIO) ' if s['prio'] else ''}{s['namn']}" for j, s in enumerate(s_lista)])
                        st.text_area("Kopiera SMS:", txt, height=100, key=f"sms_output_{i}")

            if sorterade_stopp:
                st.warning(f"⚠️ {len(sorterade_stopp)} adresser fick inte plats.")
    else:
        st.warning("Skriv in adresser!")
