from pydantic import BaseModel

class Parking (BaseModel):
    id: int
    name: str
    lat:float
    lon:float
    total_spots: int
    free_spots: int

class NearbyParking (BaseModel):
    parking: Parking
    distance_m: int