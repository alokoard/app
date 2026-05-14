import streamlit as st
import pandas as pd
import numpy as np

# --- Inställningar ---
st.set_page_config(page_title="Ruttplanerare", layout="wide")
st.title("🚛 Din Ruttplanerare")

# --- 1. Fordonsinställningar (Här bestämmer DU kapaciteten) ---
st.sidebar.header("🚚 Dina Fordon")
antal_bilar = st.sidebar.number_input("Hur många bilar kör idag?", min_value=1, max_value=10, value=2)

fordons_data = []
for i in range(int(antal_bilar)):
    cap = st.sidebar.number_input(f"Kapacitet bil {i+1} (antal vagnar)", min_value=1, value=10, key=f"cap_{i}")
    fordons_data.append({"id": i+1, "cap": cap})

# --- 2. Inmatning av adresser ---
st.subheader("📍 Lägg till adresser")
st.info("Klistra in adresser i formatet: **Namn, Antal vagnar** (en per rad)")
bulk_input = st.text_area("Exempel:\nHotell A, 5\nRestaurang B, 3", height=150)

if st.button("🚀 Planera rutter", type="primary"):
    if bulk_input:
        stopp = []
        rader = bulk_input.split('\n')
        
        for rad in rader:
            if ',' in rad:
                try:
                    delar = rad.split(',')
                    namn = delar[0].strip()
                    vagnar = int(delar[1].strip())
                    # Skapar slumpmässiga koordinater i Gbg för kartan
                    lat = 57.70 + np.random.uniform(-0.04, 0.04)
                    lon = 11.97 + np.random.uniform(-0.04, 0.04)
                    stopp.append({"namn": namn, "vagnar": vagnar, "lat": lat, "lon": lon})
                except:
                    st.error(f"Kunde inte läsa raden: {rad}")

        if stopp:
            # --- Ruttlogik (Sortering) ---
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
            st.subheader("🗺️ Kartöversikt")
            kart_data = []
            for bil_namn, stopp_lista in rutter.items():
                for s in stopp_lista:
                    kart_data.append({"lat": s['lat'], "lon": s['lon'], "Bil": bil_namn})
            
            if kart_data:
                st.map(pd.DataFrame(kart_data))

            # --- Visa Körlistor ---
            st.subheader("📋 Färdiga Körlistor")
            cols = st.columns(len(rutter))
            for i, (bil_namn, stopp_lista) in enumerate(rutter.items()):
                with cols[i]:
                    st.success(f"**{bil_namn.upper()}**")
                    if not stopp_lista:
                        st.write("Inga stopp tilldelade.")
                    else:
                        for j, s in enumerate(stopp_lista):
                            st.write(f"{j+1}. **{s['namn']}** ({s['vagnar']} vagnar)")
                        
                        # Kopierbar text
                        txt = f"RUTT {bil_namn}: " + " -> ".join([s['namn'] for s in stopp_lista])
                        st.text_area("Kopiera rutt:", txt, height=70, key=f"copy_{i}")

            if sorterade_stopp:
                st.warning(f"⚠️ {len(sorterade_stopp)} stopp hanns inte med! Du behöver fler eller större bilar.")
    else:
        st.warning("Klistra in några adresser först!")
