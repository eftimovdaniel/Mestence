import sys
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Results

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from detector.spot import free_spots
from detector.stalls import find_empty_stalls

MODEL = YOLO(str(ROOT / "yolo11n-obb.pt"))
OUTPUT_DIR = ROOT / "output"

# x1, y1, x2, y2 kako del od slikata
LOT_BOX = (0.478, 0.372, 0.798, 0.892)
VEHICLE_CLASSES = [9, 10]
SAME_CAR_PX = 30
LOW_CONF = 0.08
HIGH_CONF = 0.15

def lot_pixels(width, height):
    x1, y1, x2, y2 = LOT_BOX
    return int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)

def same_car(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= SAME_CAR_PX ** 2

def _as_numpy(value):
    if isinstance(value, np.ndarray):
        return value
    return value.detach().cpu().numpy()

def detect_vehicles(image_path: str, save_image: bool = False):
    image = cv2.imread(image_path)
    if image is None:
        raise RuntimeError(f"Ne moze da se procita slikata: {image_path}")
    height, width = image.shape[:2]
    x1, y1, x2, y2 = lot_pixels(width, height)
    crop = image[y1:y2, x1:x2].copy()
    prediction = MODEL(crop, classes=VEHICLE_CLASSES, conf=LOW_CONF, imgsz=224, verbose=False)
    if not isinstance(prediction, list) or not prediction:
        raise RuntimeError("Neocekuvan odgovor od modelot")
    first = prediction[0]
    if not isinstance(first, Results):
        raise RuntimeError("Neocekuvan odgovor od modelot")
    found = []
    obb = first.obb
    if obb is not None and len(obb) > 0:
        xywhr = _as_numpy(obb.xywhr)
        corners = _as_numpy(obb.xyxyxyxy)
        confs = _as_numpy(obb.conf)
        for index in range(len(xywhr)):
            points = corners[index]
            center = (float(points[:, 0].mean()), float(points[:, 1].mean()))
            found.append((float(confs[index]), center, points, xywhr[index]))
    found.sort(key=lambda item: item[0], reverse=True)
    strong = []
    weak = []
    for item in found:
        if item[0] >= HIGH_CONF:
            strong.append(item)
        else:
            weak.append(item)
    kept = []
    for item in strong:
        if any(same_car(item[1], other[1]) for other in kept):
            continue
        kept.append(item)
    weak_kept = []
    for item in weak:
        if any(same_car(item[1], other[1]) for other in kept):
            continue
        if any(same_car(item[1], other[1]) for other in weak_kept):
            continue
        weak_kept.append(item)
    cars = []
    car_polys = []
    for conf, center, points, whr in kept:
        cx, cy, bw, bh, ang = [float(value) for value in whr]
        cars.append((cx, cy, ang, max(bw, bh), min(bw, bh)))
        car_polys.append(points)

    weak_for_stalls = [(item[1][0], item[1][1], item[2]) for item in weak_kept]
    empty, taken = find_empty_stalls(crop, cars, car_polys, weak_for_stalls)

    occupied = len(kept) + len(taken)
    total = occupied + len(empty)
    free = free_spots(occupied, total)
    print(f"Vozila vo parcelata: {occupied}")
    print(f"Slobodni mesta: {free} od {total}")

    if save_image:
        for conf, center, points, whr in kept:
            points = points.copy()
            points[:, 0] += x1
            points[:, 1] += y1
            cv2.polylines(image, [points.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)
        for points in taken:
            points = points.copy()
            points[:, 0] += x1
            points[:, 1] += y1
            cv2.polylines(image, [points.astype(int)], isClosed=True, color=(0, 255, 0), thickness=2)
        for polygon in empty:
            polygon = polygon.copy()
            polygon[:, 0] += x1
            polygon[:, 1] += y1
            cv2.polylines(image, [polygon], isClosed=True, color=(0, 255, 255), thickness=3)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 4)
        cv2.putText(image, f"Vo parcelata: {occupied}", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (0, 0, 255), 5)
        cv2.putText(image, f"Slobodni: {free}", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (0, 0, 255), 5)
        OUTPUT_DIR.mkdir(exist_ok=True)
        out_path = OUTPUT_DIR / f"detected_{Path(image_path).name}"
        cv2.imwrite(str(out_path), image)
        print(f"Zacuvano vo: {out_path}")

    return occupied, total

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Upotreba: python detector/detect.py data/parking.jpg")
        sys.exit(1)
    detect_vehicles(sys.argv[1], save_image=True)
