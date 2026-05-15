import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time
import re

# Inställningar
st.set_page_config(page_title="Ruttplanerare Pro", layout="wide")
st.title("🚛 Ruttplanerare: För alla adresser")

# Fixa geokodning - vi lägger till ett unikt namn för att undvika blockering
geolocator = Nominatim(user_agent="textilia_logistik_system_v4")

# --- 1. Fordonsinställningar ---
st.sidebar.header("🚚 Dina Fordon")
antal_bilar = st.sidebar.number_input("Antal bilar", 1, 10, 2)
fordons_data = []
for i in range(int(antal_bilar)):
    cap = st.sidebar.number_input(f"Kapacitet bil {i+1}", 1, 100, 10, key=f"v_cap_{i}")
    fordons_data.append({"id": i+1, "cap": cap})

# --- 2. Inmatning ---
st.subheader("📍 Lägg till stopp")
st.info("""
**Tips för att det ska fungera varje gång:**
* Skriv adressen så komplett du kan: `Fibervägen 7, Mölnlycke`
* För antal vagnar, använd bindestreck: `Adress - 5`
* För prio, använd utropstecken: `! Adress - 2`
""")

bulk_input = st.text_area("Klistra in din lista här (t.ex. från Excel eller anteckningar)", height=250)

def extract_coords(text):
    match = re.search(r"(\d+\.\d+),\s*(\d+\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None

if st.button("🚀 Beräkna rutter", type="primary"):
    if bulk_input:
        stopp = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, rad in enumerate(rader):
            is_prio = rad.startswith('!')
            rensad_rad = rad.replace('!', '').strip()
            
            # 1. Antal vagnar
            vagnar = 1
            huvud_del = rensad_rad
            if " - " in rensad_rad:
                try:
                    huvud_del, vagn_str = rensad_rad.rsplit(" - ", 1)
                    vagnar = int(vagn_str.strip())
                except: pass

            # 2. Kolla koordinater
            coords = extract_coords(huvud_del)
            lat, lon = None, None
            namn_display = huvud_del

            if coords:
                lat, lon = coords
                if ":" in huvud_del:
                    namn_display = huvud_del.split(":")[0].strip()
            else:
                # 3. Förbättrad sökning för adresser
                try:
                    # Vi lägger till ", Sweden" istället för ", Göteborg" 
                    # då hittar den även Mölnlycke, Landvetter etc.
                    sok_term = f"{huvud_del}, Sweden"
                    location = geolocator.geocode(sok_term, timeout=10)
                    
                    if location:
                        lat, lon = location.latitude, location.longitude
                    
                    # Vi ökar pausen till 1.1 sekunder för att vara snälla mot servern
                    # Detta minskar risken för "Hittade inte"-fel
                    time.sleep(1.1) 
                except: pass

            if lat and lon:
                stopp.append({
                    "namn": namn_display,
                    "vagnar": vagnar,
                    "prio": is_prio,
                    "lat": lat,
                    "lon": lon
                })
            else:
                st.error(f"❌ Kunde inte hitta: {huvud_del}. Kontrollera stavning eller lägg till ortnamn.")
            
            progress_bar.progress((idx + 1) / len(rader))

        if stopp:
            # --- RUTT-LOGIK ---
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
            
            # --- Karta ---
            st.subheader("🗺️ Kartöversikt")
            map_df = pd.DataFrame([{"lat": s['lat'], "lon": s['lon'], "Bil": b} 
                                 for b, lista in rutter.items() for s in lista])
            if not map_df.empty:
                st.map(map_df)

            # --- Körlistor ---
            st.subheader("📋 Körlistor")
            cols = st.columns(len([r for r in rutter.values() if r]) or 1)
            for i, (bil_namn, s_lista) in enumerate(rutter.items()):
                if not s_lista: continue
                with cols[i % len(cols)]:
                    st.success(f"**{bil_namn.upper()}**")
                    for j, s in enumerate(s_lista):
                        prio_icon = "⭐ " if s['prio'] else ""
                        st.write(f"{j+1}. {prio_icon}{s['namn']} ({s['vagnar']} st)")
                    
                    sms_text = f"{bil_namn}:\n" + "\n".join([f"{n+1}. {s['namn']} ({s['vagnar']} st)" for n, s in enumerate(s_lista)])
                    st.text_area("Kopiera rutt:", sms_text, height=120, key=f"sms_key_{i}")

            if sorterade_stopp:
                st.warning(f"⚠️ {len(sorterade_stopp)} adresser fick inte plats.")
    else:
        st.warning("Klistra in adresser!")
