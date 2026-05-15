import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import time
import re

# Inställningar
st.set_page_config(page_title="Textilia Logistikplanering", layout="wide")
st.title("🚛 Ruttplanering: Rena & Smutsiga Vagnar")

# Fixa geokodning
geolocator = Nominatim(user_agent="textilia_gbg_v5")

# --- 1. Fordonsinställningar ---
st.sidebar.header("🚚 Dina Bilar")
antal_bilar = st.sidebar.number_input("Antal bilar i drift", 1, 10, 2)
fordons_data = []
for i in range(int(antal_bilar)):
    col1, col2 = st.sidebar.columns(2)
    namn = col1.text_input(f"Namn bil {i+1}", f"Bil {i+1}", key=f"n_{i}")
    cap = col2.number_input(f"Kapacitet", 1, 50, 12, key=f"c_{i}")
    fordons_data.append({"namn": namn, "cap": cap})

# --- 2. Inmatning ---
st.subheader("📍 Dagens körningar")
st.info("""
**Format:** `Adress - Rena, Smuts`  
*Exempel:* `Fibervägen 7, Mölnlycke - 5, 4` (Lämna 5 rena, hämta 4 smutsiga)  
*(Använd **!** först för prioritering)*
""")

bulk_input = st.text_area("Klistra in adresser här", height=200, placeholder="Spinnerivägen 1, Tollered - 2, 2\n! Metallvägen 6, Mölnlycke - 6, 6")

def extract_vagnar(text):
    # Letar efter formatet "- siffra, siffra"
    match = re.search(r"-\s*(\d+)\s*,\s*(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1, 1 # Standard om inget anges

if st.button("🚀 Optimera körschema", type="primary"):
    if bulk_input:
        stopp_lista = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        
        progress_bar = st.progress(0)
        
        for idx, rad in enumerate(rader):
            is_prio = rad.startswith('!')
            rensad_rad = rad.replace('!', '').strip()
            
            # Dela upp adress och vagnar
            rena, smuts = extract_vagnar(rensad_rad)
            adress_del = rensad_rad.split(" - ")[0].strip()

            try:
                # Sök adress (lägger till Sweden för Landvetter/Mölnlycke osv)
                sok_term = f"{adress_del}, Sweden"
                location = geolocator.geocode(sok_term, timeout=10)
                
                if location:
                    stopp_lista.append({
                        "namn": adress_del,
                        "rena": rena,
                        "smuts": smuts,
                        "prio": is_prio,
                        "lat": location.latitude,
                        "lon": location.longitude
                    })
                else:
                    st.error(f"❌ Hittade inte: {adress_del}")
                
                time.sleep(1.1) # Viktig paus
            except: pass
            
            progress_bar.progress((idx + 1) / len(rader))

        if stopp_lista:
            # Sortera: Prio först
            sorterade = sorted(stopp_lista, key=lambda x: x['prio'], reverse=True)
            rutter = {f["namn"]: [] for f in fordons_data}
            
            # Fördela på bilar
            for bil in fordons_data:
                # Logik: En bil börjar full med alla rena vagnar som ska ut
                nuvarande_i_bil = 0 
                # Vi testar att lägga till stopp så länge max-kapaciteten inte överskrids
                temp_lista = sorterade.copy()
                for s in temp_lista:
                    # Vi kollar om bilen någonsin blir för full
                    # (Detta är en enkel modell som kollar totala vagnar vid stoppet)
                    if nuvarande_i_bil + max(s['rena'], s['smuts']) <= bil['cap']:
                        rutter[bil['namn']].append(s)
                        sorterade.remove(s)
            
            # --- Resultat ---
            st.subheader("🗺️ Kartöversikt")
            map_points = []
            for b_namn, s_lista in rutter.items():
                for s in s_lista:
                    map_points.append({"lat": s['lat'], "lon": s['lon'], "Bil": b_namn})
            if map_points:
                st.map(pd.DataFrame(map_points))

            st.subheader("📋 Körscheman för chaufförer")
            cols = st.columns(len([r for r in rutter.values() if r]) or 1)
            
            for i, (b_namn, s_lista) in enumerate(rutter.items()):
                if not s_lista: continue
                with cols[i % len(cols)]:
                    st.success(f"**{b_namn.upper()}** (Kapacitet: {fordons_data[i]['cap']})")
                    
                    total_rena = sum(s['rena'] for s in s_lista)
                    st.write(f"📦 **Lasta på tvätteri:** {total_rena} rena vagnar")
                    
                    for j, s in enumerate(s_lista):
                        p_mark = "⭐ " if s['prio'] else ""
                        st.info(f"**{j+1}. {p_mark}{s['namn']}**\n\n⬇️ Lämna: {s['rena']} rena  \n⬆️ Hämta: {s['smuts']} smuts")
                    
                    # SMS Format
                    sms = f"KÖRNING {b_namn}\nLasta {total_rena} rena.\n"
                    for n, s in enumerate(s_lista):
                        sms += f"\n{n+1}. {s['namn']}\nUT: {s['rena']}, IN: {s['smuts']}"
                    
                    st.text_area("Kopiera rutt:", sms, height=150, key=f"sms_{i}")

            if sorterade:
                st.warning(f"⚠️ {len(sorterade)} stopp fick inte plats. Du behöver fler bilar!")
