from pathlib import Path
from app.models import Parking

ROOT = Path(__file__).resolve().parents[1]

def update_free_spots(parking: Parking) -> bool:
    if not parking.image:
        return False
    from detector.detect import detect_vehicles
    from detector.spot import free_spots
    occupied = detect_vehicles(str(ROOT / parking.image))
    parking.free_spots = free_spots(occupied, parking.total_spots)
    return True