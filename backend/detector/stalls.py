import cv2
import numpy as np

MAX_END_STEPS = 4

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

def _covers_car(stall, car_polys, image_shape):
    stall_mask = np.zeros(image_shape[:2], np.uint8)
    cv2.fillPoly(stall_mask, [stall], 1)
    area = int(stall_mask.sum())
    if area == 0:
        return True
    for car in car_polys:
        car_mask = np.zeros(image_shape[:2], np.uint8)
        cv2.fillPoly(car_mask, [np.asarray(car, dtype=np.int32)], 1)
        overlap = int(np.logical_and(stall_mask, car_mask).sum())
        if overlap / area > 0.4:
            return True
    return False

def _contains(polygon, point):
    return cv2.pointPolygonTest(polygon.astype(np.float32),(float(point[0]), float(point[1])),False,) >= 0

def _has_white_line(white, center, across, along, length, width):
    height, width_px = white.shape
    hits = 0
    for sign in (-1, 1):
        origin = np.array(center, dtype=float) + across * (width * 0.5 * sign)
        for t in np.linspace(-0.35, 0.35, 8):
            point = origin + along * (length * t)
            x, y = int(round(point[0])), int(round(point[1]))
            if 2 <= x < width_px - 2 and 2 <= y < height - 2:
                if white[y - 2:y + 3, x - 2:x + 3].any():
                    hits += 1
    return hits >= 3

def _take_weak(polygon, weak, used):
    for index, (wx, wy, points) in enumerate(weak):
        if used[index]:
            continue
        if _contains(polygon, (wx, wy)):
            used[index] = True
            return points
    return None

def _line_bars(gray, horizontal):
    kernel = max(36, gray.shape[1] // 16)
    if not horizontal:
        gray = gray.T
        kernel = max(36, gray.shape[1] // 16)
    hat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
    _, bw = cv2.threshold(hat, 10, 255, cv2.THRESH_BINARY)
    opened = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kernel, 1)))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(opened)
    bars = []
    for index in range(1, count):
        x, y, width, height, _area = stats[index]
        if width >= kernel and height <= 10:
            bars.append((float(centroids[index][1]), float(x), float(x + width)))
    wide = [bar for bar in bars if bar[2] - bar[1] >= max(kernel * 2, 80)]
    if len(wide) < 4:
        return []
    typical = float(np.median([bar[2] - bar[1] for bar in wide]))
    return [bar for bar in wide if bar[2] - bar[1] >= typical * 0.55]


def _stalls_from_end_lines(crop, cars, car_polys, weak, used):
    """Mesto e megju dve bela linii na zatvoreniot kraj, vo edna kolona, bez kola vnatre."""
    if len(cars) < 2:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    painted = gray.copy()
    fill = int(np.median(gray))
    for poly in car_polys:
        cv2.fillConvexPoly(painted, np.asarray(poly, np.int32), fill)

    best = None
    for horizontal in (True, False):
        bars = _line_bars(painted, horizontal)
        if len(bars) < 3:
            continue
        widths = sorted(b - a for _, a, b in bars)
        stall_w = float(np.median(widths))
        if stall_w < 30:
            continue
        pieces = []
        for y, x1, x2 in bars:
            span = x2 - x1
            slots = max(1, min(3, int(round(span / stall_w))))
            for slot in range(slots):
                pieces.append((y, x1 + slot * span / slots, x1 + (slot + 1) * span / slots))
        columns = []
        for y, a, b in sorted(pieces, key=lambda item: (item[1] + item[2]) / 2):
            center_x = (a + b) / 2
            for column in columns:
                mean_x = float(np.mean([(p[1] + p[2]) / 2 for p in column]))
                if abs(center_x - mean_x) < stall_w * 0.55:
                    column.append((y, a, b))
                    break
            else:
                columns.append([(y, a, b)])
        stalls = []
        for column in columns:
            column = sorted(column)
            gaps = [b[0] - a[0] for a, b in zip(column, column[1:]) if stall_w * 0.35 < b[0] - a[0] < stall_w * 1.4]
            if len(gaps) < 2:
                continue
            pitch = float(np.median(gaps))
            for left, right in zip(column, column[1:]):
                gap = right[0] - left[0]
                slots = int(round(gap / pitch))
                if slots < 1 or slots > 2 or gap > pitch * 2.4:
                    continue
                x1 = max(left[1], right[1])
                x2 = min(left[2], right[2])
                if x2 - x1 < stall_w * 0.45:
                    x1 = min(left[1], right[1])
                    x2 = max(left[2], right[2])
                for slot in range(slots):
                    y1 = left[0] + slot * gap / slots
                    y2 = left[0] + (slot + 1) * gap / slots
                    stalls.append((x1, y1, x2, y2))
        if len(stalls) < 4:
            continue
        if best is None or len(stalls) > len(best[0]):
            best = (stalls, horizontal)

    if best is None:
        return None

    stalls, horizontal = best
    height, width = crop.shape[:2]
    empty = []
    taken = []
    centers = [(car[0], car[1]) for car in cars]

    def inside(box, x, y):
        x1, y1, x2, y2 = box
        if not horizontal:
            x, y = y, x
        return x1 <= x <= x2 and y1 <= y <= y2

    for box in stalls:
        hit = next((index for index, (wx, wy, _points) in enumerate(weak) if not used[index] and inside(box, wx, wy)), None)
        if hit is not None:
            used[hit] = True
            taken.append(weak[hit][2])
            continue
        if any(inside(box, x, y) for x, y in centers):
            continue
        x1, y1, x2, y2 = box
        if horizontal:
            polygon = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
        else:
            polygon = np.array([[y1, x1], [y2, x1], [y2, x2], [y1, x2]], dtype=np.int32)
        polygon[:, 0] = np.clip(polygon[:, 0], 0, width - 1)
        polygon[:, 1] = np.clip(polygon[:, 1], 0, height - 1)
        if _covers_car(polygon, car_polys, crop.shape):
            continue
        empty.append(polygon)
    return empty, taken


def find_empty_stalls(crop, cars, car_polys=None, weak=None):
    if len(cars) < 2:
        return [], []

    car_polys = car_polys or []
    weak = weak or []
    used = [False] * len(weak)
    painted = _stalls_from_end_lines(crop, cars, car_polys, weak, used)
    if painted is not None:
        return painted

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
        return [], []
    pitch = float(np.median(gaps))
    length = float(np.median([car["long"] for car in placed])) * 0.92
    width = pitch * 0.82
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, 170), (180, 60, 255))

    empty = []
    taken = []

    def consider(center, require_line):
        polygon = _polygon(center, across, along, length, width)
        if _covers_car(polygon, car_polys, crop.shape):
            return False
        if require_line and not _has_white_line(white, center, across, along, length, width):
            return False
        weak_points = _take_weak(polygon, weak, used)
        if weak_points is not None:
            taken.append(weak_points)
            return True
        if not _is_asphalt(hsv, polygon):
            return False
        empty.append(polygon)
        return True

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
                consider(center, require_line=False)

        for direction, origin in ((-1, row[0]), (1, row[-1])):
            cx, cy = origin["cx"], origin["cy"]
            for _ in range(MAX_END_STEPS):
                cx = cx + across[0] * pitch * direction
                cy = cy + across[1] * pitch * direction
                if not consider((cx, cy), require_line=True):
                    break

    return empty, taken
