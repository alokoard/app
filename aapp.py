import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time
import re

# Inställningar
st.set_page_config(page_title="Ruttplanerare Pro", layout="wide")
st.title("🚛 Ruttplanerare: Adresser & Koordinater")

# Fixa geokodning
geolocator = Nominatim(user_agent="textilia_gbg_v3")

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
**Du kan skriva på tre sätt:**
1. Vanlig adress: `Storgatan 1 - 5`
2. Koordinater: `57.70, 11.97 - 2`
3. Namn & Koordinat: `Kundnamn: 57.70, 11.97 - 3`
*(Använd **!** först för att prioritera)*
""")

bulk_input = st.text_area("Klistra in din lista här", height=250)

def extract_coords(text):
    """Kollar om texten innehåller lat, lon"""
    match = re.search(r"(\d+\.\d+),\s*(\d+\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None

if st.button("🚀 Planera rutter", type="primary"):
    if bulk_input:
        stopp = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        
        progress_bar = st.progress(0)
        
        for idx, rad in enumerate(rader):
            is_prio = rad.startswith('!')
            rensad_rad = rad.replace('!', '').strip()
            
            # 1. Kolla antal vagnar (efter bindestreck)
            vagnar = 1
            huvud_del = rensad_rad
            if " - " in rensad_rad:
                try:
                    huvud_del, vagn_str = rensad_rad.rsplit(" - ", 1)
                    vagnar = int(vagn_str.strip())
                except: pass

            # 2. Kolla efter koordinater i texten
            coords = extract_coords(huvud_del)
            
            namn_display = huvud_del
            lat, lon = None, None

            if coords:
                lat, lon = coords
                # Om det finns ett namn före koordinaterna (t.ex. Kund: 57.7, 11.9)
                if ":" in huvud_del:
                    namn_display = huvud_del.split(":")[0].strip()
            else:
                # 3. Om inga koordinater finns, sök med Geopy
                try:
                    sok_term = huvud_del if "göteborg" in huvud_del.lower() else f"{huvud_del}, Göteborg"
                    location = geolocator.geocode(sok_term, timeout=10)
                    if location:
                        lat, lon = location.latitude, location.longitude
                    time.sleep(0.7) # För att inte bli bannad från karttjänsten
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
                st.error(f"❌ Kunde inte hitta: {huvud_del}")
            
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
            cols = st.columns(len(rutter))
            for i, (bil_namn, s_lista) in enumerate(rutter.items()):
                with cols[i]:
                    st.success(f"**{bil_namn.upper()}**")
                    if not s_lista:
                        st.write("Inga stopp.")
                    else:
                        for j, s in enumerate(s_lista):
                            prio_icon = "⭐ " if s['prio'] else ""
                            st.write(f"{j+1}. {prio_icon}{s['namn']} ({s['vagnar']} st)")
                        
                        # SMS-format
                        sms_text = f"{bil_namn}:\n" + "\n".join([f"{n+1}. {'(PRIO) ' if s['prio'] else ''}{s['namn']} - vagnar: {s['vagnar']}" for n, s in enumerate(s_lista)])
                        st.text_area("Kopiera SMS:", sms_text, height=120, key=f"sms_{i}")

            if sorterade_stopp:
                st.warning(f"⚠️ {len(sorterade_stopp)} adresser fick inte plats.")
    else:
        st.warning("Skriv in adresser eller koordinater!")
