"""Compare object detectors on one authenticated CCTV snapshot.

Outputs: outputs/model-comparison/results.json and annotated images.
No credential printed. No face recognition.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
import requests
from dotenv import dotenv_values
from ultralytics import YOLO

PERSON_CLASS = 0
CHAIR_CLASS = 56
TARGET_CLASSES = [PERSON_CLASS, CHAIR_CLASS]
DEFAULT_MODELS = [
    "yolo11n.pt",
    "yolov8n.pt",
    "yolov10n.pt",
    "yolov9t.pt",
    "dfine-n.pt",
    "dfine-s.pt",
    "rtdetr-l.pt",
]


def read_frame(env: dict[str, str]) -> np.ndarray:
    url = env.get("SNAPSHOT_URL", "")
    user = env.get("CCTV_USERNAME", "")
    password = env.get("CCTV_PASSWORD", "")
    if not url or not user or not password:
        raise SystemExit("SNAPSHOT_URL, CCTV_USERNAME, CCTV_PASSWORD wajib diisi")
    response = requests.get(url, params={"t": int(time.time() * 1000)}, auth=(user, password), timeout=20)
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise SystemExit(f"Response bukan image: HTTP {response.status_code}")
    frame = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise SystemExit("Snapshot gagal didecode OpenCV")
    return frame


def model_names() -> list[str]:
    raw = os.getenv("COMPARE_MODELS", "").strip()
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else DEFAULT_MODELS


def main() -> None:
    project = Path(__file__).resolve().parent
    env = {**dotenv_values(project / ".env"), **os.environ}
    frame = read_frame(env)
    output = project / "outputs" / "model-comparison"
    output.mkdir(parents=True, exist_ok=True)
    conf = float(env.get("CONFIDENCE", "0.25"))
    iou = float(env.get("IOU", "0.50"))
    imgsz = int(env.get("IMG_SIZE", "640"))
    device = env.get("DEVICE", "cpu")
    results: list[dict] = []

    for weights in model_names():
        row = {"model": weights, "status": "failed", "error": None}
        try:
            started = time.perf_counter()
            model = YOLO(weights)
            load_seconds = time.perf_counter() - started
            started = time.perf_counter()
            result = model.predict(frame, classes=TARGET_CLASSES, conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False)[0]
            inference_seconds = time.perf_counter() - started
            classes = result.boxes.cls.int().tolist() if result.boxes is not None else []
            counts = {"person": classes.count(PERSON_CLASS), "chair": classes.count(CHAIR_CLASS)}
            annotated = result.plot()
            label = f"{weights} person={counts['person']} chair={counts['chair']}"
            cv2.putText(annotated, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
            safe_name = Path(weights).stem.replace(".", "_")
            cv2.imwrite(str(output / f"{safe_name}.jpg"), annotated)
            row.update({"status": "ok", "counts": counts, "load_seconds": round(load_seconds, 4), "inference_seconds": round(inference_seconds, 4), "fps_estimate": round(1 / inference_seconds, 3) if inference_seconds else None, "output": f"{safe_name}.jpg"})
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))

    report = {"source": "authenticated_snapshot", "frame_width": int(frame.shape[1]), "frame_height": int(frame.shape[0]), "ground_truth": False, "classes": {"person": PERSON_CLASS, "chair": CHAIR_CLASS}, "parameters": {"conf": conf, "iou": iou, "imgsz": imgsz, "device": device}, "results": results}
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {output / 'results.json'}")


if __name__ == "__main__":
    main()
