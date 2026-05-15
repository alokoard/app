import streamlit as st
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import time
import re

# Inställningar
st.set_page_config(page_title="Textilia Logistik & Tid", layout="wide")
st.title("Planning 2.0: Rutter, Last & Arbetstider")

# Fixa geokodning
geolocator = Nominatim(user_agent="textilia_gbg_v6")

# --- 1. FORDONS- OCH TIDSINSTÄLLNINGAR ---
st.sidebar.header("⚙️ Inställningar")

# Arbetstider
start_pass = st.sidebar.time_input("Passet startar", datetime.strptime("06:45", "%H:%M").time())
slut_pass = st.sidebar.time_input("Passet slutar", datetime.strptime("15:30", "%H:%M").time())
stopp_tid = st.sidebar.number_input("Minuter per stopp (lastning)", min_value=5, value=15)
snitthastighet = st.sidebar.slider("Snitthastighet (km/h i stan)", 20, 60, 40)

st.sidebar.divider()

antal_bilar = st.sidebar.number_input("Antal bilar", 1, 10, 2)
fordons_data = []
for i in range(int(antal_bilar)):
    col1, col2 = st.sidebar.columns(2)
    namn = col1.text_input(f"Bil {i+1}", f"Bil {i+1}", key=f"n_{i}")
    cap = col2.number_input(f"Kapacitet", 1, 50, 12, key=f"c_{i}")
    fordons_data.append({"namn": namn, "cap": cap})

# --- 2. INMATNING ---
st.subheader("📍 Dagens körningar")
st.info("Format: `Adress - Rena, Smuts` (Använd **!** för prio)")
bulk_input = st.text_area("Klistra in adresser här", height=150)

def extract_vagnar(text):
    match = re.search(r"-\s*(\d+)\s*,\s*(\d+)", text)
    if match: return int(match.group(1)), int(match.group(2))
    return 1, 1

if st.button("🚀 Optimera körschema & tider", type="primary"):
    if bulk_input:
        stopp_lista = []
        rader = [r.strip() for r in bulk_input.split('\n') if r.strip()]
        progress = st.progress(0)
        
        for idx, rad in enumerate(rader):
            is_prio = rad.startswith('!')
            rensad = rad.replace('!', '').strip()
            rena, smuts = extract_vagnar(rensad)
            adress = rensad.split(" - ")[0].strip()

            try:
                location = geolocator.geocode(f"{adress}, Sweden", timeout=10)
                if location:
                    stopp_lista.append({
                        "namn": adress, "rena": rena, "smuts": smuts, "prio": is_prio,
                        "lat": location.latitude, "lon": location.longitude
                    })
                time.sleep(1.1)
            except: st.error(f"Kunde inte hitta: {adress}")
            progress.progress((idx + 1) / len(rader))

        if stopp_lista:
            # Sortera prio
            sorterade = sorted(stopp_lista, key=lambda x: x['prio'], reverse=True)
            rutter = {f["namn"]: [] for f in fordons_data}
            
            # Fördela på bilar
            for bil in fordons_data:
                last = 0
                temp = sorterade.copy()
                for s in temp:
                    if last + max(s['rena'], s['smuts']) <= bil['cap']:
                        rutter[bil['namn']].append(s)
                        sorterade.remove(s)

            # --- TIDSKALKYLATOR ---
            st.subheader("📋 Optimerade körlistor med tider")
            cols = st.columns(len([r for r in rutter.values() if r]) or 1)
            
            for i, (b_namn, s_lista) in enumerate(rutter.items()):
                if not s_lista: continue
                with cols[i % len(cols)]:
                    st.success(f"**{b_namn.upper()}**")
                    
                    # Starttid
                    nuvarande_tid = datetime.combine(datetime.today(), start_pass)
                    last_lat, last_lon = 57.7089, 11.9746 # Tvätteriet Gbg
                    
                    st.write(f"🕘 **Start Tvätteri:** {nuvarande_tid.strftime('%H:%M')}")
                    st.write(f"📦 **Lasta:** {sum(s['rena'] for s in s_lista)} st")
                    st.divider()

                    for j, s in enumerate(s_lista):
                        # Beräkna körtid (Haversine för enkelhet)
                        dist = np.sqrt((s['lat']-last_lat)**2 + (s['lon']-last_lon)**2) * 111 # ca km
                        kor_minuter = (dist / snitthastighet) * 60
                        
                        ankomst = nuvarande_tid + timedelta(minutes=kor_minuter)
                        avgång = ankomst + timedelta(minutes=stopp_tid)
                        
                        p_mark = "⭐ " if s['prio'] else ""
                        st.markdown(f"**{j+1}. {p_mark}{s['namn']}**")
                        st.caption(f"Ankomst ca: **{ankomst.strftime('%H:%M')}**")
                        st.write(f"UT: {s['rena']}, IN: {s['smuts']}")
                        
                        nuvarande_tid = avgång
                        last_lat, last_lon = s['lat'], s['lon']

                    # Retur till tvätteri
                    dist_hem = np.sqrt((57.7089-last_lat)**2 + (11.9746-last_lon)**2) * 111
                    hemkomst = nuvarande_tid + timedelta(minutes=(dist_hem/snitthastighet)*60)
                    
                    st.divider()
                    if hemkomst.time() > slut_pass:
                        st.error(f"⚠️ Slutid: {hemkomst.strftime('%H:%M')} (Övertid!)")
                    else:
                        st.info(f"🏁 Åter tvätteri: {hemkomst.strftime('%H:%M')}")

                    # SMS format med tider
                    sms = f"RUTT {b_namn} ({start_pass.strftime('%H:%M')})\n"
                    for n, s in enumerate(s_lista):
                        sms += f"\nStopp {n+1}: {s['namn']}\nSka vara där ca kl: {ankomst.strftime('%H:%M')}"
                    st.text_area("Kopiera till chaufför:", sms, height=100, key=f"t_{i}")

            if sorterade:
                st.warning(f"⚠️ {len(sorterade)} adresser hanns inte med.")
    else:
        st.warning("Klistra in adresser!")
