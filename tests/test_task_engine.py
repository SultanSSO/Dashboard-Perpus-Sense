import json
from pathlib import Path

from cctv_mcp_service import CCTVPaths, CCTVService
from vision_agent.task_engine import TaskRuleEngine


def build_service(tmp_path: Path) -> CCTVService:
    catalog = tmp_path / "catalog.json"
    vision = tmp_path / "vision.json"
    events = tmp_path / "events.jsonl"
    catalog.write_text(
        json.dumps({"cameras": [{"camera_id": "CAM-01", "operational_status": "active"}]}),
        encoding="utf-8",
    )
    vision.write_text(
        json.dumps({"analysis_cameras": [{"camera_id": "CAM-01", "enabled": True}]}),
        encoding="utf-8",
    )
    events.write_text("", encoding="utf-8")
    return CCTVService(
        CCTVPaths(catalog, vision, events, tmp_path / "tasks.json", tmp_path / "audit.jsonl")
    )


def append_observation(service: CCTVService, event_id: str, observed_at: str, people: int) -> None:
    event = {
        "schema_version": "vision.event.v1",
        "event_id": event_id,
        "event_type": "occupancy_update",
        "observed_at": observed_at,
        "source": {"camera_id": "CAM-01"},
        "measurement": {"person_count": people},
        "quality": {"stream_ok": True},
    }
    with service.paths.events.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def alert_events(service: CCTVService) -> list[dict]:
    return [
        json.loads(line)
        for line in service.paths.events.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event_type") == "PEOPLE_THRESHOLD_EXCEEDED"
    ]


def test_threshold_opens_and_resolves_after_configured_persistence(tmp_path):
    service = build_service(tmp_path)
    task, _ = service.create_task(
        name="Monitor lobby",
        goal="Alert when occupancy exceeds threshold",
        camera_ids=["CAM-01"],
        task_type="STANDING_MONITOR",
        actor_id="operator-1",
        rule={
            "type": "PEOPLE_THRESHOLD_EXCEEDED",
            "threshold": 2,
            "persistence_seconds": 10,
            "resolution_seconds": 5,
            "cooldown_seconds": 300,
        },
    )
    service.transition_task(task_id=task["task_id"], target_status="RUNNING", actor_id="operator-1")
    engine = TaskRuleEngine(service)

    append_observation(service, "obs-1", "2026-09-23T10:00:00+00:00", 3)
    assert engine.process_once()["events_emitted"] == 0

    append_observation(service, "obs-2", "2026-09-23T10:00:11+00:00", 4)
    assert engine.process_once()["events_emitted"] == 1
    assert engine.process_once()["events_emitted"] == 0
    assert service.current_observation("CAM-01")["event_id"] == "obs-2"
    assert len(service.active_alerts()) == 1

    append_observation(service, "obs-3", "2026-09-23T10:00:12+00:00", 1)
    assert engine.process_once()["events_emitted"] == 0

    append_observation(service, "obs-4", "2026-09-23T10:00:18+00:00", 1)
    assert engine.process_once()["events_emitted"] == 1
    assert service.active_alerts() == []

    alerts = alert_events(service)
    assert [event["state"] for event in alerts] == ["OPEN", "RESOLVED"]
    assert alerts[0]["event_id"] == alerts[1]["event_id"]
    assert alerts[0]["measurement"] == {"person_count": 4, "threshold": 2}


def create_running_task(service: CCTVService, rule: dict, name: str = "Rule task") -> dict:
    task, _ = service.create_task(
        name=name,
        goal="Evaluate deterministic vision rule",
        camera_ids=["CAM-01"],
        task_type="STANDING_MONITOR",
        actor_id="operator-1",
        rule=rule,
    )
    service.transition_task(task_id=task["task_id"], target_status="RUNNING", actor_id="operator-1")
    return task


def test_crowd_level_emits_only_persistent_level_transitions(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "CROWD_LEVEL_MONITOR",
            "medium_threshold": 2,
            "high_threshold": 4,
            "critical_threshold": 6,
            "persistence_seconds": 10,
            "resolution_seconds": 5,
            "cooldown_seconds": 0,
        },
    )
    engine = TaskRuleEngine(service)

    append_observation(service, "crowd-1", "2026-09-25T10:00:00+00:00", 4)
    assert engine.process_once()["events_emitted"] == 0
    append_observation(service, "crowd-2", "2026-09-25T10:00:11+00:00", 5)
    assert engine.process_once()["events_emitted"] == 1

    events = [
        json.loads(line)
        for line in service.paths.events.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event_type") == "CROWD_LEVEL_CHANGED"
    ]
    assert events[-1]["state"] == "OPEN"
    assert events[-1]["data"]["level"] == "HIGH"


def test_after_hours_rule_uses_timezone_and_persistence(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "AFTER_HOURS_PRESENCE",
            "start_time": "22:00",
            "end_time": "06:00",
            "timezone": "Asia/Jakarta",
            "person_threshold": 1,
            "persistence_seconds": 10,
            "resolution_seconds": 5,
            "cooldown_seconds": 0,
        },
    )
    engine = TaskRuleEngine(service)

    append_observation(service, "night-1", "2026-09-25T15:30:00+00:00", 1)
    assert engine.process_once()["events_emitted"] == 0
    append_observation(service, "night-2", "2026-09-25T15:30:11+00:00", 2)
    assert engine.process_once()["events_emitted"] == 1

    events = [
        json.loads(line)
        for line in service.paths.events.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event_type") == "AFTER_HOURS_PRESENCE"
    ]
    assert events[-1]["state"] == "OPEN"
    assert events[-1]["data"]["timezone"] == "Asia/Jakarta"


def test_after_hours_monitor_only_records_state_without_alert(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "AFTER_HOURS_PRESENCE",
            "start_time": "22:00",
            "end_time": "06:00",
            "timezone": "Asia/Jakarta",
            "person_threshold": 1,
            "persistence_seconds": 0,
            "camera_overrides": {"CAM-01": {"mode": "monitor_only"}},
        },
    )

    append_observation(service, "monitor-only", "2026-09-25T16:00:00+00:00", 2)
    assert TaskRuleEngine(service).process_once()["events_emitted"] == 0


def test_camera_health_waits_for_offline_grace_when_no_observation_exists(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "CAMERA_HEALTH_MONITOR",
            "degraded_after_seconds": 30,
            "offline_after_seconds": 60,
            "recovery_observations": 2,
            "cooldown_seconds": 0,
        },
    )
    engine = TaskRuleEngine(service)
    service.paths.events.write_text("", encoding="utf-8")

    assert engine.process_once(now="2026-09-25T10:00:00+00:00")["events_emitted"] == 0
    assert engine.process_once(now="2026-09-25T10:00:31+00:00")["events_emitted"] == 1
    assert engine.process_once(now="2026-09-25T10:00:59+00:00")["events_emitted"] == 0
    assert engine.process_once(now="2026-09-25T10:01:01+00:00")["events_emitted"] == 1


def test_camera_health_reports_offline_and_recovered(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "CAMERA_HEALTH_MONITOR",
            "degraded_after_seconds": 30,
            "offline_after_seconds": 60,
            "recovery_observations": 2,
            "cooldown_seconds": 0,
        },
    )
    engine = TaskRuleEngine(service)

    append_observation(service, "health-1", "2026-09-25T10:00:00+00:00", 0)
    result = engine.process_once(now="2026-09-25T10:01:01+00:00")
    assert result["events_emitted"] == 1

    append_observation(service, "health-2", "2026-09-25T10:01:02+00:00", 0)
    assert engine.process_once(now="2026-09-25T10:01:02+00:00")["events_emitted"] == 0
    append_observation(service, "health-3", "2026-09-25T10:01:03+00:00", 0)
    assert engine.process_once(now="2026-09-25T10:01:03+00:00")["events_emitted"] == 1

    events = [
        json.loads(line)
        for line in service.paths.events.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event_type") in {"CAMERA_OFFLINE", "CAMERA_RECOVERED"}
    ]
    assert [event["event_type"] for event in events] == ["CAMERA_OFFLINE", "CAMERA_RECOVERED"]


def test_active_health_alert_reports_runtime_event_type(tmp_path):
    service = build_service(tmp_path)
    create_running_task(
        service,
        {
            "type": "CAMERA_HEALTH_MONITOR",
            "degraded_after_seconds": 30,
            "offline_after_seconds": 60,
            "recovery_observations": 2,
            "cooldown_seconds": 0,
        },
    )
    engine = TaskRuleEngine(service)
    append_observation(service, "health-active", "2026-09-25T10:00:00+00:00", 0)

    assert engine.process_once(now="2026-09-25T10:00:31+00:00")["events_emitted"] == 1
    alert = service.active_alerts()[0]
    assert alert["event_type"] == "VISION_DEGRADED"
    assert alert["observed_at"] == "2026-09-25T10:00:00+00:00"
