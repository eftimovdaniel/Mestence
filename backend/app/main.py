from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.data import PARKING
from app.models import Parking

class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

app = FastAPI(title = "Mestence API", default_response_class=UTF8JSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status:": "OK"}

@app.get("/api/parkings", response_model=list[Parking])
def get_parkings():
    return PARKING

@app.get("/api/parkings/{parking_id}", response_model=Parking)
def get_parking(parking_id: int):
    for parking in PARKING:
        if parking.id == parking_id:
            return parking
    raise HTTPException(status_code = 404, detail="Vo nasiot sisitem, parkingot ne postoi")