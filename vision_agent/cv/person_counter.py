"""Detect and count people from image, video, webcam, or CCTV stream.

Default model: RT-DETR-L. Counting means people visible in current frame.
No face recognition. No identity tracking.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np
import requests
try:
    import torch
except ModuleNotFoundError:  # Counting helpers/tests can run without PyTorch.
    torch = None
from dotenv import load_dotenv
from ultralytics import YOLO

PERSON_CLASS = 0


def count_people(class_ids) -> int:
    """Return number of detections whose COCO class ID is person (0)."""
    if class_ids is None:
        return 0
    if hasattr(class_ids, "int"):
        class_ids = class_ids.int().tolist()
    return sum(int(class_id) == PERSON_CLASS for class_id in class_ids)


def parse_source(value: str):
    return int(value) if value.isdigit() else value


def build_rtsp_url() -> str:
    """Build native Hikvision RTSP URL from .env values."""
    explicit = os.getenv("CCTV_RTSP_URL", "").strip()
    if explicit:
        return explicit
    host = os.getenv("CCTV_HOST", "CAMERA_HOST").strip()
    channel = os.getenv("CCTV_CHANNEL", "13").strip().zfill(2)
    username = os.getenv("CCTV_USERNAME", "").strip()
    password = os.getenv("CCTV_PASSWORD", "").strip()
    if not username or not password:
        return ""
    return (
        f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@"
        f"{host}:554/Streaming/Channels/{channel}02"
    )


def select_device(requested: str) -> str:
    """Use CUDA when available, otherwise CPU."""
    requested = (requested or "auto").strip().lower()
    if requested in {"auto", "cuda", "gpu", "0"}:
        if torch is not None and torch.cuda.is_available():
            return "0"
        if requested != "auto":
            print("CUDA tidak tersedia; fallback ke CPU.")
        return "cpu"
    return requested


def is_snapshot_url(value: str) -> bool:
    """Return true for HTTP(S) snapshot endpoints, including extensionless URLs."""
    value = str(value).strip().lower()
    return value.startswith(("http://", "https://"))


def is_local_image(value: str) -> bool:
    """Return true for an existing local image path."""
    path = Path(value).expanduser()
    return path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def safe_source(value: str) -> str:
    """Hide RTSP password in logs and summary."""
    if "@" not in value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{host}"
    return value


def read_snapshot(url: str, username: str, password: str):
    response = requests.get(
        url,
        params={"t": int(time.time() * 1000)},
        auth=(username, password),
        timeout=15,
    )
    response.raise_for_status()
    if not response.headers.get("content-type", "").lower().startswith("image/"):
        raise RuntimeError(f"Response snapshot bukan image: HTTP {response.status_code}")
    frame = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("Snapshot gagal didecode OpenCV")
    return frame


def detect_frame(model, frame, conf: float, iou: float, imgsz: int, device: str):
    """Run inference; fallback to CPU if CUDA fails at runtime."""
    if torch is None:
        raise RuntimeError("PyTorch belum terpasang. Install dependency project sebelum inference.")
    kwargs = {
        "classes": [PERSON_CLASS],
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "device": device,
        "verbose": False,
    }
    try:
        return model.predict(frame, **kwargs)[0], device
    except (RuntimeError, AssertionError, OSError) as exc:
        if device != "cpu":
            print(f"CUDA inference gagal ({type(exc).__name__}); fallback ke CPU.")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            kwargs["device"] = "cpu"
            return model.predict(frame, **kwargs)[0], "cpu"
        raise


def device_label(device: str) -> str:
    if device == "0" and torch is not None and torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return "CPU"


def annotate(result, people: int):
    frame = result.plot()
    cv2.putText(
        frame,
        f"PEOPLE: {people}",
        (15, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return frame


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="RT-DETR person detector and counter")
    parser.add_argument("--source", default=os.getenv("PERSON_SOURCE", ""))
    parser.add_argument("--model", default=os.getenv("PERSON_MODEL", os.getenv("MODEL_PATH", "rtdetr-l.pt")))
    parser.add_argument("--output-dir", default=os.getenv("PERSON_OUTPUT_DIR", "outputs/person-counter"))
    parser.add_argument("--conf", type=float, default=float(os.getenv("PERSON_CONFIDENCE", os.getenv("CONFIDENCE", "0.35"))))
    parser.add_argument("--iou", type=float, default=float(os.getenv("PERSON_IOU", os.getenv("IOU", "0.50"))))
    parser.add_argument("--imgsz", type=int, default=int(os.getenv("PERSON_IMG_SIZE", os.getenv("IMG_SIZE", "960"))))
    parser.add_argument("--device", default=os.getenv("PERSON_DEVICE", os.getenv("DEVICE", "auto")))
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args()

    snapshot_url = os.getenv("SNAPSHOT_URL", "").strip()
    if not args.source:
        # Snapshot HTTP diprioritaskan; RTSP hanya fallback jika snapshot belum diisi.
        args.source = snapshot_url or build_rtsp_url()
    snapshot_mode = is_snapshot_url(args.source)
    local_image_mode = is_local_image(args.source)
    if not args.source:
        raise SystemExit("Source belum diisi. Isi CCTV_HOST/CCTV_CHANNEL/CCTV_USERNAME/CCTV_PASSWORD di .env")
    if not snapshot_mode and not local_image_mode and not args.source.isdigit() and not str(args.source).lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        raise SystemExit(f"Source lokal tidak ditemukan atau format tidak didukung: {args.source}")
    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path
    if not model_path.is_file():
        raise SystemExit(f"Model tidak ditemukan: {model_path}")
    if snapshot_mode and (not os.getenv("CCTV_USERNAME") or not os.getenv("CCTV_PASSWORD")):
        raise SystemExit("CCTV_USERNAME/CCTV_PASSWORD belum diisi untuk SNAPSHOT_URL")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = select_device(args.device)
    gpu_name = torch.cuda.get_device_name(0) if torch is not None and device == "0" else "CPU"
    print(f"Device: {device} ({gpu_name})")
    model = YOLO(str(model_path))
    source = parse_source(args.source)
    cap = None
    local_frame = None
    if local_image_mode:
        local_frame = cv2.imread(str(Path(args.source).expanduser()), cv2.IMREAD_COLOR)
        if local_frame is None:
            raise SystemExit(f"Gambar lokal gagal dibaca: {args.source}")
    elif not snapshot_mode:
        # RTSP via TCP reduces packet loss and stale frames on CCTV LAN.
        transport = os.getenv("CCTV_RTSP_TRANSPORT", "tcp").strip().lower()
        if transport not in {"tcp", "udp"}:
            raise SystemExit("CCTV_RTSP_TRANSPORT harus tcp atau udp")
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}|stimeout;10000000"
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    if not snapshot_mode and not local_image_mode and not cap.isOpened():
        redacted = safe_source(str(args.source))
        reason = "credential RTSP ditolak (401), atau host/port/path tidak dapat diakses"
        raise SystemExit(f"Source RTSP gagal dibuka: {redacted}; {reason}. Periksa akun RTSP dan akses LAN/VPN.")

    writer = None
    frame_no = 0
    max_people = 0
    total_people_samples = 0
    started_all = time.perf_counter()
    events_path = output_dir / "people_counts.jsonl"
    show = not args.no_window

    try:
        while True:
            if snapshot_mode:
                try:
                    frame = read_snapshot(args.source, os.getenv("CCTV_USERNAME", ""), os.getenv("CCTV_PASSWORD", ""))
                except requests.RequestException as exc:
                    raise SystemExit(f"Snapshot gagal diambil: {exc}") from exc
                ok = True
            elif local_image_mode:
                if frame_no >= 1:
                    break
                frame = local_frame
                ok = True
            else:
                ok, frame = cap.read()
                if not ok:
                    break
            frame_no += 1
            result, device = detect_frame(model, frame, args.conf, args.iou, args.imgsz, device)
            class_ids = result.boxes.cls if result.boxes is not None else None
            people = count_people(class_ids)
            max_people = max(max_people, people)
            total_people_samples += people
            annotated = annotate(result, people)

            if writer is None:
                height, width = annotated.shape[:2]
                fps = (cap.get(cv2.CAP_PROP_FPS) if cap is not None else 1.0) or 15.0
                writer = cv2.VideoWriter(
                    str(output_dir / "people_annotated.mp4"),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps,
                    (width, height),
                )
            writer.write(annotated)
            event = {"frame": frame_no, "people_visible": people}
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")
            print(json.dumps(event))

            if show:
                cv2.imshow("RT-DETR Person Counter", annotated)
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

    elapsed = max(time.perf_counter() - started_all, 1e-9)
    summary = {
        "model": str(model_path),
        "source": safe_source(str(args.source)),
        "ground_truth": False,
        "counting_semantics": "people visible in current frame; not unique people over time",
        "frames_processed": frame_no,
        "peak_people_visible": max_people,
        "mean_people_visible": round(total_people_samples / frame_no, 3) if frame_no else 0,
        "elapsed_seconds": round(elapsed, 3),
        "processing_fps": round(frame_no / elapsed, 3) if frame_no else 0,
        "parameters": {"conf": args.conf, "iou": args.iou, "imgsz": args.imgsz, "device": device},
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
