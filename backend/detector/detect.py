import sys
from pathlib import Path
import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
MODEL = YOLO(str(ROOT / "yolo11n-obb.pt"))
OUTPUT_DIR = ROOT / "output"

# x1, y1, x2, y2 kako del od slikata
LOT_BOX = (0.478, 0.372, 0.798, 0.892)
VEHICLE_CLASSES = [9, 10]
SAME_CAR_PX = 30

def lot_pixels(width, height):
    x1, y1, x2, y2 = LOT_BOX
    return int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)

def same_car(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= SAME_CAR_PX ** 2

def detect_vehicles(image_path: str) -> int:
    image = cv2.imread(image_path)
    if image is None:
        raise SystemExit(f"Ne moze da se procita slikata: {image_path}")
    height, width = image.shape[:2]
    x1, y1, x2, y2 = lot_pixels(width, height)
    crop = image[y1:y2, x1:x2].copy()

    results = MODEL(crop,classes=VEHICLE_CLASSES,conf=0.15,imgsz=224,verbose=False,)
    result = results[0]
    found = []
    if result.obb is not None:
        for box in result.obb:
            points = box.xyxyxyxy[0].cpu().numpy()
            center = (float(points[:, 0].mean()), float(points[:, 1].mean()))
            found.append((float(box.conf[0]), center, points))

    found.sort(key=lambda item: item[0], reverse=True)
    kept = []
    for item in found:
        if any(same_car(item[1], other[1]) for other in kept):
            continue
        kept.append(item)

    for conf, center, points in kept:
        points = points.copy()
        points[:, 0] += x1
        points[:, 1] += y1
        points = points.astype(int)
        cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)

    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 4)
    cv2.putText(image,f"Vo parcelata: {len(kept)}",(40, 120),cv2.FONT_HERSHEY_SIMPLEX,2.4,(0, 0, 255),5,)
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"detected_{Path(image_path).name}"
    cv2.imwrite(str(out_path), image)
    print(f"Vozila vo parcelata: {len(kept)}")
    print(f"Zacuvano vo: {out_path}")
    return len(kept)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Upotreba: python detector/detect.py data/parking.jpg")
        sys.exit(1)
    detect_vehicles(sys.argv[1])