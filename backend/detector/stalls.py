import cv2
import numpy as np

def _axis(angle):
    across = np.array([np.cos(angle), np.sin(angle)])
    along = np.array([-np.sin(angle), np.cos(angle)])
    return across, along

def _polygon(center, across, along, length, width):
    cx, cy = center
    du = along * (length / 2)
    dv = across * (width / 2)
    return np.array([[cx, cy] - du - dv,[cx, cy] + du - dv,[cx, cy] + du + dv,[cx, cy] - du + dv,], dtype=np.int32)

def _is_asphalt(hsv, polygon):
    mask = np.zeros(hsv.shape[:2], np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    pixels = hsv[mask == 255]
    if len(pixels) < 40:
        return False
    hue, sat, val = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    green = (hue > 35) & (hue < 95) & (sat > 40)
    dark = val < 150
    return float(green.mean()) < 0.12 and float(dark.mean()) > 0.45

def find_empty_stalls(crop, cars):
    if len(cars) < 2:
        return []

    angles = [np.degrees(car[2]) % 180 for car in cars]
    theta = np.radians(float(np.median(angles)))
    across, along = _axis(theta)

    placed = []
    for cx, cy, angle, long_side, short_side in cars:
        point = np.array([cx, cy], dtype=float)
        placed.append({
            "cx": cx,
            "cy": cy,
            "u": float(point @ along),
            "v": float(point @ across),
            "long": long_side,
        })

    placed.sort(key=lambda car: car["u"])
    split = float(np.median([car["long"] for car in placed])) * 0.6
    rows = [[placed[0]]]
    for car in placed[1:]:
        if car["u"] - rows[-1][-1]["u"] > split:
            rows.append([car])
        else:
            rows[-1].append(car)

    gaps = []
    for row in rows:
        vs = sorted(car["v"] for car in row)
        gaps.extend(b - a for a, b in zip(vs, vs[1:]))
    if not gaps:
        return []

    pitch = float(np.median(gaps))
    length = float(np.median([car["long"] for car in placed])) * 0.92
    width = pitch * 0.82
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    empty = []
    for row in rows:
        row = sorted(row, key=lambda car: car["v"])
        for left, right in zip(row, row[1:]):
            gap = right["v"] - left["v"]
            missing = int(round(gap / pitch)) - 1
            if missing < 1 or missing > 3:
                continue
            for step in range(1, missing + 1):
                t = step / (missing + 1)
                center = (
                    left["cx"] + (right["cx"] - left["cx"]) * t,
                    left["cy"] + (right["cy"] - left["cy"]) * t,
                )
                polygon = _polygon(center, across, along, length, width)
                if _is_asphalt(hsv, polygon):
                    empty.append(polygon)
    return empty
