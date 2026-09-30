"""Domain service for the CCTV MCP server.

This module is transport-independent so its security and data behavior can be
tested without starting an MCP process.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CCTVServiceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CCTVPaths:
    catalog: Path
    vision: Path
    events: Path
    tasks: Path
    audit: Path


_SECRET_URL = re.compile(r"(://[^:/]+:)[^@]+(@)")
_TASK_TYPES = {"MONITOR", "STANDING_MONITOR", "REPORT"}
_MUTABLE_STATES = {"PAUSED", "RUNNING", "CANCELLED"}
_TASK_STATES = {"CREATED", "SCHEDULED", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED"}
_RULE_TYPES = {
    "PEOPLE_THRESHOLD_EXCEEDED",
    "PEOPLE_COUNT_ANALYTICS",
    "CROWD_LEVEL_MONITOR",
    "CAMERA_HEALTH_MONITOR",
    "AFTER_HOURS_PRESENCE",
}
_RULE_SEVERITIES = {"info", "warning", "critical"}
_RULE_MODES = {"alert", "monitor_only", "disabled"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CCTVServiceError("INVALID_TIME", f"Format waktu tidak valid: {value}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _limit(value: int, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise CCTVServiceError("INVALID_ARGUMENT", f"{name} harus integer 1..{maximum}")
    return value


def _number(value: Any, name: str, default: float = 0) -> float:
    value = default if value is None else value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise CCTVServiceError("INVALID_RULE", f"{name} harus angka non-negatif")
    return value


def _clock(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise CCTVServiceError("INVALID_RULE", f"{name} harus berformat HH:MM")
    return value


def _validate_rule(rule: dict[str, Any] | None) -> dict[str, Any]:
    if rule is None:
        return {}
    if not isinstance(rule, dict):
        raise CCTVServiceError("INVALID_RULE", "rule harus berupa object")
    normalized = deepcopy(rule)
    rule_type = normalized.get("type")
    if rule_type not in _RULE_TYPES:
        raise CCTVServiceError("INVALID_RULE", "type rule tidak didukung")

    for name, default in (
        ("persistence_seconds", 0),
        ("resolution_seconds", 0),
        ("cooldown_seconds", 0),
    ):
        normalized[name] = _number(normalized.get(name), name, default)

    severity = normalized.get("severity", "warning")
    if severity not in _RULE_SEVERITIES:
        raise CCTVServiceError("INVALID_RULE", "severity harus info, warning, atau critical")
    normalized["severity"] = severity

    mode = normalized.get("mode", "alert")
    if mode not in _RULE_MODES:
        raise CCTVServiceError("INVALID_RULE", "mode harus alert, monitor_only, atau disabled")
    normalized["mode"] = mode

    if rule_type == "PEOPLE_THRESHOLD_EXCEEDED":
        normalized["threshold"] = _number(normalized.get("threshold"), "threshold")
    elif rule_type == "CROWD_LEVEL_MONITOR":
        medium = _number(normalized.get("medium_threshold"), "medium_threshold", 5)
        high = _number(normalized.get("high_threshold"), "high_threshold", 10)
        critical = _number(normalized.get("critical_threshold"), "critical_threshold", 15)
        if not medium < high < critical:
            raise CCTVServiceError(
                "INVALID_RULE", "threshold wajib medium_threshold < high_threshold < critical_threshold"
            )
        normalized.update(
            medium_threshold=medium,
            high_threshold=high,
            critical_threshold=critical,
        )
    elif rule_type == "CAMERA_HEALTH_MONITOR":
        degraded = _number(normalized.get("degraded_after_seconds"), "degraded_after_seconds", 30)
        offline = _number(normalized.get("offline_after_seconds"), "offline_after_seconds", 60)
        recovery = normalized.get("recovery_observations", 3)
        if degraded >= offline:
            raise CCTVServiceError("INVALID_RULE", "degraded_after_seconds harus lebih kecil dari offline_after_seconds")
        if isinstance(recovery, bool) or not isinstance(recovery, int) or recovery < 1:
            raise CCTVServiceError("INVALID_RULE", "recovery_observations harus integer positif")
        normalized.update(
            degraded_after_seconds=degraded,
            offline_after_seconds=offline,
            recovery_observations=recovery,
        )
    elif rule_type == "AFTER_HOURS_PRESENCE":
        normalized["start_time"] = _clock(normalized.get("start_time", "22:00"), "start_time")
        normalized["end_time"] = _clock(normalized.get("end_time", "06:00"), "end_time")
        timezone_name = normalized.get("timezone", "Asia/Jakarta")
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, TypeError) as exc:
            raise CCTVServiceError("INVALID_RULE", "timezone tidak valid") from exc
        normalized["timezone"] = timezone_name
        normalized["person_threshold"] = _number(
            normalized.get("person_threshold"), "person_threshold", 1
        )

    reporting = normalized.get("reporting", {})
    if not isinstance(reporting, dict):
        raise CCTVServiceError("INVALID_RULE", "reporting harus berupa object")
    normalized["reporting"] = reporting
    overrides = normalized.get("camera_overrides", {})
    if not isinstance(overrides, dict) or any(not isinstance(item, dict) for item in overrides.values()):
        raise CCTVServiceError("INVALID_RULE", "camera_overrides harus berupa object per kamera")
    for override in overrides.values():
        override_mode = override.get("mode", "alert")
        if override_mode not in _RULE_MODES:
            raise CCTVServiceError("INVALID_RULE", "mode override tidak valid")
    normalized["camera_overrides"] = overrides
    return normalized


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class CCTVService:
    def __init__(self, paths: CCTVPaths):
        self.paths = paths
        self._lock = threading.RLock()
        self._events_cache_key: tuple[int, int] | None = None
        self._events_cache: list[dict[str, Any]] = []
        self._catalog = self._read_catalog()
        self._vision = self._read_vision()
        self._analysis = {
            item["camera_id"]: item
            for item in self._vision.get("analysis_cameras", [])
            if isinstance(item, dict) and item.get("camera_id")
        }
        self._cameras = {item["camera_id"]: item for item in self._catalog}

    @classmethod
    def from_env(cls, project_dir: Path | None = None) -> "CCTVService":
        root = project_dir or Path(__file__).resolve().parents[2]

        def path(name: str, default: str) -> Path:
            configured = Path(os.getenv(name, default))
            return configured if configured.is_absolute() else root / configured

        return cls(CCTVPaths(
            catalog=path("MCP_CCTV_CATALOG_PATH", "config/camera_catalog.json"),
            vision=path("MCP_CCTV_VISION_PATH", "config/vision_agent.json"),
            events=path("MCP_CCTV_EVENTS_PATH", "outputs/events.jsonl"),
            tasks=path("MCP_CCTV_TASKS_PATH", "outputs/mcp/tasks.json"),
            audit=path("MCP_CCTV_AUDIT_PATH", "outputs/mcp/audit.jsonl"),
        ))

    def _read_catalog(self) -> list[dict[str, Any]]:
        if not self.paths.catalog.exists():
            raise CCTVServiceError("CATALOG_UNAVAILABLE", f"Catalog tidak ditemukan: {self.paths.catalog}")
        try:
            raw = json.loads(self.paths.catalog.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("CATALOG_INVALID", "Catalog kamera tidak dapat dibaca") from exc
        cameras = raw.get("cameras") if isinstance(raw, dict) else None
        if not isinstance(cameras, list):
            raise CCTVServiceError("CATALOG_INVALID", "Catalog harus memiliki array cameras")
        result = [deepcopy(item) for item in cameras if isinstance(item, dict) and item.get("camera_id")]
        if not result:
            raise CCTVServiceError("CATALOG_INVALID", "Catalog tidak berisi kamera valid")
        return result

    def _read_vision(self) -> dict[str, Any]:
        if not self.paths.vision.exists():
            return {"analysis_cameras": []}
        try:
            raw = json.loads(self.paths.vision.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("VISION_CONFIG_INVALID", "Konfigurasi vision tidak dapat dibaca") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("analysis_cameras", []), list):
            raise CCTVServiceError("VISION_CONFIG_INVALID", "Konfigurasi vision tidak valid")
        return raw

    def _camera(self, camera_id: str) -> dict[str, Any]:
        if not isinstance(camera_id, str) or not camera_id.strip():
            raise CCTVServiceError("INVALID_ARGUMENT", "camera_id wajib diisi")
        try:
            return self._cameras[camera_id.strip()]
        except KeyError as exc:
            raise CCTVServiceError("CAMERA_NOT_FOUND", f"Kamera tidak ditemukan: {camera_id}") from exc

    def _metadata(self, camera: dict[str, Any]) -> dict[str, Any]:
        profile = self._analysis.get(camera.get("camera_id"), {})
        return {
            "camera_id": camera.get("camera_id"), "catalog_id": camera.get("catalog_id"),
            "device_id": camera.get("device_id"), "ip": camera.get("ip"),
            "channel": camera.get("channel"), "source_type": camera.get("source_type"),
            "operational_status": camera.get("operational_status"), "visual_status": camera.get("visual_status"),
            "location": camera.get("location"), "description": camera.get("description"),
            "verified_from_frame": bool(camera.get("verified_from_frame", False)),
            "analysis_enabled": bool(profile.get("enabled", False)),
            "vision_profile": profile.get("profile"), "analysis_purpose": profile.get("purpose"),
        }

    def list_cameras(self, *, status: str | None = None, location: str | None = None,
                     analysis_only: bool = False, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        limit = _limit(limit, "limit", 200)
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 10000:
            raise CCTVServiceError("INVALID_ARGUMENT", "offset harus integer 0..10000")
        if status and status not in {"active", "inactive", "unknown"}:
            raise CCTVServiceError("INVALID_ARGUMENT", "status harus active, inactive, atau unknown")
        items = self._catalog
        if status:
            items = [item for item in items if item.get("operational_status", "unknown") == status]
        if location:
            query = location.casefold()
            items = [item for item in items if query in str(item.get("location") or "").casefold()]
        if analysis_only:
            items = [item for item in items if self._analysis.get(item.get("camera_id"), {}).get("enabled") is True]
        page = items[offset:offset + limit]
        return {"items": [self._metadata(item) for item in page], "total": len(items),
                "offset": offset, "limit": limit, "has_more": offset + len(page) < len(items)}

    def get_metadata(self, camera_id: str) -> dict[str, Any]:
        return self._metadata(self._camera(camera_id))

    def _events(self, max_lines: int = 5000) -> list[dict[str, Any]]:
        if not self.paths.events.exists():
            return []
        try:
            stat = self.paths.events.stat()
            cache_key = (stat.st_mtime_ns, stat.st_size)
        except OSError as exc:
            raise CCTVServiceError("EVENT_STORE_UNAVAILABLE", "Event store tidak dapat dibaca") from exc
        with self._lock:
            if cache_key == self._events_cache_key:
                return list(self._events_cache)
            try:
                lines = self.paths.events.read_text(encoding="utf-8").splitlines()[-max_lines:]
            except OSError as exc:
                raise CCTVServiceError("EVENT_STORE_UNAVAILABLE", "Event store tidak dapat dibaca") from exc
            result = []
            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    result.append(event)
            self._events_cache_key = cache_key
            self._events_cache = result
            return list(result)

    def _observations(self) -> list[dict[str, Any]]:
        return [event for event in self._events() if event.get("event_type") == "occupancy_update"]

    @staticmethod
    def _event_camera(event: dict[str, Any]) -> str | None:
        source = event.get("source")
        value = source.get("camera_id") if isinstance(source, dict) else None
        return value if isinstance(value, str) else None

    @staticmethod
    def _redact(event: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(event)
        if isinstance(result.get("source"), dict) and "stream" in result["source"]:
            stream = result["source"]["stream"]
            result["source"]["stream"] = _SECRET_URL.sub(r"\1***\2", stream) if isinstance(stream, str) else stream
        return result

    @staticmethod
    def _freshness(observed_at: str | None, maximum_age: float = 30) -> tuple[float | None, bool]:
        observed = parse_time(observed_at)
        if observed is None:
            return None, False
        age_seconds = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds())
        return age_seconds, age_seconds <= maximum_age

    def get_status(self, camera_id: str) -> dict[str, Any]:
        camera = self._camera(camera_id)
        events = [event for event in self._observations() if self._event_camera(event) == camera_id]
        latest = max(events, key=lambda event: event.get("observed_at", ""), default=None)
        observed_at = latest.get("observed_at") if latest else None
        age_seconds, fresh = self._freshness(observed_at)
        stream_ok = bool(latest and latest.get("quality", {}).get("stream_ok", True))
        stream_status = "online" if fresh and stream_ok else "stale" if latest else "unknown"
        return {"camera_id": camera_id, "catalog_status": camera.get("operational_status", "unknown"),
                "visual_status": camera.get("visual_status"), "stream_status": stream_status,
                "last_seen": observed_at, "age_seconds": age_seconds, "fresh": fresh,
                "last_event_id": latest.get("event_id") if latest else None,
                "health_source": "catalog_and_event_store", "live_worker_connected": fresh and stream_ok}

    def current_observation(self, camera_id: str) -> dict[str, Any]:
        self._camera(camera_id)
        events = [event for event in self._observations() if self._event_camera(event) == camera_id]
        latest = max(events, key=lambda event: event.get("observed_at", ""), default=None)
        if latest is None:
            return {"camera_id": camera_id, "available": False, "fresh": False,
                    "age_seconds": None, "reason": "no_camera_scoped_observation",
                    "observed_at": None, "measurement": None, "quality": None}
        age_seconds, fresh = self._freshness(latest.get("observed_at"))
        return {"camera_id": camera_id, "available": True, "fresh": fresh,
                "age_seconds": age_seconds, "observed_at": latest.get("observed_at"),
                "measurement": latest.get("measurement", {}), "confidence": latest.get("confidence"),
                "quality": latest.get("quality", {}), "privacy": latest.get("privacy", {}),
                "event_id": latest.get("event_id")}

    def active_alerts(self) -> list[dict[str, Any]]:
        state_path = self.paths.tasks.with_name("rule_state.json")
        if not state_path.exists():
            return []
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("RULE_STATE_INVALID", "State rule tidak dapat dibaca") from exc
        rules = payload.get("rules") if isinstance(payload, dict) else None
        if not isinstance(rules, dict):
            raise CCTVServiceError("RULE_STATE_INVALID", "State rule tidak valid")
        tasks = {task.get("task_id"): task for task in self._read_tasks()}
        alerts = []
        for state in rules.values():
            if not isinstance(state, dict) or state.get("status") not in {"OPEN", "RESOLVING"}:
                continue
            task = tasks.get(state.get("task_id"), {})
            if task.get("status") != "RUNNING":
                continue
            rule = task.get("rule", {}) if isinstance(task, dict) else {}
            alerts.append({
                "event_id": state.get("event_id"),
                "event_type": state.get("event_type", state.get("rule_type")),
                "state": "OPEN",
                "engine_state": state.get("status"),
                "severity": rule.get("severity", "warning"),
                "task_id": state.get("task_id"),
                "task_name": task.get("name"),
                "observed_at": state.get("last_observed_at"),
                "opened_at": state.get("opened_at"),
                "source": {"camera_id": state.get("camera_id")},
                "measurement": {
                    "person_count": state.get("last_count"),
                    "threshold": rule.get("threshold"),
                },
            })
        alerts.sort(key=lambda item: item.get("opened_at") or "", reverse=True)
        return alerts

    def events(self, *, camera_id: str | None = None, event_type: str | None = None,
               start: str | None = None, end: str | None = None, limit: int = 50) -> dict[str, Any]:
        limit = _limit(limit, "limit", 200)
        if camera_id:
            self._camera(camera_id)
        start_dt, end_dt = parse_time(start), parse_time(end)
        if start_dt and end_dt and start_dt > end_dt:
            raise CCTVServiceError("INVALID_ARGUMENT", "start tidak boleh melebihi end")
        matched = []
        for event in self._events():
            if camera_id and self._event_camera(event) != camera_id:
                continue
            if event_type and event.get("event_type") != event_type:
                continue
            observed = parse_time(event.get("observed_at")) if event.get("observed_at") else None
            if start_dt and (observed is None or observed < start_dt):
                continue
            if end_dt and (observed is None or observed > end_dt):
                continue
            matched.append(self._redact(event))
        matched.sort(key=lambda item: item.get("observed_at", ""), reverse=True)
        return {"items": matched[:limit], "total": len(matched), "limit": limit}

    def summary(self, *, camera_ids: list[str] | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        if camera_ids:
            if len(camera_ids) > 100:
                raise CCTVServiceError("INVALID_ARGUMENT", "camera_ids maksimal 100")
            for camera_id in camera_ids:
                self._camera(camera_id)
        start_dt, end_dt = parse_time(start), parse_time(end)
        values, times = [], []
        for event in self._events():
            if camera_ids and self._event_camera(event) not in camera_ids:
                continue
            observed = parse_time(event.get("observed_at")) if event.get("observed_at") else None
            if start_dt and (observed is None or observed < start_dt):
                continue
            if end_dt and (observed is None or observed > end_dt):
                continue
            measurement = event.get("measurement", {})
            value = measurement.get("person_count", measurement.get("count")) if isinstance(measurement, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
            if isinstance(event.get("observed_at"), str):
                times.append(event["observed_at"])
        return {"camera_ids": camera_ids, "sample_count": len(values),
                "people_count": {"min": min(values) if values else None, "max": max(values) if values else None,
                                  "average": round(sum(values) / len(values), 2) if values else None},
                "first_observed_at": min(times) if times else None, "last_observed_at": max(times) if times else None,
                "source": "vision.event.v1 JSONL", "ground_truth": False}

    def audit(self, action: str, actor_id: str, details: dict[str, Any]) -> str:
        audit_id = f"AUD-{uuid.uuid4().hex[:12]}"
        self.paths.audit.parent.mkdir(parents=True, exist_ok=True)
        record = {"audit_id": audit_id, "occurred_at": utc_now(), "action": action, "actor_id": actor_id, "details": details}
        with self.paths.audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return audit_id

    def _read_tasks(self) -> list[dict[str, Any]]:
        if not self.paths.tasks.exists():
            return []
        try:
            raw = json.loads(self.paths.tasks.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("TASK_STORE_INVALID", "Task store tidak dapat dibaca") from exc
        return raw.get("tasks", []) if isinstance(raw, dict) and isinstance(raw.get("tasks", []), list) else []

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
        _atomic_write(self.paths.tasks, {"schema_version": "vision.task.v1", "tasks": tasks})

    def agent_settings(self) -> dict[str, Any]:
        path = self.paths.tasks.with_name("agent_settings.json")
        if not path.exists():
            return {
                "schema_version": "vision.agent-settings.v1",
                "run_all_tasks": False,
                "mode": "individual",
                "updated_at": None,
                "updated_by": None,
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("AGENT_SETTINGS_INVALID", "Pengaturan default agent tidak dapat dibaca") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("run_all_tasks"), bool):
            raise CCTVServiceError("AGENT_SETTINGS_INVALID", "Pengaturan default agent tidak valid")
        return {
            "schema_version": "vision.agent-settings.v1",
            "run_all_tasks": payload["run_all_tasks"],
            "mode": "all_tasks" if payload["run_all_tasks"] else "individual",
            "updated_at": payload.get("updated_at"),
            "updated_by": payload.get("updated_by"),
        }

    def configure_agent_settings(self, *, run_all_tasks: bool,
                                 actor_id: str) -> tuple[dict[str, Any], str]:
        if not isinstance(run_all_tasks, bool):
            raise CCTVServiceError("INVALID_ARGUMENT", "run_all_tasks harus boolean")
        if not actor_id.strip():
            raise CCTVServiceError("INVALID_ARGUMENT", "actor_id wajib diisi")
        now = utc_now()
        activated_task_ids = []
        with self._lock:
            tasks = self._read_tasks()
            if run_all_tasks:
                for task in tasks:
                    rule = task.get("rule") if isinstance(task, dict) else None
                    if not isinstance(rule, dict) or rule.get("type") not in _RULE_TYPES:
                        continue
                    if task.get("status") not in {"CREATED", "SCHEDULED", "PAUSED", "RUNNING"}:
                        continue
                    if task.get("status") != "RUNNING":
                        task["status"] = "RUNNING"
                        task["updated_at"] = now
                        activated_task_ids.append(task["task_id"])
                self._write_tasks(tasks)
            settings = {
                "schema_version": "vision.agent-settings.v1",
                "run_all_tasks": run_all_tasks,
                "mode": "all_tasks" if run_all_tasks else "individual",
                "updated_at": now,
                "updated_by": actor_id,
            }
            _atomic_write(self.paths.tasks.with_name("agent_settings.json"), settings)
        audit_id = self.audit(
            "agent.settings.configure",
            actor_id,
            {"run_all_tasks": run_all_tasks, "activated_task_ids": activated_task_ids},
        )
        return {**settings, "activated_task_ids": activated_task_ids}, audit_id

    def list_tasks(self, *, status: str | None = None, limit: int = 50) -> dict[str, Any]:
        limit = _limit(limit, "limit", 200)
        if status and status not in _TASK_STATES:
            raise CCTVServiceError("INVALID_ARGUMENT", "status task tidak valid")
        tasks = self._read_tasks()
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        tasks.sort(key=lambda task: task.get("updated_at", ""), reverse=True)
        return {"items": tasks[:limit], "total": len(tasks), "limit": limit}

    def get_task(self, task_id: str) -> dict[str, Any]:
        for task in self._read_tasks():
            if task.get("task_id") == task_id:
                return task
        raise CCTVServiceError("TASK_NOT_FOUND", f"Task tidak ditemukan: {task_id}")

    def configure_task(self, *, task_id: str, rule: dict[str, Any], enabled: bool,
                       actor_id: str) -> tuple[dict[str, Any], str]:
        if not actor_id.strip():
            raise CCTVServiceError("INVALID_ARGUMENT", "actor_id wajib diisi")
        if not isinstance(enabled, bool):
            raise CCTVServiceError("INVALID_ARGUMENT", "enabled harus boolean")
        if not enabled and self.agent_settings()["run_all_tasks"]:
            raise CCTVServiceError("ACTION_DENIED", "Mode default semua task aktif; nonaktifkan mode default terlebih dahulu")
        validated_rule = _validate_rule(rule)
        with self._lock:
            tasks = self._read_tasks()
            task = next((item for item in tasks if item.get("task_id") == task_id), None)
            if task is None:
                raise CCTVServiceError("TASK_NOT_FOUND", f"Task tidak ditemukan: {task_id}")
            current = task.get("status")
            if current not in {"CREATED", "RUNNING", "PAUSED"}:
                raise CCTVServiceError("INVALID_TRANSITION", f"Task berstatus {current} tidak dapat dikonfigurasi")
            task["rule"] = validated_rule
            task["status"] = "RUNNING" if enabled else "PAUSED"
            task["updated_at"] = utc_now()
            self._write_tasks(tasks)
        audit_id = self.audit(
            "task.configure",
            actor_id,
            {"task_id": task_id, "from": current, "to": task["status"], "rule_type": validated_rule.get("type")},
        )
        return task, audit_id

    def create_task(self, *, name: str, goal: str, camera_ids: list[str], task_type: str,
                    actor_id: str, rule: dict[str, Any] | None = None) -> tuple[dict[str, Any], str]:
        if not name.strip() or not goal.strip() or not actor_id.strip():
            raise CCTVServiceError("INVALID_ARGUMENT", "name, goal, dan actor_id wajib diisi")
        if task_type not in _TASK_TYPES:
            raise CCTVServiceError("INVALID_ARGUMENT", "task_type tidak valid")
        if not camera_ids or len(camera_ids) > 100:
            raise CCTVServiceError("INVALID_ARGUMENT", "camera_ids harus berisi 1..100 kamera")
        for camera_id in camera_ids:
            self._camera(camera_id)
        validated_rule = _validate_rule(rule)
        for override_camera_id in validated_rule.get("camera_overrides", {}):
            self._camera(override_camera_id)
        now = utc_now()
        default_running = bool(validated_rule) and self.agent_settings()["run_all_tasks"]
        task = {"task_id": f"TASK-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
                "name": name.strip(), "goal": goal.strip(), "type": task_type,
                "status": "RUNNING" if default_running else "CREATED",
                "camera_ids": camera_ids, "rule": validated_rule, "created_at": now, "updated_at": now,
                "created_by": actor_id, "execution": {"scheduler": "task_rule_engine", "state_authority": "local_json_registry"}}
        with self._lock:
            tasks = self._read_tasks(); tasks.append(task); self._write_tasks(tasks)
        return task, self.audit("task.create", actor_id, {"task_id": task["task_id"], "camera_ids": camera_ids})

    def transition_task(self, *, task_id: str, target_status: str, actor_id: str) -> tuple[dict[str, Any], str]:
        if target_status not in _MUTABLE_STATES:
            raise CCTVServiceError("INVALID_ARGUMENT", f"State mutasi tidak didukung: {target_status}")
        if target_status == "PAUSED" and self.agent_settings()["run_all_tasks"]:
            raise CCTVServiceError("ACTION_DENIED", "Mode default semua task aktif; task tidak dapat dijeda")
        with self._lock:
            tasks = self._read_tasks(); task = next((item for item in tasks if item.get("task_id") == task_id), None)
            if task is None:
                raise CCTVServiceError("TASK_NOT_FOUND", f"Task tidak ditemukan: {task_id}")
            current = task.get("status")
            allowed = {"CREATED": {"PAUSED", "RUNNING", "CANCELLED"}, "SCHEDULED": {"PAUSED", "RUNNING", "CANCELLED"},
                       "RUNNING": {"PAUSED", "CANCELLED"}, "PAUSED": {"RUNNING", "CANCELLED"}}.get(current, set())
            if target_status not in allowed:
                raise CCTVServiceError("INVALID_TRANSITION", f"Tidak dapat mengubah {current} menjadi {target_status}")
            task["status"] = target_status; task["updated_at"] = utc_now(); self._write_tasks(tasks)
        return task, self.audit("task.transition", actor_id, {"task_id": task_id, "from": current, "to": target_status})

    def health(self) -> dict[str, Any]:
        events = self._observations()
        latest = max(events, key=lambda event: event.get("observed_at", ""), default=None)
        latest_at = latest.get("observed_at") if latest else None
        connected = False
        age_seconds = None
        if latest_at:
            observed = parse_time(latest_at)
            if observed:
                age_seconds = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds())
                connected = age_seconds <= 30
        return {"service": "cctv-mcp", "status": "ready",
                "catalog": {"path": str(self.paths.catalog), "available": self.paths.catalog.exists(), "camera_count": len(self._catalog)},
                "vision_config": {"path": str(self.paths.vision), "available": self.paths.vision.exists(), "analysis_camera_count": len(self._analysis),
                                  "model": self._vision.get("model"), "device": self._vision.get("device")},
                "event_store": {"path": str(self.paths.events), "available": self.paths.events.exists()},
                "task_store": {"path": str(self.paths.tasks), "available": self.paths.tasks.exists(), "mode": "local_json_registry"},
                "agent_settings": self.agent_settings(),
                "audit_store": {"path": str(self.paths.audit), "available": self.paths.audit.exists()},
                "live_worker": {"connected": connected, "last_event_at": latest_at, "age_seconds": age_seconds,
                                "reason": None if connected else "tidak ada event vision terbaru"}}


__all__ = ["CCTVPaths", "CCTVService", "CCTVServiceError"]
