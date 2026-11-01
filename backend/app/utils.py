import math

EARTH_RADIUS_M = 6_371_000

#rastojanie vo metri pomegju dve koordinati, dve tocki
def distance_m (lat1: float, lon1: float, lat2: float, lon2: float) -> float:
   phi1 = math.radians(lat1)
   phi2 = math.radians(lat2)
   d_phi = math.radians(lat2 - lat1)
   d_lambda = math.radians(lon2 - lon1)

   a = (math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
   return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))