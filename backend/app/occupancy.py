import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from app.data import PARKING
from app.models import Parking

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()

def update_free_spots(parking: Parking) -> bool:
    if not parking.image:
        return False
    from detector.detect import detect_vehicles
    from detector.spot import free_spots
    with LOCK:
        occupied = detect_vehicles(str(ROOT / parking.image))
        parking.free_spots = free_spots(occupied, parking.total_spots)
        parking.checked_at = datetime.now(timezone.utc)
        parking.source = "image"
    return True

async def watch_images(interval_s: int = 30):
    while True:
        for parking in PARKING:
            if parking.image:
                await asyncio.to_thread(update_free_spots, parking)
        await asyncio.sleep(interval_s)