from datetime import datetime
from pydantic import BaseModel

class Parking(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    total_spots: int
    free_spots: int | None = None
    image: str | None = None
    checked_at: datetime | None = None
    source: str | None = None

class NearbyParking(BaseModel):
    parking: Parking
    distance_m: int