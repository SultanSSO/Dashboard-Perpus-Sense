"""Lifecycle manager for Vision Agent camera workers and task engine."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from vision_agent.mcp.service import CCTVServiceError, utc_now


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class RuntimeManager:
    """Start, stop, and inspect bounded Vision Agent subprocesses."""

    def __init__(
        self,
        project_dir: Path,
        *,
        catalog_path: Path | None = None,
        vision_path: Path | None = None,
        process_factory: Callable[..., Any] = subprocess.Popen,
        environment: dict[str, str] | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.catalog_path = catalog_path or self.project_dir / "config" / "camera_catalog.json"
        self.vision_path = vision_path or self.project_dir / "config" / "vision_agent.json"
        self.process_factory = process_factory
        self.environment = dict(os.environ if environment is None else environment)
        self._lock = threading.RLock()
        self._workers: dict[str, Any] = {}
        self._worker_logs: dict[str, Any] = {}
        self._task_engine: Any | None = None
        self._task_log: Any | None = None
        self._started_at: dict[str, str] = {}
        self._errors: dict[str, str] = {}
        self._stopped_by_user: set[str] = set()
        self._cameras, self._vision = self._load_config()

    def _load_config(self) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        try:
            catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            vision = json.loads(self.vision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("RUNTIME_CONFIG_INVALID", "Konfigurasi runtime tidak dapat dibaca") from exc
        catalog_by_id = {
            item["camera_id"]: item
            for item in catalog.get("cameras", [])
            if isinstance(item, dict) and item.get("camera_id")
        }
        configured: dict[str, dict[str, Any]] = {}
        for profile in vision.get("analysis_cameras", []):
            if not isinstance(profile, dict) or not profile.get("camera_id") or not profile.get("enabled", False):
                continue
            camera_id = profile["camera_id"]
            camera = catalog_by_id.get(camera_id)
            if camera and camera.get("operational_status") == "active":
                configured[camera_id] = {**camera, "runtime_profile": profile}
        return configured, vision

    def _camera(self, camera_id: str) -> dict[str, Any]:
        camera = self._cameras.get(camera_id)
        if camera is None:
            raise CCTVServiceError("CAMERA_NOT_CONFIGURED", f"Kamera tidak dikonfigurasi: {camera_id}")
        return camera

    def _source(self, camera: dict[str, Any]) -> str:
        override = self.environment.get("SNAPSHOT_URL", "").strip()
        catalog_id = str(camera.get("catalog_id", ""))
        camera_id = str(camera.get("camera_id", ""))
        if override and any(
            key and key in _source_key(override)
            for key in (_source_key(catalog_id), _source_key(camera_id))
        ):
            return override
        source = str(camera.get("snapshot_url_template") or camera.get("rtsp_url_template") or "").strip()
        if not source:
            raise CCTVServiceError("SOURCE_UNAVAILABLE", f"Source kamera belum tersedia: {camera_id}")
        return source

    @staticmethod
    def _running(process: Any | None) -> bool:
        return process is not None and process.poll() is None

    def _open_log(self, name: str):
        path = self.project_dir / "outputs" / "runtime" / "logs" / f"{_safe_id(name)}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("a", encoding="utf-8", buffering=1)

    def _spawn(self, command: list[str], name: str):
        log = self._open_log(name)
        kwargs = {
            "cwd": str(self.project_dir),
            "env": self.environment,
            "stdin": subprocess.DEVNULL,
            "stdout": log,
            "stderr": subprocess.STDOUT,
        }
        try:
            process = self.process_factory(command, **kwargs)
        except Exception:
            log.close()
            raise
        return process, log

    def start_camera(self, camera_id: str) -> dict[str, Any]:
        with self._lock:
            camera = self._camera(camera_id)
            existing = self._workers.get(camera_id)
            if self._running(existing):
                return self.camera_status(camera_id)
            if existing is not None:
                self._close_worker_log(camera_id)
            source = self._source(camera)
            model = str(self._vision.get("model", "yolo11n.pt"))
            device = str(self._vision.get("device", "auto"))
            command = [
                sys.executable,
                str(self.project_dir / "vision_cctv.py"),
                "--source", source,
                "--model", model,
                "--camera", camera_id,
                "--output-dir", str(self.project_dir / "outputs"),
                "--no-window",
            ]
            env = dict(self.environment)
            env["DEVICE"] = device
            original = self.environment
            self.environment = env
            try:
                process, log = self._spawn(command, f"camera-{camera_id}")
            finally:
                self.environment = original
            self._workers[camera_id] = process
            self._worker_logs[camera_id] = log
            self._started_at[camera_id] = utc_now()
            self._errors.pop(camera_id, None)
            self._stopped_by_user.discard(camera_id)
            return self.camera_status(camera_id)

    def _stop_process(self, process: Any | None, timeout: float = 10) -> None:
        if not self._running(process):
            return
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, TimeoutError):
            process.kill()
            process.wait(timeout=5)

    def _close_worker_log(self, camera_id: str) -> None:
        handle = self._worker_logs.pop(camera_id, None)
        if handle is not None and not handle.closed:
            handle.close()

    def stop_camera(self, camera_id: str) -> dict[str, Any]:
        with self._lock:
            self._camera(camera_id)
            process = self._workers.get(camera_id)
            self._stop_process(process)
            self._stopped_by_user.add(camera_id)
            self._close_worker_log(camera_id)
            return self.camera_status(camera_id)

    def restart_camera(self, camera_id: str) -> dict[str, Any]:
        self.stop_camera(camera_id)
        return self.start_camera(camera_id)

    def start_task_engine(self) -> dict[str, Any]:
        with self._lock:
            if self._running(self._task_engine):
                return self.task_engine_status()
            if self._task_log is not None and not self._task_log.closed:
                self._task_log.close()
            command = [sys.executable, "-m", "vision_agent.task_engine", "--poll-seconds", "5"]
            self._task_engine, self._task_log = self._spawn(command, "task-engine")
            return self.task_engine_status()

    def stop_task_engine(self) -> dict[str, Any]:
        with self._lock:
            self._stop_process(self._task_engine)
            if self._task_log is not None and not self._task_log.closed:
                self._task_log.close()
            return self.task_engine_status()

    def start_all(self, *, batch_size: int = 4, batch_delay: float = 1.0) -> dict[str, Any]:
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 16:
            raise CCTVServiceError("INVALID_ARGUMENT", "batch_size harus integer 1..16")
        if not isinstance(batch_delay, (int, float)) or isinstance(batch_delay, bool) or batch_delay < 0:
            raise CCTVServiceError("INVALID_ARGUMENT", "batch_delay harus angka non-negatif")
        camera_ids = list(self._cameras)
        for index, camera_id in enumerate(camera_ids):
            try:
                self.start_camera(camera_id)
            except (CCTVServiceError, OSError, ValueError) as exc:
                self._errors[camera_id] = str(exc)
            if batch_delay and (index + 1) % batch_size == 0 and index + 1 < len(camera_ids):
                time.sleep(batch_delay)
        self.start_task_engine()
        return self.status()

    def stop_all(self) -> dict[str, Any]:
        self.stop_task_engine()
        for camera_id in list(self._cameras):
            self.stop_camera(camera_id)
        return self.status()

    def restart_all(self, *, batch_size: int = 4, batch_delay: float = 1.0) -> dict[str, Any]:
        self.stop_all()
        return self.start_all(batch_size=batch_size, batch_delay=batch_delay)

    def camera_status(self, camera_id: str) -> dict[str, Any]:
        camera = self._camera(camera_id)
        process = self._workers.get(camera_id)
        running = self._running(process)
        exit_code = None if process is None or running else process.poll()
        expected_stop = camera_id in self._stopped_by_user
        error = self._errors.get(camera_id)
        if process is not None and not running and not expected_stop and exit_code not in {None, 0}:
            error = error or f"Worker berhenti dengan exit code {exit_code}"
            self._errors[camera_id] = error
        return {
            "camera_id": camera_id,
            "location": camera.get("location"),
            "running": running,
            "pid": process.pid if running else None,
            "exit_code": exit_code,
            "started_at": self._started_at.get(camera_id),
            "stopped_by_user": expected_stop,
            "error": error,
        }

    def task_engine_status(self) -> dict[str, Any]:
        running = self._running(self._task_engine)
        return {
            "running": running,
            "pid": self._task_engine.pid if running else None,
            "exit_code": None if self._task_engine is None or running else self._task_engine.poll(),
        }

    def status(self) -> dict[str, Any]:
        cameras = [self.camera_status(camera_id) for camera_id in self._cameras]
        running = sum(item["running"] for item in cameras)
        task_engine = self.task_engine_status()
        if running == 0 and not task_engine["running"]:
            system_status = "STOPPED"
        elif running == len(cameras) and task_engine["running"]:
            system_status = "RUNNING"
        else:
            system_status = "DEGRADED"
        return {
            "system_status": system_status,
            "configured_cameras": len(cameras),
            "workers_running": running,
            "workers_failed": sum(bool(item.get("error")) for item in cameras),
            "task_engine": task_engine,
            "cameras": cameras,
        }


__all__ = ["RuntimeManager"]
