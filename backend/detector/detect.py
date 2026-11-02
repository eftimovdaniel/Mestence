import sys
from pathlib import Path
import cv2
from ultralytics import YOLO

VEHICLE_CLASSES = {9: "large vehicle", 10: "small vehicle"}

def detect_vehicles(image_path: str, output_dir: str = "output") -> int:
    model = YOLO("yolo11n-obb.pt")
    results = model(image_path, classes=list(VEHICLE_CLASSES.keys()),conf=0.3, imgsz=1280)
    result = results[0]
    image = cv2.imread(image_path)
    count = 0

    for box in result.obb:
        conf = float(box.conf[0])
        points = box.xyxyxyxy[0].cpu().numpy().astype(int)

        cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)
        x, y = points[0]
        cv2.putText(image, f"{conf:.2f}", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        count += 1

    cv2.putText(image, f"Vozila: {count}", (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 6)
    Path(output_dir).mkdir(exist_ok=True)
    out_path = Path(output_dir) / f"detected_{Path(image_path).name}"
    cv2.imwrite(str(out_path), image)

    print(f"Najdeni vozila: {count}")
    print(f"Zacuvano vo: {out_path}")
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Upotreba: python detector/detect.py <pateka_do_slika>")
        sys.exit(1)
    detect_vehicles(sys.argv[1])