"""Deterministic task and rule runtime for structured CCTV observations."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from vision_agent.mcp.service import CCTVService, CCTVServiceError, parse_time, utc_now

PEOPLE_THRESHOLD = "PEOPLE_THRESHOLD_EXCEEDED"
PEOPLE_ANALYTICS = "PEOPLE_COUNT_ANALYTICS"
CROWD_MONITOR = "CROWD_LEVEL_MONITOR"
HEALTH_MONITOR = "CAMERA_HEALTH_MONITOR"
AFTER_HOURS = "AFTER_HOURS_PRESENCE"
SUPPORTED_RULES = {PEOPLE_THRESHOLD, PEOPLE_ANALYTICS, CROWD_MONITOR, HEALTH_MONITOR, AFTER_HOURS}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
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


def _seconds(rule: dict[str, Any], name: str, default: float) -> float:
    value = rule.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise CCTVServiceError("INVALID_RULE", f"{name} harus angka non-negatif")
    return float(value)


def _effective_rule(rule: dict[str, Any], camera_id: str) -> dict[str, Any]:
    result = dict(rule)
    overrides = rule.get("camera_overrides", {})
    if isinstance(overrides, dict) and isinstance(overrides.get(camera_id), dict):
        result.update(overrides[camera_id])
    return result


def _count(observation: dict[str, Any]) -> float | None:
    value = (observation.get("measurement") or {}).get("person_count")
    return None if isinstance(value, bool) or not isinstance(value, (int, float)) else value


def _is_after_hours(observed: datetime, rule: dict[str, Any]) -> bool:
    local = observed.astimezone(ZoneInfo(rule.get("timezone", "Asia/Jakarta")))
    start_hour, start_minute = map(int, rule.get("start_time", "22:00").split(":"))
    end_hour, end_minute = map(int, rule.get("end_time", "06:00").split(":"))
    current = local.hour * 60 + local.minute
    start = start_hour * 60 + start_minute
    end = end_hour * 60 + end_minute
    return start <= current < end if start < end else current >= start or current < end


def _crowd_level(count: float, rule: dict[str, Any]) -> str:
    if count >= rule["critical_threshold"]:
        return "CRITICAL"
    if count >= rule["high_threshold"]:
        return "HIGH"
    if count >= rule["medium_threshold"]:
        return "MEDIUM"
    return "LOW"


class TaskRuleEngine:
    """Evaluate persisted RUNNING tasks against the latest observations."""

    def __init__(self, service: CCTVService, state_path: Path | None = None):
        self.service = service
        self.state_path = state_path or service.paths.tasks.with_name("rule_state.json")
        self._state = self._read_state()

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": "vision.rule-state.v2", "rules": {}}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CCTVServiceError("RULE_STATE_INVALID", "State rule tidak dapat dibaca") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("rules"), dict):
            raise CCTVServiceError("RULE_STATE_INVALID", "State rule tidak valid")
        return payload

    def _append_event(self, event: dict[str, Any]) -> None:
        self.service.paths.events.parent.mkdir(parents=True, exist_ok=True)
        with self.service.paths.events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    @staticmethod
    def _event(
        task: dict[str, Any], rule: dict[str, Any], camera_id: str,
        observation: dict[str, Any], state: dict[str, Any], event_type: str,
        lifecycle: str, data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observed_at = observation.get("observed_at") or utc_now()
        count = _count(observation)
        measurement = {"person_count": count}
        if event_type == PEOPLE_THRESHOLD:
            measurement["threshold"] = rule.get("threshold")
        return {
            "schema_version": "vision.alert.v1",
            "event_id": state["event_id"],
            "event_type": event_type,
            "state": lifecycle,
            "severity": rule.get("severity", "warning"),
            "task_id": task["task_id"],
            "rule_id": rule.get("rule_id", f"{task['task_id']}-RULE-1"),
            "observed_at": observed_at,
            "opened_at": state.get("opened_at"),
            "updated_at": observed_at,
            "resolved_at": observed_at if lifecycle in {"RESOLVED", "RECOVERED"} else None,
            "source": {"camera_id": camera_id},
            "measurement": measurement,
            "data": data or {},
        }

    def _state_for(self, task: dict[str, Any], camera_id: str, rule_type: str) -> dict[str, Any]:
        key = f"{task['task_id']}::{camera_id}::{rule_type}"
        return self._state["rules"].setdefault(
            key, {"status": "NORMAL", "task_id": task["task_id"], "camera_id": camera_id, "rule_type": rule_type}
        )

    def _evaluate_boolean(
        self, task: dict[str, Any], camera_id: str, observation: dict[str, Any],
        rule: dict[str, Any], condition: bool, event_type: str, data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        observed_at = observation.get("observed_at")
        observed = parse_time(observed_at)
        if observed is None:
            return []
        current = self._state_for(task, camera_id, rule["type"])
        if current.get("last_observation_event_id") == observation.get("event_id"):
            return []
        current.update(last_observation_event_id=observation.get("event_id"), last_observed_at=observed_at,
                       last_count=_count(observation))
        persistence = _seconds(rule, "persistence_seconds", 0)
        resolution = _seconds(rule, "resolution_seconds", 0)
        emitted: list[dict[str, Any]] = []
        status = current.get("status", "NORMAL")
        if condition:
            current.pop("resolution_since", None)
            if status == "RESOLVING":
                current["status"] = "OPEN"
                status = "OPEN"
            if status == "NORMAL":
                current.update(status="CANDIDATE", candidate_since=observed_at)
                status = "CANDIDATE"
            if status == "CANDIDATE":
                since = parse_time(current.get("candidate_since"))
                if since and (observed - since).total_seconds() >= persistence:
                    current.update(status="OPEN", event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}", opened_at=observed_at)
                    if rule.get("mode", "alert") == "alert":
                        emitted.append(self._event(task, rule, camera_id, observation, current, event_type, "OPEN", data))
        else:
            current.pop("candidate_since", None)
            if status == "CANDIDATE":
                current["status"] = "NORMAL"
            elif status == "OPEN":
                current.update(status="RESOLVING", resolution_since=observed_at)
            if current.get("status") == "RESOLVING":
                since = parse_time(current.get("resolution_since"))
                if since and (observed - since).total_seconds() >= resolution:
                    if rule.get("mode", "alert") == "alert":
                        emitted.append(self._event(task, rule, camera_id, observation, current, event_type, "RESOLVED", data))
                    current.update(status="NORMAL", resolved_at=observed_at)
                    for key in ("resolution_since", "event_id", "opened_at"):
                        current.pop(key, None)
        return emitted

    def _evaluate_threshold(self, task: dict[str, Any], camera_id: str,
                            observation: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
        count = _count(observation)
        if count is None:
            return []
        threshold = rule.get("threshold")
        return self._evaluate_boolean(
            task, camera_id, observation, rule, count > threshold, PEOPLE_THRESHOLD,
            {"condition": "person_count > threshold", "threshold": threshold},
        )

    def _evaluate_after_hours(self, task: dict[str, Any], camera_id: str,
                              observation: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
        count = _count(observation)
        observed = parse_time(observation.get("observed_at"))
        if count is None or observed is None:
            return []
        condition = _is_after_hours(observed, rule) and count >= rule.get("person_threshold", 1)
        return self._evaluate_boolean(
            task, camera_id, observation, rule, condition, AFTER_HOURS,
            {"timezone": rule.get("timezone", "Asia/Jakarta"), "start_time": rule.get("start_time", "22:00"),
             "end_time": rule.get("end_time", "06:00"), "person_threshold": rule.get("person_threshold", 1)},
        )

    def _evaluate_crowd(self, task: dict[str, Any], camera_id: str,
                        observation: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
        count = _count(observation)
        observed_at = observation.get("observed_at")
        observed = parse_time(observed_at)
        if count is None or observed is None:
            return []
        level = _crowd_level(count, rule)
        current = self._state_for(task, camera_id, rule["type"])
        if current.get("last_observation_event_id") == observation.get("event_id"):
            return []
        current.update(last_observation_event_id=observation.get("event_id"), last_observed_at=observed_at,
                       last_count=count)
        stable = current.get("stable_level", "LOW")
        if level == stable:
            current.pop("candidate_level", None)
            current.pop("candidate_since", None)
            return []
        if current.get("candidate_level") != level:
            current.update(candidate_level=level, candidate_since=observed_at)
        since = parse_time(current.get("candidate_since"))
        wait = _seconds(rule, "resolution_seconds" if level == "LOW" else "persistence_seconds", 0)
        if not since or (observed - since).total_seconds() < wait:
            return []
        previous = stable
        current.update(stable_level=level, status="NORMAL" if level == "LOW" else "OPEN",
                       event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}", opened_at=observed_at)
        current.pop("candidate_level", None)
        current.pop("candidate_since", None)
        if rule.get("mode", "alert") != "alert":
            return []
        lifecycle = "RESOLVED" if level == "LOW" else "OPEN"
        return [self._event(task, rule, camera_id, observation, current, "CROWD_LEVEL_CHANGED", lifecycle,
                            {"level": level, "previous_level": previous,
                             "thresholds": {"medium": rule["medium_threshold"], "high": rule["high_threshold"],
                                            "critical": rule["critical_threshold"]}})]

    def _evaluate_health(self, task: dict[str, Any], camera_id: str, observation: dict[str, Any],
                         rule: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        current = self._state_for(task, camera_id, rule["type"])
        observed = parse_time(observation.get("observed_at")) if observation.get("available") else None
        if observed is None:
            first_checked = parse_time(current.get("first_checked_at"))
            if first_checked is None:
                current["first_checked_at"] = now.isoformat()
                return []
            age = (now - first_checked).total_seconds()
        else:
            age = (now - observed).total_seconds()
        current["last_observed_at"] = observation.get("observed_at")
        current["last_count"] = _count(observation)
        quality = observation.get("quality") or {}
        valid = bool(observed and quality.get("stream_ok", True) and age < rule["degraded_after_seconds"])
        offline = age >= rule["offline_after_seconds"]
        degraded = not offline and not valid
        emitted: list[dict[str, Any]] = []
        status = current.get("health_status", "UNKNOWN")
        if offline and status != "OFFLINE":
            current.update(health_status="OFFLINE", status="OPEN", event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                           opened_at=now.isoformat(), recovery_count=0, last_observed_at=observation.get("observed_at"))
            if rule.get("mode", "alert") == "alert":
                current["event_type"] = "CAMERA_OFFLINE"
                emitted.append(self._event(task, rule, camera_id, observation, current, "CAMERA_OFFLINE", "OPEN",
                                           {"age_seconds": round(age, 3)}))
        elif degraded and status not in {"DEGRADED", "OFFLINE"}:
            current.update(health_status="DEGRADED", status="OPEN", event_id=f"EVT-{uuid.uuid4().hex[:12].upper()}",
                           opened_at=now.isoformat(), recovery_count=0)
            if rule.get("mode", "alert") == "alert":
                current["event_type"] = "VISION_DEGRADED"
                emitted.append(self._event(task, rule, camera_id, observation, current, "VISION_DEGRADED", "OPEN",
                                           {"age_seconds": round(age, 3)}))
        elif valid:
            event_id = observation.get("event_id")
            if current.get("last_recovery_event_id") != event_id:
                current["last_recovery_event_id"] = event_id
                current["recovery_count"] = current.get("recovery_count", 0) + 1
            if status in {"OFFLINE", "DEGRADED"} and current["recovery_count"] >= rule["recovery_observations"]:
                current["health_status"] = "ONLINE"
                current["status"] = "NORMAL"
                current["event_type"] = "CAMERA_RECOVERED"
                if rule.get("mode", "alert") == "alert":
                    emitted.append(self._event(task, rule, camera_id, observation, current, "CAMERA_RECOVERED", "RECOVERED",
                                               {"recovery_observations": current["recovery_count"]}))
                current["recovery_count"] = 0
            elif status == "UNKNOWN":
                current["health_status"] = "ONLINE"
                current["status"] = "NORMAL"
                current["recovery_count"] = 0
        return emitted

    def process_once(self, now: str | datetime | None = None) -> dict[str, int]:
        tasks = self.service.list_tasks(status="RUNNING", limit=200)["items"]
        current_time = parse_time(now) if isinstance(now, str) else now
        current_time = current_time or datetime.now(timezone.utc)
        observations_evaluated = 0
        events_emitted = 0
        for task in tasks:
            base_rule = task.get("rule") or {}
            rule_type = base_rule.get("type")
            if rule_type not in SUPPORTED_RULES:
                continue
            for camera_id in task.get("camera_ids", []):
                rule = _effective_rule(base_rule, camera_id)
                if rule.get("mode", "alert") == "disabled":
                    continue
                observation = self.service.current_observation(camera_id)
                if rule_type != HEALTH_MONITOR and not observation.get("available"):
                    continue
                observations_evaluated += 1
                if rule_type == PEOPLE_ANALYTICS:
                    continue
                if rule_type == PEOPLE_THRESHOLD:
                    events = self._evaluate_threshold(task, camera_id, observation, rule)
                elif rule_type == CROWD_MONITOR:
                    events = self._evaluate_crowd(task, camera_id, observation, rule)
                elif rule_type == AFTER_HOURS:
                    events = self._evaluate_after_hours(task, camera_id, observation, rule)
                else:
                    events = self._evaluate_health(task, camera_id, observation, rule, current_time)
                for event in events:
                    self._append_event(event)
                    events_emitted += 1
        _atomic_write(self.state_path, self._state)
        return {"tasks_evaluated": len(tasks), "observations_evaluated": observations_evaluated,
                "events_emitted": events_emitted}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run deterministic CCTV task rules")
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("TASK_ENGINE_POLL_SECONDS", "1")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds harus lebih besar dari 0")
    engine = TaskRuleEngine(CCTVService.from_env())
    if args.once:
        print(json.dumps(engine.process_once(), ensure_ascii=False), flush=True)
        return
    print(f"Task engine ready; poll_seconds={args.poll_seconds:g}", flush=True)
    try:
        while True:
            try:
                result = engine.process_once()
                if result["events_emitted"]:
                    print(json.dumps({"processed_at": utc_now(), **result}, ensure_ascii=False), flush=True)
            except (CCTVServiceError, OSError, ValueError) as exc:
                print(json.dumps({"processed_at": utc_now(), "error": str(exc)}, ensure_ascii=False), flush=True)
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
