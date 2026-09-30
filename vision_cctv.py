"""CCTV -> YOLO -> structured Vision Agent events.

Input: RTSP, HLS, MJPEG, webcam index, or local video.
Default: anonymous person detection/tracking only. No face recognition.
"""
from __future__ import annotations

import argparse
import json
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
TARGET_CLASSES = [PERSON_CLASS, CHAIR_CLASS]


def point_list(raw: str):
    if not raw.strip():
        return []
    return [tuple(map(int, p.split(","))) for p in raw.split(";")]


def side_of_line(point, line, margin=8):
    (x1, y1), (x2, y2) = line
    value = (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)
    if abs(value) <= margin * max(abs(x2 - x1) + abs(y2 - y1), 1):
        return 0
    return -1 if value < 0 else 1


def parse_source(value: str):
    return int(value) if value.isdigit() else value


def resolve_source(explicit: str, snapshot: str, stream: str) -> str:
    """Select CLI source first, then snapshot, then stream."""
    return (explicit or snapshot or stream or "").strip()


def safe_source(value: str):
    """Remove password from logged event source."""
    return re.sub(r"(://[^:/]+:)[^@]+(@)", r"\1***\2", str(value))


def latest_snapshot_path(output_dir: Path, camera_id: str) -> Path:
    safe_camera_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(camera_id))
    return output_dir / f"latest_{safe_camera_id}.jpg"


def write_latest_snapshot(output_dir: Path, camera_id: str, frame) -> Path:
    target = latest_snapshot_path(output_dir, camera_id)
    encoded_ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not encoded_ok:
        raise RuntimeError("Snapshot gagal diencode sebagai JPEG")
    temporary = target.with_suffix(".tmp.jpg")
    temporary.write_bytes(encoded.tobytes())
    for attempt in range(6):
        try:
            os.replace(temporary, target)
            return target
        except PermissionError:
            if attempt == 5:
                temporary.unlink(missing_ok=True)
                if target.exists():
                    return target
                raise
            time.sleep(0.05 * (attempt + 1))

def is_snapshot_source(value: str) -> bool:
    return str(value).lower().startswith(("http://", "https://"))


def read_snapshot(url: str, username: str, password: str):
    response = requests.get(url, params={"t": int(time.time() * 1000)}, auth=(username, password), timeout=15)
    response.raise_for_status()
    if not response.headers.get("content-type", "").lower().startswith("image/"):
        raise RuntimeError(f"Response snapshot bukan image: HTTP {response.status_code}")
    image = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Response bukan image yang dapat dibaca OpenCV")
    return image


def snapshot_retry_delay(attempt: int) -> int:
    """Return bounded exponential backoff for transient snapshot failures."""
    return min(30, 2 ** max(0, attempt - 1))


def infer_frame(model, frame, mode, conf, iou, imgsz, device):
    if mode == "predict":
        return model.predict(frame, classes=TARGET_CLASSES, conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False)[0]
    return model.track(frame, persist=True, tracker="bytetrack.yaml", classes=TARGET_CLASSES, conf=conf, iou=iou, imgsz=imgsz, device=device, verbose=False)[0]


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Anonymous CCTV analytics with YOLO")
    parser.add_argument("--source", default="")
    parser.add_argument("--model", default=os.getenv("MODEL_PATH", "yolo11n.pt"))
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_DIR", "outputs"))
    parser.add_argument("--camera", default=os.getenv("CAMERA_ID", ""))
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()
    source = resolve_source(args.source, os.getenv("SNAPSHOT_URL", ""), os.getenv("STREAM_URL", ""))
    if not source:
        raise SystemExit("STREAM_URL atau SNAPSHOT_URL belum diisi.")

    conf = float(os.getenv("CONFIDENCE", "0.35"))
    iou = float(os.getenv("IOU", "0.50"))
    imgsz = int(os.getenv("IMG_SIZE", "640"))
    device = os.getenv("DEVICE", "cpu")
    if device in {"auto", "cuda", "gpu", "0"}:
        try:
            import torch
            if device == "auto":
                device = "0" if torch.cuda.is_available() else "cpu"
            elif device != "0" or not torch.cuda.is_available():
                device = "cpu"
        except ModuleNotFoundError:
            device = "cpu"
    every = max(1, int(os.getenv("INFER_EVERY_N_FRAMES", "1")))
    snapshot_interval = max(0.1, float(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "0.2")))
    snapshot_mode_name = os.getenv("SNAPSHOT_INFERENCE_MODE", "predict").lower()
    if snapshot_mode_name not in {"predict", "track"}:
        raise SystemExit("SNAPSHOT_INFERENCE_MODE harus predict atau track.")
    cctv_user = os.getenv("CCTV_USERNAME", "")
    cctv_password = os.getenv("CCTV_PASSWORD", "")
    show = os.getenv("SHOW_WINDOW", "false").lower() == "true" and not args.no_window
    zone = point_list(os.getenv("ZONE_POLYGON", ""))
    line = point_list(os.getenv("FLOW_LINE", ""))
    if zone and len(zone) < 3:
        raise SystemExit("ZONE_POLYGON perlu minimal 3 titik: x,y;x,y;x,y")
    if line and len(line) != 2:
        raise SystemExit("FLOW_LINE perlu 2 titik: x,y;x,y")
    zone_polygon = np.array(zone, dtype="int32") if zone else None

    model = YOLO(args.model)
    camera_id = args.camera or Path(source.split("?", 1)[0]).stem
    snapshot_mode = is_snapshot_source(source)
    cap = None if snapshot_mode else cv2.VideoCapture(parse_source(source))
    if not snapshot_mode and not cap.isOpened():
        raise SystemExit("Stream gagal dibuka. Periksa endpoint, VPN, jaringan, codec, dan izin read-only.")
    if snapshot_mode and (not cctv_user or not cctv_password):
        raise SystemExit("CCTV_USERNAME/CCTV_PASSWORD belum diisi untuk snapshot endpoint.")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "events.jsonl"
    writer = None
    frame_no = 0
    track_sides = {}
    flow_count = Counter()
    last_event = 0.0
    snapshot_failures = 0

    try:
        while True:
            cycle_started = time.perf_counter()
            if snapshot_mode:
                try:
                    frame = read_snapshot(source, cctv_user, cctv_password)
                    snapshot_failures = 0
                except requests.HTTPError as exc:
                    status = exc.response.status_code if exc.response is not None else None
                    if status in {401, 403}:
                        raise SystemExit(f"Snapshot gagal: HTTP {status}; credential ditolak") from exc
                    snapshot_failures += 1
                    delay = snapshot_retry_delay(snapshot_failures)
                    print(f"Snapshot sementara gagal: HTTP {status}; retry {delay}s", flush=True)
                    time.sleep(delay)
                    continue
                except requests.RequestException as exc:
                    snapshot_failures += 1
                    delay = snapshot_retry_delay(snapshot_failures)
                    print(f"Snapshot sementara gagal: {type(exc).__name__}; retry {delay}s", flush=True)
                    time.sleep(delay)
                    continue
                ok = True
            else:
                ok, frame = cap.read()
                if not ok:
                    print("Frame gagal dibaca; stream berhenti atau koneksi putus.")
                    break
            frame_no += 1
            if frame_no % every != 0:
                continue
            h, w = frame.shape[:2]
            if writer is None:
                fps = (cap.get(cv2.CAP_PROP_FPS) if cap is not None else 1.0) or 15.0
                writer = cv2.VideoWriter(str(out_dir / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            started_inference = time.perf_counter()
            result = infer_frame(model, frame, snapshot_mode_name if snapshot_mode else "track", conf, iou, imgsz, device)
            annotated = result.plot()
            ids = result.boxes.id.int().tolist() if result.boxes is not None and result.boxes.id is not None else []
            classes = result.boxes.cls.int().tolist() if result.boxes is not None else []
            boxes = result.boxes.xyxy.tolist() if result.boxes is not None else []
            counts = Counter({"person": 0, "chair": 0})
            zone_counts = Counter({"person": 0, "chair": 0})
            for idx, box in enumerate(boxes):
                cls = classes[idx]
                if cls == PERSON_CLASS:
                    counts["person"] += 1
                elif cls == CHAIR_CLASS:
                    counts["chair"] += 1
                else:
                    continue
                x1, y1, x2, y2 = box
                center = (int((x1+x2)/2), int((y1+y2)/2))
                inside = not zone or cv2.pointPolygonTest(zone_polygon, center, False) >= 0
                if inside:
                    zone_counts["person" if cls == PERSON_CLASS else "chair"] += 1
                if cls == PERSON_CLASS and line and idx < len(ids):
                    tid = ids[idx]
                    side = side_of_line(center, line)
                    old = track_sides.get(tid)
                    if side and old and side != old:
                        flow_count["person"] += 1
                    if side:
                        track_sides[tid] = side
            if zone:
                cv2.polylines(annotated, [zone_polygon], True, (0, 255, 255), 2)
            if line:
                cv2.line(annotated, line[0], line[1], (255, 0, 255), 2)
            write_latest_snapshot(out_dir, camera_id, frame)
            writer.write(annotated)
            inference_seconds = time.perf_counter() - started_inference
            cycle_seconds = max(time.perf_counter() - cycle_started, 1e-9)
            if snapshot_mode:
                time.sleep(max(0, snapshot_interval - cycle_seconds))

            now = time.time()
            if now - last_event >= 1.0:
                event = {
                    "schema_version": "vision.event.v1",
                    "event_id": f"cctv-{frame_no}-{int(now*1000)}",
                    "event_type": "occupancy_update",
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "source": {"camera_id": camera_id, "stream": safe_source(source), "zone_id": "configured-zone" if zone else None},
                    "measurement": {
                        "person_count": counts["person"],
                        "chair_count": counts["chair"],
                        "occupancy": zone_counts["person"] if zone else counts["person"],
                        "zone_person_count": zone_counts["person"] if zone else None,
                        "zone_chair_count": zone_counts["chair"] if zone else None,
                        "flow_crossings": flow_count["person"],
                    },
                    "confidence": conf,
                    "privacy": {"identity_mode": "anonymous", "face_recognition": False},
                    "quality": {"stream_ok": True, "frame_width": w, "frame_height": h, "inference_seconds": round(inference_seconds, 4), "cycle_seconds": round(cycle_seconds, 4)},
                }
                with events_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
                print(json.dumps(event, ensure_ascii=False))
                last_event = now
            if show:
                cv2.imshow("Vision Agent CCTV", annotated)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
            if args.max_frames and frame_no >= args.max_frames:
                break
    finally:
        if cap is not None:
            cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

# Integration note: replace local JSONL sink with Vision Agent API/event bus after schema approval.
# Do not put CCTV passwords in source code or commit .env.
