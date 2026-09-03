import json
import random

def generate_ice_density_grid(center_lat=-69.0, center_lon=76.0, grid_size=25, cell_size=0.08):
    features = []
    half_grid = grid_size / 2
    shelf_lat = center_lat - 0.6
    
    for i in range(grid_size):
        for j in range(grid_size):
            min_lon = center_lon + (i - half_grid) * cell_size
            max_lon = min_lon + cell_size
            min_lat = center_lat + (j - half_grid) * cell_size
            max_lat = min_lat + cell_size
            
            cell_center_lat = (min_lat + max_lat) / 2
            dist_from_shelf = max(0, cell_center_lat - shelf_lat)
            base_density = max(0, 100 - (dist_from_shelf * 45))
            noise = random.uniform(-12, 12)
            concentration = round(min(100, max(0, base_density + noise)), 1)
            
            risk = "LOW" if concentration < 25 else "MEDIUM" if concentration < 55 else "HIGH" if concentration < 80 else "EXTREME"
            
            coordinates = [[[round(min_lon, 4), round(min_lat, 4)], [round(max_lon, 4), round(min_lat, 4)], [round(max_lon, 4), round(max_lat, 4)], [round(min_lon, 4), round(max_lat, 4)], [round(min_lon, 4), round(min_lat, 4)]]]
            
            features.append({
                "type": "Feature",
                "properties": {"cell_id": f"GRID_{i:02d}_{j:02d}", "row": j, "col": i, "sea_ice_concentration": concentration, "risk_level": risk, "traversal_penalty": round(1.0 + (concentration / 10.0), 2)},
                "geometry": {"type": "Polygon", "coordinates": coordinates}
            })
    return {"type": "FeatureCollection", "features": features}

def generate_icebergs(count=12, center_lat=-69.0, center_lon=76.0):
    features = []
    prefixes = ["B-15", "A-76", "C-22", "D-19"]
    for i in range(count):
        lat = round(center_lat + random.uniform(-0.7, 0.7), 4)
        lon = round(center_lon + random.uniform(-0.7, 0.7), 4)
        length_m = random.randint(400, 3200)
        features.append({
            "type": "Feature",
            "properties": {"berg_id": f"BERG_{i+1:03d}", "name": f"{random.choice(prefixes)}-{chr(65 + i)}", "length_m": length_m, "drift_speed_knots": round(random.uniform(0.8, 3.2), 2), "heading_deg": random.randint(0, 359), "safety_radius_km": round(random.uniform(2.5, 6.0), 1)},
            "geometry": {"type": "Point", "coordinates": [lon, lat]}
        })
    return {"type": "FeatureCollection", "features": features}

def generate_waypoints():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"point_type": "START", "name": "Open Ocean Approach"}, "geometry": {"type": "Point", "coordinates": [75.1, -68.2]}},
        {"type": "Feature", "properties": {"point_type": "DESTINATION", "name": "Bharati Station"}, "geometry": {"type": "Point", "coordinates": [76.9, -69.4]}}
    ]}

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/ice_density.geojson", "w") as f: json.dump(generate_ice_density_grid(), f, indent=2)
    with open("data/icebergs.geojson", "w") as f: json.dump(generate_icebergs(), f, indent=2)
    with open("data/ports.geojson", "w") as f: json.dump(generate_waypoints(), f, indent=2)
    print("Map data created in data/ folder!")