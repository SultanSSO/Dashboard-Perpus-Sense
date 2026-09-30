"""Latest-frame RTSP/HLS/MJPEG worker for CCTV inference."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO

PERSON_CLASS = 0
CHAIR_CLASS = 56
TARGET_CLASSES = [PERSON_CLASS, CHAIR_CLASS]
INFERENCE_LOCK = threading.Lock()


@dataclass
class FrameResult:
    frame_rgb: np.ndarray | None = None
    person_count: int = 0
    chair_count: int = 0
    fps: float = 0.0
    latency: float = 0.0
    error: str | None = None
    frame_id: int = 0


class LatestFrameWorker:
    """Capture and inference threads; stale frames are deliberately dropped."""

    def __init__(self, source: str, model: YOLO, conf: float = 0.25, imgsz: int = 640, device: str = "cpu"):
        self.source = source
        self.model = model
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self.result = FrameResult()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.latest_frame: np.ndarray | None = None
        self.latest_id = 0
        self.last_inferred_id = -1
        self.capture_error: str | None = None

    def start(self) -> "LatestFrameWorker":
        self.capture_thread.start()
        self.inference_thread.start()
        return self

    def stop(self) -> None:
        self.stop_event.set()
        self.capture_thread.join(timeout=2)
        self.inference_thread.join(timeout=2)

    def snapshot(self) -> FrameResult:
        with self.lock:
            return FrameResult(
                frame_rgb=None if self.result.frame_rgb is None else self.result.frame_rgb.copy(),
                person_count=self.result.person_count,
                chair_count=self.result.chair_count,
                fps=self.result.fps,
                latency=self.result.latency,
                error=self.result.error,
                frame_id=self.result.frame_id,
            )

    def _capture_loop(self) -> None:
        transport = os.getenv("CCTV_RTSP_TRANSPORT", "tcp").lower()
        if transport not in {"tcp", "udp"}:
            transport = "tcp"
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}|stimeout;10000000"
        cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            with self.lock:
                self.capture_error = "RTSP gagal dibuka; periksa URL, VPN, port, dan credential"
            return
        try:
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    with self.lock:
                        self.capture_error = "Frame RTSP gagal dibaca"
                    time.sleep(0.2)
                    continue
                with self.lock:
                    self.latest_frame = frame
                    self.latest_id += 1
                    self.capture_error = None
        finally:
            cap.release()

    def _inference_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                frame = None if self.latest_frame is None else self.latest_frame.copy()
                frame_id = self.latest_id
                capture_error = self.capture_error
            if frame is None or frame_id == self.last_inferred_id:
                with self.lock:
                    self.result.error = capture_error or "Menunggu frame RTSP"
                time.sleep(0.01)
                continue
            started = time.perf_counter()
            try:
                with INFERENCE_LOCK:
                    result = self.model.track(
                        frame, persist=True, tracker="bytetrack.yaml", classes=TARGET_CLASSES,
                        conf=self.conf, imgsz=self.imgsz, device=self.device, verbose=False,
                    )[0]
                classes = result.boxes.cls.int().tolist() if result.boxes is not None else []
                person_count = classes.count(PERSON_CLASS)
                chair_count = classes.count(CHAIR_CLASS)
                annotated = cv2.cvtColor(result.plot(), cv2.COLOR_BGR2RGB)
                elapsed = time.perf_counter() - started
                with self.lock:
                    self.result = FrameResult(
                        frame_rgb=annotated, person_count=person_count, chair_count=chair_count,
                        fps=1 / elapsed if elapsed else 0, latency=elapsed, error=None, frame_id=frame_id,
                    )
                self.last_inferred_id = frame_id
            except Exception as exc:
                with self.lock:
                    self.result.error = f"Inference error: {type(exc).__name__}: {exc}"
                time.sleep(0.1)


__all__ = ["LatestFrameWorker", "FrameResult"]
