from app.models import Parking

PARKING = [
     Parking(id=1, name="Паркинг Центар", lat=41.7455, lon=22.1960,
            total_spots=40, free_spots=0),
    Parking(id=2, name="Паркинг Пазар", lat=41.7440, lon=22.1985,
            total_spots=30, free_spots=12),
    Parking(id=3, name="Паркинг Болница", lat=41.7400, lon=22.1900,
            total_spots=60, free_spots=25),
    Parking(id=4, name="Паркинг УГД", lat=41.7510, lon=22.1830,
            total_spots=80, free_spots=5),
]