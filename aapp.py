import streamlit as st
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math

# --- KONFIGURATION & STYLING ---
st.set_page_config(page_title="Textilia Gbg Logistik", layout="wide")
st.title("🚛 Textilia Gbg: Ruttplanering")

# Initiera session state för att spara adresser under körning
if 'stops' not in st.session_state:
    st.session_state.stops = []

# --- SIDEBAR: FORDONSFLOTTA ---
st.sidebar.header("🚚 Dagens Fordon")
heavy_trucks = st.sidebar.number_input("Antal Lastbilar (12 vagnar)", min_value=0, value=2)
light_trucks = st.sidebar.number_input("Antal Lätta Lastbilar (6 vagnar)", min_value=0, value=1)

vehicle_capacities = ([12] * heavy_trucks) + ([6] * light_trucks)
num_vehicles = len(vehicle_capacities)

# --- INPUT: LÄGG TILL ADRESSER ---
st.subheader("1. Mata in dagens leveranser")
with st.form("address_form"):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        addr = st.text_input("Adress/Kundnamn")
    with col2:
        out_carts = st.number_input("Rena vagnar UT", min_value=0, step=1)
    with col3:
        in_carts = st.number_input("Smutsiga vagnar IN", min_value=0, step=1)
    
    # För demonstration använder vi enkla koordinater (X, Y) 
    # I en produktion-app ersätts detta av Google Maps API
    submitted = st.form_submit_button("Lägg till stopp")
    if submitted and addr:
        # Vi simulerar koordinater för Göteborgsområdet för logiken
        st.session_state.stops.append({
            "name": addr, 
            "demand": max(out_carts, in_carts), # Kapacitet som krävs
            "x": len(st.session_state.stops) * 2, # Dummy-koordinat
            "y": (len(st.session_state.stops) % 3) * 5 # Dummy-koordinat
        })

if st.session_state.stops:
    st.write(f"Antal stopp inlagda: **{len(st.session_state.stops)}**")
    if st.button("Rensa alla stopp"):
        st.session_state.stops = []
        st.rerun()

# --- OPTIMERINGSMOTOR (OR-TOOLS) ---
def solve_routing(stops, capacities):
    if not stops or not capacities: return None
    
    # Skapa distansmatris (Euclidiskt avstånd för demo)
    all_points = [{"name": "Tvätteriet", "x": 0, "y": 0}] + stops
    dist_matrix = []
    for p1 in all_points:
        row = []
        for p2 in all_points:
            dist = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
            row.append(int(dist * 100)) # OR-Tools gillar heltal
        dist_matrix.append(row)

    # Data modell
    data = {
        'distance_matrix': dist_matrix,
        'demands': [0] + [s['demand'] for s in stops],
        'vehicle_capacities': capacities,
        'num_vehicles': len(capacities),
        'depot': 0
    }

    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return data['distance_matrix'][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return data['demands'][manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    
    return routing.SolveWithParameters(search_params), manager, routing, all_points

# --- DISPLAY RESULTAT ---
if st.button("🚀 Beräkna optimala rutter", type="primary"):
    if len(st.session_state.stops) > 0:
        solution, manager, routing, all_points = solve_routing(st.session_state.stops, vehicle_capacities)
        
        if solution:
            st.success("Rutter optimerade!")
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                plan = []
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    plan.append(all_points[node_index]['name'])
                    index = solution.Value(routing.NextVar(index))
                plan.append("Tvätteriet")
                
                if len(plan) > 2: # Visa endast bilar som faktiskt kör
                    with st.expander(f"📋 Körlista: Fordon {vehicle_id + 1} ({'Lastbil' if vehicle_capacities[vehicle_id]>6 else 'Lätt lastbil'})"):
                        for i, stop in enumerate(plan):
                            st.write(f"**{i+1}. {stop}**")
                        
                        # Text för att enkelt kopiera
                        copy_text = " -> ".join(plan)
                        st.text_area("Kopiera rutt:", copy_text, key=f"text_{vehicle_id}")
        else:
            st.error("Kunde inte hitta en lösning. Kontrollera att bilarnas kapacitet räcker till.")
    else:
        st.warning("Lägg till adresser först!")