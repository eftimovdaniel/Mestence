from pydantic import BaseModel

class Parking (BaseModel):
    id: int
    name: str
    lat:float
    lon:float
    total_spots: int
    free_spots: int