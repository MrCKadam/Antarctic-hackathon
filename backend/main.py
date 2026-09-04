from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(title="Antarctic Navigator API", version="1.0.0")

# 1. CORS Setup — Enables cross-origin requests from React / GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Pydantic Models for Input Validation
class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class RouteRequest(BaseModel):
    start: Coordinate
    end: Coordinate

class RouteResponse(BaseModel):
    distance_nm: float
    est_hours: float
    hazards_avoided: int
    path: List[List[float]]

class Iceberg(BaseModel):
    id: str
    lat: float
    lng: float
    size_km2: float
    speed_knots: float
    direction: str
    dist_to_lane_nm: float
    time_to_impact_hrs: float
    risk_score: float
    risk_level: str

# 3. Deterministic Risk Score Logic
def compute_risk_score(dist_lane_nm: float, speed_kts: float, area_km2: float, time_hrs: float) -> tuple[float, str]:
    raw_risk = (50.0 / (dist_lane_nm + 1.0)) + (12.0 * speed_kts) + (1.5 * area_km2) - (0.4 * time_hrs)
    score = round(min(100.0, max(0.0, raw_risk)), 1)
    
    if score >= 75.0:
        level = "red"
    elif score >= 40.0:
        level = "yellow"
    else:
        level = "green"
        
    return score, level

# 4. In-Memory Dataset
RAW_ICEBERGS = [
    {"id": "IB-042", "lat": -64.9, "lng": -63.6, "size_km2": 14.2, "speed_knots": 1.8, "direction": "NW", "dist_to_lane_nm": 2.1, "time_to_impact_hrs": 14.0},
    {"id": "IB-108", "lat": -65.3, "lng": -64.2, "size_km2": 6.5, "speed_knots": 1.1, "direction": "W", "dist_to_lane_nm": 8.5, "time_to_impact_hrs": 36.0},
    {"id": "IB-201", "lat": -65.1, "lng": -62.8, "size_km2": 2.1, "speed_knots": 0.8, "direction": "SW", "dist_to_lane_nm": 18.2, "time_to_impact_hrs": 72.0},
    {"id": "IB-315", "lat": -65.7, "lng": -63.9, "size_km2": 18.9, "speed_knots": 2.1, "direction": "NW", "dist_to_lane_nm": 0.8, "time_to_impact_hrs": 8.0},
]

def get_processed_icebergs() -> List[Iceberg]:
    processed = []
    for item in RAW_ICEBERGS:
        score, level = compute_risk_score(
            item["dist_to_lane_nm"], item["speed_knots"], item["size_km2"], item["time_to_impact_hrs"]
        )
        processed.append(Iceberg(**item, risk_score=score, risk_level=level))
    return processed

# 5. API Endpoints
@app.get("/icebergs", response_model=List[Iceberg])
def get_icebergs(risk: Optional[str] = Query(None, description="Filter by risk: red, yellow, green")):
    icebergs = get_processed_icebergs()
    if risk:
        icebergs = [b for b in icebergs if b.risk_level.lower() == risk.lower()]
    return icebergs

@app.get("/icebergs/{iceberg_id}", response_model=Iceberg)
def get_iceberg_by_id(iceberg_id: str):
    icebergs = get_processed_icebergs()
    for berg in icebergs:
        if berg.id.lower() == iceberg_id.lower():
            return berg
    raise HTTPException(status_code=404, detail=f"Iceberg '{iceberg_id}' not found")

@app.get("/alerts")
def get_alerts():
    icebergs = get_processed_icebergs()
    alerts = [
        {
            "id": b.id,
            "severity": "CRITICAL",
            "message": f"Iceberg {b.id} entering shipping lane — ETA {b.time_to_impact_hrs}h"
        }
        for b in icebergs if b.risk_level == "red"
    ]
    alerts.append({
        "id": "SYS-001",
        "severity": "WARNING",
        "message": "Rapid sea-ice accumulation in Neumayer Channel"
    })
    return {"alerts": alerts}

@app.get("/stats")
def get_stats():
    icebergs = get_processed_icebergs()
    total = len(icebergs)
    high_risk = sum(1 for b in icebergs if b.risk_level == "red")
    avg_speed = round(sum(b.speed_knots for b in icebergs) / total, 2) if total else 0.0
    return {
        "total_icebergs": total,
        "high_risk_count": high_risk,
        "avg_speed_knots": avg_speed,
        "active_alerts": len(icebergs)
    }

@app.post("/route", response_model=RouteResponse)
def calculate_route(request: RouteRequest):
    s_lat, s_lng = request.start.lat, request.start.lng
    e_lat, e_lng = request.end.lat, request.end.lng
    
    approx_dist = round(((e_lat - s_lat)**2 + (e_lng - s_lng)**2)**0.5 * 60.0, 1)
    est_hours = round(approx_dist / 13.0, 1)
    
    waypoints = [
        [s_lat, s_lng],
        [round((s_lat + e_lat) / 2 + 0.1, 2), round((s_lng + e_lng) / 2 - 0.2, 2)],
        [e_lat, e_lng]
    ]
    
    return RouteResponse(
        distance_nm=approx_dist,
        est_hours=est_hours,
        hazards_avoided=3,
        path=waypoints
    )