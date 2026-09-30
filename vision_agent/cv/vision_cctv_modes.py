"""CCTV detector with selectable analysis modes.

Modes: person, chair, both, empty-chair, density.
Empty-chair uses bbox-center proximity heuristic. Density uses configured capacity.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from ultralytics import YOLO

PERSON_CLASS = 0
CHAIR_CLASS = 56
MODE_CLASSES = {
    "person": [PERSON_CLASS],
    "chair": [CHAIR_CLASS],
    "both": [PERSON_CLASS, CHAIR_CLASS],
    "empty-chair": [PERSON_CLASS, CHAIR_CLASS],
    "density": [PERSON_CLASS],
}
TASK_MENU = [
    ("a", "person", "Deteksi orang"),
    ("b", "chair", "Deteksi kursi"),
    ("c", "both", "Deteksi orang dan kursi"),
    ("d", "density", "Deteksi kepadatan"),
]
MODE_ALIASES = {
    "a": "person", "b": "chair", "c": "both", "d": "density", "e": "empty-chair",
    "people": "person", "chairs": "chair", "empty": "empty-chair",
}


def available_models(project: Path) -> list[str]:
    return sorted(path.name for path in project.glob("*.pt") if path.is_file())


def choose_model(project: Path) -> str:
    models = available_models(project)
    if not models:
        raise SystemExit(f"Tidak ada file model .pt di {project}")
    print("\nPilih model:")
    for index, name in enumerate(models, 1):
        print(f"  {index}. {name}")
    while True:
        choice = input("Model [1]: ").strip() or "1"
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1]
        print(f"Pilihan tidak valid. Gunakan angka 1-{len(models)}")


def choose_task() -> str:
    print("\nPilih task:")
    for key, mode, label in TASK_MENU:
        print(f"  {key}. {label}")
    while True:
        choice = input("Task [a]: ").strip().lower() or "a"
        for key, mode, _ in TASK_MENU:
            if choice == key:
                return mode
        print("Pilihan tidak valid. Gunakan a, b, c, atau d")


def resolve_source(explicit: str, snapshot: str, stream: str) -> str:
    """Select explicit CLI source, then snapshot, then stream."""
    return (explicit or snapshot or stream or "").strip()


def normalize_mode(value: str) -> str:
    mode = MODE_ALIASES.get(str(value).strip().lower(), str(value).strip().lower())
    if mode not in MODE_CLASSES:
        raise ValueError("mode harus a-e, person, chair, both, empty-chair, atau density")
    return mode


def classify_density(people: int, capacity: int) -> dict:
    if capacity <= 0:
        raise ValueError("capacity harus lebih besar dari 0")
    ratio = people / capacity
    if ratio < 0.50:
        level = "low"
    elif ratio < 0.80:
        level = "medium"
    elif ratio < 1.00:
        level = "high"
    else:
        level = "critical"
    return {"level": level, "ratio": round(ratio, 3), "capacity": capacity}


def center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def count_empty_chairs(chairs, people, max_distance: float = 80.0) -> int:
    """Count chairs with no person bbox center within max_distance pixels."""
    person_centers = [center(box) for box in people]
    empty = 0
    for chair in chairs:
        cx, cy = center(chair)
        occupied = any(math.dist((cx, cy), person) <= max_distance for person in person_centers)
        empty += not occupied
    return empty


def safe_source(value: str) -> str:
    return re.sub(r"(://[^:/]+:)[^@]+(@)", r"\1***\2", str(value))


def startup_info(mode: str, model: str, source: str, device: str) -> dict:
    return {
        "status": "VIDEO AKTIF",
        "task": mode,
        "model": Path(model).name,
        "source": safe_source(source),
        "device": device,
    }


def print_startup(info: dict) -> None:
    print("\n" + "=" * 58)
    print("VISION CCTV | VIDEO AKTIF")
    print("=" * 58)
    print(f"Task   : {info['task']}")
    print(f"Model  : {info['model']}")
    print(f"Source : {info['source']}")
    print(f"Device : {info['device']}")
    print("Status : berjalan | tekan q atau Esc untuk berhenti")
    print("=" * 58)


def print_progress(frame_no: int, metrics: dict, elapsed: float) -> None:
    fps = frame_no / elapsed if elapsed > 0 else 0.0
    extra = ""
    if "density" in metrics:
        extra = f" | density={metrics['density']['level']}"
    if "empty_chair_count" in metrics:
        extra += f" | empty_chair={metrics['empty_chair_count']}"
    print(
        f"[INFO] frame={frame_no} | person={metrics.get('person_count', 0)}"
        f" | chair={metrics.get('chair_count', 0)}{extra} | fps={fps:.2f}"
    )


def is_snapshot_source(value: str) -> bool:
    lower = str(value).lower()
    return lower.startswith(("http://", "https://")) and ".m3u8" not in lower


def read_snapshot(url: str, username: str, password: str):
    response = requests.get(
        url,
        params={"t": int(time.time() * 1000)},
        auth=(username, password),
        headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*,*/*;q=0.8"},
        timeout=15,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    frame = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError(
            f"Response snapshot bukan image: HTTP {response.status_code}, content-type={content_type or 'unknown'}"
        )
    return frame


def result_boxes(result):
    if result.boxes is None:
        return [], [], []
    classes = result.boxes.cls.int().tolist()
    boxes = result.boxes.xyxy.tolist()
    return classes, boxes, result.boxes.conf.tolist()


def annotate_result(result, mode: str, capacity: int, chair_distance: float):
    classes, boxes, confidences = result_boxes(result)
    people = [box for cls, box in zip(classes, boxes) if cls == PERSON_CLASS]
    chairs = [box for cls, box in zip(classes, boxes) if cls == CHAIR_CLASS]
    counts = {"person": len(people), "chair": len(chairs)}
    metrics = {"person_count": counts["person"], "chair_count": counts["chair"]}
    if mode == "empty-chair":
        metrics["empty_chair_count"] = count_empty_chairs(chairs, people, chair_distance)
    if mode == "density":
        metrics["density"] = classify_density(len(people), capacity)
    annotated = result.plot()
    label = f"mode={mode} person={counts['person']} chair={counts['chair']}"
    if "empty_chair_count" in metrics:
        label += f" empty={metrics['empty_chair_count']}"
    if "density" in metrics:
        label += f" density={metrics['density']['level']}"
    cv2.putText(annotated, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return annotated, metrics


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="CCTV detector dengan mode analisis")
    parser.add_argument("--mode", default="", help="a-d atau nama task; tanpa argumen tampil menu")
    # Keep CLI override separate; source precedence is CLI -> snapshot -> stream.
    parser.add_argument("--source", default="")
    parser.add_argument("--model", default="", help="nama file model .pt; tanpa argumen tampil menu")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_DIR", "outputs/modes"))
    parser.add_argument("--camera", default=os.getenv("CAMERA_ID", "camera"))
    parser.add_argument("--conf", type=float, default=float(os.getenv("CONFIDENCE", "0.35")))
    parser.add_argument("--iou", type=float, default=float(os.getenv("IOU", "0.50")))
    parser.add_argument("--imgsz", type=int, default=int(os.getenv("IMG_SIZE", "640")))
    parser.add_argument("--device", default=os.getenv("DEVICE", "cpu"))
    parser.add_argument("--capacity", type=int, default=int(os.getenv("DENSITY_CAPACITY", "20")))
    parser.add_argument("--chair-distance", type=float, default=float(os.getenv("CHAIR_PERSON_DISTANCE", "80")))
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[2]
    if not args.model and not args.mode:
        args.model = choose_model(project)
        args.mode = choose_task()
    else:
        args.model = args.model or os.getenv("MODEL_PATH", "yolo11n.pt")
        args.mode = args.mode or os.getenv("VISION_MODE", "a")
    try:
        mode = normalize_mode(args.mode)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    source = resolve_source(args.source, os.getenv("SNAPSHOT_URL", ""), os.getenv("STREAM_URL", ""))
    if not source:
        raise SystemExit("STREAM_URL atau SNAPSHOT_URL belum diisi")
    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = project / model_path
    if not model_path.is_file():
        raise SystemExit(f"Model tidak ditemukan: {model_path}")
    snapshot = is_snapshot_source(source)
    user, password = os.getenv("CCTV_USERNAME", ""), os.getenv("CCTV_PASSWORD", "")
    if snapshot and (not user or not password):
        raise SystemExit("CCTV_USERNAME/CCTV_PASSWORD wajib untuk snapshot")
    if mode == "density" and args.capacity <= 0:
        raise SystemExit("--capacity harus lebih besar dari 0")

    model = YOLO(str(model_path))
    device = args.device
    if device in {"auto", "cuda", "gpu", "0"}:
        try:
            import torch
            device = "0" if torch.cuda.is_available() else "cpu"
        except ModuleNotFoundError:
            device = "cpu"
    cap = None if snapshot else cv2.VideoCapture(int(source) if source.isdigit() else source, cv2.CAP_FFMPEG)
    if not snapshot and not cap.isOpened():
        raise SystemExit(f"Stream gagal dibuka: {safe_source(source)}")
    print_startup(startup_info(mode, str(model_path), source, device))
    out_dir = Path(args.output_dir) / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "events.jsonl"
    writer = None
    frame_no = 0
    started = time.perf_counter()
    last_progress = started
    try:
        while True:
            if snapshot:
                try:
                    frame = read_snapshot(source, user, password)
                except (requests.RequestException, RuntimeError) as exc:
                    raise SystemExit(f"Snapshot gagal: {exc}. Gunakan URL JPEG langsung, bukan halaman CCTV HTML.") from exc
            else:
                ok, frame = cap.read()
                if not ok:
                    break
            frame_no += 1
            result = model.predict(frame, classes=MODE_CLASSES[mode], conf=args.conf, iou=args.iou, imgsz=args.imgsz, device=device, verbose=False)[0]
            annotated, metrics = annotate_result(result, mode, args.capacity, args.chair_distance)
            if writer is None:
                h, w = annotated.shape[:2]
                fps = (cap.get(cv2.CAP_PROP_FPS) if cap is not None else 1.0) or 15.0
                writer = cv2.VideoWriter(str(out_dir / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            writer.write(annotated)
            event = {"schema_version": "vision.event.v1", "mode": mode, "frame": frame_no, "observed_at": datetime.now(timezone.utc).isoformat(), "source": safe_source(source), "measurement": metrics, "ground_truth": False}
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            now = time.perf_counter()
            if frame_no == 1 or now - last_progress >= 5.0:
                print_progress(frame_no, metrics, now - started)
                last_progress = now
            if not args.no_window:
                cv2.imshow(f"CCTV - {mode}", annotated)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
            if args.max_frames and frame_no >= args.max_frames:
                break
    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
    elapsed = max(time.perf_counter() - started, 1e-9)
    print("\n" + "=" * 58)
    print(f"SELESAI | frame={frame_no} | durasi={elapsed:.1f}s | fps={frame_no / elapsed:.2f}")
    print(f"Output : {out_dir}")
    print("=" * 58)


if __name__ == "__main__":
    main()
