import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Ruttplanerare", layout="wide")
st.title("🚛 Din Ruttplanerare")

st.sidebar.header("🚚 Dina Fordon")
antal_bilar = st.sidebar.number_input("Hur många bilar kör idag?", min_value=1, max_value=10, value=2)

fordons_data = []
for i in range(int(antal_bilar)):
    cap = st.sidebar.number_input(
        f"Kapacitet bil {i+1} (antal vagnar)",
        min_value=1,
        value=10,
        key=f"cap_{i}"
    )
    fordons_data.append({
        "id": i + 1,
        "cap": cap,
        "last": 0
    })

st.subheader("📍 Lägg till adresser")
st.info("Klistra in adresser i formatet: Namn, Antal vagnar")

bulk_input = st.text_area(
    "Exempel:\nHotell A, 5\nRestaurang B, 3",
    height=150
)

if st.button("🚀 Planera rutter", type="primary"):

    if not bulk_input.strip():
        st.warning("Klistra in några adresser först!")
        st.stop()

    stopp = []

    for rad in bulk_input.splitlines():
        if not rad.strip():
            continue

        try:
            namn, vagnar = rad.rsplit(",", 1)
            vagnar = int(vagnar.strip())

            lat = 57.70 + np.random.uniform(-0.04, 0.04)
            lon = 11.97 + np.random.uniform(-0.04, 0.04)

            stopp.append({
                "namn": namn.strip(),
                "vagnar": vagnar,
                "lat": lat,
                "lon": lon
            })

        except:
            st.error(f"Kunde inte läsa raden: {rad}")

    if not stopp:
        st.warning("Inga giltiga stopp hittades.")
        st.stop()

    # Sortera största stopp först = bättre kapacitetsplanering
    stopp = sorted(stopp, key=lambda x: x["vagnar"], reverse=True)

    rutter = {f"Bil {bil['id']}": [] for bil in fordons_data}
    otilldelade = []

    for s in stopp:
        bästa_bil = None
        min_ledigt_efter = float("inf")

        for bil in fordons_data:
            ledigt = bil["cap"] - bil["last"]

            if s["vagnar"] <= ledigt:
                ledigt_efter = ledigt - s["vagnar"]

                if ledigt_efter < min_ledigt_efter:
                    min_ledigt_efter = ledigt_efter
                    bästa_bil = bil

        if bästa_bil:
            rutter[f"Bil {bästa_bil['id']}"].append(s)
            bästa_bil["last"] += s["vagnar"]
        else:
            otilldelade.append(s)

    st.subheader("🗺️ Kartöversikt")

    kart_data = []
    for bil_namn, stopp_lista in rutter.items():
        for s in stopp_lista:
            kart_data.append({
                "lat": s["lat"],
                "lon": s["lon"]
            })

    if kart_data:
        st.map(pd.DataFrame(kart_data))
    else:
        st.info("Inga stopp kunde visas på kartan.")

    st.subheader("📋 Färdiga Körlistor")

    cols = st.columns(len(rutter))

    for i, (bil_namn, stopp_lista) in enumerate(rutter.items()):
        with cols[i]:
            total_vagnar = sum(s["vagnar"] for s in stopp_lista)
            kapacitet = fordons_data[i]["cap"]

            st.success(f"{bil_namn.upper()}")
            st.write(f"Last: **{total_vagnar}/{kapacitet} vagnar**")

            if not stopp_lista:
                st.write("Inga stopp tilldelade.")
            else:
                for j, s in enumerate(stopp_lista):
                    st.write(f"{j+1}. **{s['namn']}** ({s['vagnar']} vagnar)")

                txt = f"RUTT {bil_namn}:\n" + "\n".join(
                    [f"{j+1}. {s['namn']} - {s['vagnar']} vagnar" for j, s in enumerate(stopp_lista)]
                )

                st.text_area("Kopiera rutt:", txt, height=120, key=f"copy_{i}")

    if otilldelade:
        st.warning("⚠️ Följande stopp fick inte plats:")

        for s in otilldelade:
            st.write(f"- {s['namn']} ({s['vagnar']} vagnar)")
