from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json, math, networkx as nx

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def load_geojson(filename):
    with open(f"data/{filename}", "r") as f: return json.load(f)

@app.get("/")
def root(): return {"status": "Antarctic Navigation API Active"}

@app.get("/api/data")
def get_map_data():
    return {
        "ice_grid": load_geojson("ice_density.geojson"),
        "icebergs": load_geojson("icebergs.geojson"),
        "ports": load_geojson("ports.geojson")
    }

@app.post("/api/predict-drift")
def predict_drift(hours: float = 6.0):
    icebergs = load_geojson("icebergs.geojson")
    for feature in icebergs["features"]:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        speed_knots, heading_deg = props["drift_speed_knots"], props["heading_deg"]
        
        distance_deg = (speed_knots * 1.852 / 111.0) * hours
        rad = math.radians(heading_deg)
        
        feature["geometry"]["coordinates"] = [
            round(lon + (distance_deg * math.sin(rad)), 4),
            round(lat + (distance_deg * math.cos(rad)), 4)
        ]
    return {"status": "success", "hours_shifted": hours, "updated_icebergs": icebergs}

@app.post("/api/route")
def calculate_safe_route():
    ice_data = load_geojson("ice_density.geojson")
    features = ice_data["features"]
    G = nx.grid_2d_graph(25, 25)
    grid_lookup = {}
    
    for feature in features:
        props, coords = feature["properties"], feature["geometry"]["coordinates"][0]
        col, row = props["col"], props["row"]
        grid_lookup[(col, row)] = {
            "lon": (coords[0][0] + coords[2][0]) / 2,
            "lat": (coords[0][1] + coords[2][1]) / 2,
            "penalty": props["traversal_penalty"],
            "ice_density": props["sea_ice_concentration"]
        }

    for (u, v) in G.edges(): 
        G[u][v]['weight'] = grid_lookup[v]["penalty"]
    
    path_nodes = nx.astar_path(G, (0, 20), (24, 5), heuristic=lambda a,b: math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2), weight='weight')
    
    route_coords = [[grid_lookup[node]["lon"], grid_lookup[node]["lat"]] for node in path_nodes]
    
    # Calculate voyage metrics
    total_distance_nm = round(len(path_nodes) * 4.8, 1) # Approximate Nautical Miles
    avg_ice_density = round(sum(grid_lookup[node]["ice_density"] for node in path_nodes) / len(path_nodes), 1)
    estimated_voyage_hrs = round(total_distance_nm / 12.0, 1) # Assumes 12 knot vessel speed
    fuel_savings_pct = max(5, round(35 - (avg_ice_density * 0.25), 1))

    return {
        "status": "success",
        "route": route_coords,
        "metrics": {
            "distance_nm": total_distance_nm,
            "avg_ice_density": avg_ice_density,
            "voyage_hours": estimated_voyage_hrs,
            "fuel_savings_pct": fuel_savings_pct
        }
    }