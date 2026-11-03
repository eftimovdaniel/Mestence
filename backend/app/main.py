from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.data import PARKING
from app.models import Parking, NearbyParking
from app.utils import distance_m
from app.occupancy import update_free_spots

class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

app = FastAPI(title="Mestence API", default_response_class=UTF8JSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def find_parking(parking_id: int) -> Parking:
    for parking in PARKING:
        if parking.id == parking_id:
            return parking
    raise HTTPException(status_code=404, detail="Vo nasiot sisitem, parkingot ne postoi")

@app.get("/api/health")
def health():
    return {"status": "OK"}

@app.get("/api/parkings", response_model=list[Parking])
def get_parkings():
    return PARKING

@app.get("/api/parkings/{parking_id}", response_model=Parking)
def get_parking(parking_id: int):
    return find_parking(parking_id)

@app.post("/api/parkings/{parking_id}/detect", response_model=Parking)
def detect_parking(parking_id: int):
    parking = find_parking(parking_id)
    if not update_free_spots(parking):
        raise HTTPException(status_code=400, detail="Ovoj parking nema slika")
    return parking

@app.get("/api/parkings/{parking_id}/nearest-free", response_model=list[NearbyParking])
def get_nearest_free(parking_id: int, limit: int = 3):
    selected = find_parking(parking_id)
    candidates = []
    for parking in PARKING:
        if parking.id == selected.id or not parking.free_spots:
            continue
        dist = distance_m(selected.lat, selected.lon, parking.lat, parking.lon)
        candidates.append(NearbyParking(parking=parking, distance_m=round(dist)))
    candidates.sort(key=lambda c: c.distance_m)
    return candidates[:limit]