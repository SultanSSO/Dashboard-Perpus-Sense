"""Serve the static dashboard and a read-only CCTV data API."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

from vision_agent.mcp.service import CCTVService, CCTVServiceError, utc_now
from vision_agent.runtime_manager import RuntimeManager

load_dotenv()


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """Expose dashboard assets and a same-origin API backed by CCTVService."""

    service: CCTVService
    runtime: RuntimeManager

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the operator console focused on startup and API errors.
        if self.path.startswith("/api/"):
            return
        super().log_message(format, *args)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, error: CCTVServiceError) -> None:
        status = 403 if error.code == "ACTION_DENIED" else 400
        self._send_json({"error": {"code": error.code, "message": error.message}}, status)

    def _snapshot_path(self, camera_id: str) -> Path:
        self.service.get_metadata(camera_id)
        safe_camera_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", camera_id)
        return self.service.paths.events.parent / f"latest_{safe_camera_id}.jpg"

    def _send_snapshot(self, camera_id: str) -> None:
        snapshot = self._snapshot_path(camera_id)
        if not snapshot.exists():
            raise CCTVServiceError("SNAPSHOT_UNAVAILABLE", "Snapshot terbaru belum tersedia")
        body = snapshot.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _bool(query: dict[str, list[str]], name: str, default: bool = False) -> bool:
        value = query.get(name, [str(default).lower()])[0].strip().lower()
        return value in {"1", "true", "yes", "on"}

    @staticmethod
    def _int(query: dict[str, list[str]], name: str, default: int) -> int:
        try:
            return int(query.get(name, [str(default)])[0])
        except ValueError as exc:
            raise CCTVServiceError("INVALID_ARGUMENT", f"{name} harus integer") from exc

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise CCTVServiceError("INVALID_ARGUMENT", "Content-Length tidak valid") from exc
        if not 0 < length <= 16_384:
            raise CCTVServiceError("INVALID_ARGUMENT", "Body JSON wajib diisi dan maksimal 16 KB")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("INVALID_ARGUMENT", "Body JSON tidak valid") from exc
        if not isinstance(payload, dict):
            raise CCTVServiceError("INVALID_ARGUMENT", "Body harus berupa object JSON")
        return payload

    def _require_local_mutation(self) -> None:
        if os.getenv("MCP_ENABLE_MUTATIONS", "false").casefold() != "true":
            raise CCTVServiceError("ACTION_DENIED", "Mutasi task dinonaktifkan")
        try:
            is_loopback = ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            raise CCTVServiceError("ACTION_DENIED", "Pengaturan agent hanya tersedia dari localhost")
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            raise CCTVServiceError("ACTION_DENIED", "Origin pengaturan agent tidak diizinkan")

    def _overview(self) -> dict[str, Any]:
        catalog = self.service.list_cameras(limit=200)
        analysis = [camera for camera in catalog["items"] if camera.get("analysis_enabled")]
        observations: dict[str, Any] = {}
        statuses: dict[str, Any] = {}
        for camera in analysis:
            camera_id = camera["camera_id"]
            observations[camera_id] = self.service.current_observation(camera_id)
            statuses[camera_id] = self.service.get_status(camera_id)
        return {
            "generated_at": utc_now(),
            "health": self.service.health(),
            "catalog": catalog,
            "analysis_cameras": analysis,
            "observations": observations,
            "statuses": statuses,
            "events": self.service.events(limit=30)["items"],
            "tasks": self.service.list_tasks(limit=50)["items"],
            "alerts": self.service.active_alerts(),
        }

    def _api(self, path: str, query: dict[str, list[str]]) -> Any:
        parts = [unquote(part) for part in path.split("/") if part]
        if parts[:2] != ["api", "v1"]:
            raise CCTVServiceError("NOT_FOUND", "API endpoint tidak ditemukan")
        route = parts[2:]
        if route == ["health"]:
            return self.service.health()
        if route == ["overview"]:
            return self._overview()
        if route == ["agent", "settings"]:
            return self.service.agent_settings()
        if route == ["runtime", "status"]:
            return self.runtime.status()
        if route == ["cameras"]:
            return self.service.list_cameras(
                status=query.get("status", [None])[0],
                location=query.get("location", [None])[0],
                analysis_only=self._bool(query, "analysis_only"),
                limit=self._int(query, "limit", 100),
                offset=self._int(query, "offset", 0),
            )
        if len(route) == 3 and route[0] == "cameras" and route[2] in {"observation", "status", "metadata"}:
            camera_id = route[1]
            if route[2] == "observation":
                return self.service.current_observation(camera_id)
            if route[2] == "status":
                return self.service.get_status(camera_id)
            return self.service.get_metadata(camera_id)
        if route == ["events"]:
            return self.service.events(
                camera_id=query.get("camera_id", [None])[0],
                event_type=query.get("event_type", [None])[0],
                start=query.get("start", [None])[0],
                end=query.get("end", [None])[0],
                limit=self._int(query, "limit", 50),
            )
        if route == ["summary"]:
            raw_ids = query.get("camera_ids", [""])[0]
            camera_ids = [item for item in raw_ids.split(",") if item] or None
            return self.service.summary(
                camera_ids=camera_ids,
                start=query.get("start", [None])[0],
                end=query.get("end", [None])[0],
            )
        if route == ["tasks"]:
            return self.service.list_tasks(
                status=query.get("status", [None])[0],
                limit=self._int(query, "limit", 50),
            )
        raise CCTVServiceError("NOT_FOUND", "API endpoint tidak ditemukan")
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) == 5 and parts[:3] == ["api", "v1", "cameras"] and parts[4] == "snapshot":
            try:
                self._send_snapshot(parts[3])
            except CCTVServiceError as exc:
                self._send_error_json(exc)
            except OSError:
                self._send_json({"error": {"code": "SNAPSHOT_UNAVAILABLE", "message": "Snapshot tidak dapat dibaca"}}, 404)
            return
        if parsed.path.startswith("/api/"):
            try:
                self._send_json(self._api(parsed.path, parse_qs(parsed.query)))
            except CCTVServiceError as exc:
                self._send_error_json(exc)
            except Exception as exc:  # pragma: no cover - defensive HTTP boundary
                self._send_json({"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, 500)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        try:
            self._require_local_mutation()
            if parts == ["api", "v1", "agent", "settings"]:
                payload = self._read_json_body()
                settings, audit_id = self.service.configure_agent_settings(
                    run_all_tasks=payload.get("run_all_tasks"),
                    actor_id=os.getenv("MCP_ACTOR_ID", "mcp-local"),
                )
                self._send_json({"settings": settings, "audit_id": audit_id})
                return
            if len(parts) == 4 and parts[:3] == ["api", "v1", "runtime"]:
                payload = self._read_json_body()
                action = parts[3]
                if action == "start":
                    result = self.runtime.start_all(
                        batch_size=payload.get("batch_size", 4),
                        batch_delay=payload.get("batch_delay", 1.0),
                    )
                elif action == "stop":
                    result = self.runtime.stop_all()
                elif action == "restart":
                    result = self.runtime.restart_all(
                        batch_size=payload.get("batch_size", 4),
                        batch_delay=payload.get("batch_delay", 1.0),
                    )
                else:
                    raise CCTVServiceError("NOT_FOUND", "Aksi runtime tidak ditemukan")
                audit_id = self.service.audit(
                    f"runtime.{action}", os.getenv("MCP_ACTOR_ID", "mcp-local"),
                    {"workers_running": result["workers_running"]},
                )
                self._send_json({"runtime": result, "audit_id": audit_id})
                return
            if len(parts) == 5 and parts[:3] == ["api", "v1", "runtime"]:
                camera_id, action = parts[3], parts[4]
                self._read_json_body()
                if action == "start":
                    result = self.runtime.start_camera(camera_id)
                elif action == "stop":
                    result = self.runtime.stop_camera(camera_id)
                elif action == "restart":
                    result = self.runtime.restart_camera(camera_id)
                else:
                    raise CCTVServiceError("NOT_FOUND", "Aksi kamera runtime tidak ditemukan")
                audit_id = self.service.audit(
                    f"runtime.camera.{action}", os.getenv("MCP_ACTOR_ID", "mcp-local"),
                    {"camera_id": camera_id, "running": result["running"]},
                )
                self._send_json({"camera": result, "audit_id": audit_id})
                return
            if len(parts) == 5 and parts[:3] == ["api", "v1", "tasks"] and parts[4] == "settings":
                payload = self._read_json_body()
                task, audit_id = self.service.configure_task(
                    task_id=parts[3],
                    rule=payload.get("rule"),
                    enabled=payload.get("enabled"),
                    actor_id=os.getenv("MCP_ACTOR_ID", "mcp-local"),
                )
                self._send_json({"task": task, "audit_id": audit_id})
                return
            raise CCTVServiceError("NOT_FOUND", "API endpoint tidak ditemukan")
        except CCTVServiceError as exc:
            self._send_error_json(exc)
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send_json({"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, 500)


def create_server(root: Path, host: str, port: int) -> ThreadingHTTPServer:
    service = CCTVService.from_env(root)
    runtime = RuntimeManager(root)

    class BoundDashboardRequestHandler(DashboardRequestHandler):
        pass

    BoundDashboardRequestHandler.service = service
    BoundDashboardRequestHandler.runtime = runtime
    handler = partial(BoundDashboardRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    server.runtime_manager = runtime  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Vision Agent dashboard and CCTV API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    server = create_server(args.root.resolve(), args.host, args.port)
    print(f"Dashboard API ready at http://{args.host}:{args.port}/api/v1/health", flush=True)
    print(f"Dashboard UI ready at http://{args.host}:{args.port}/desain-awal-dashboard/login.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.runtime_manager.stop_all()  # type: ignore[attr-defined]
        server.server_close()


if __name__ == "__main__":
    main()
