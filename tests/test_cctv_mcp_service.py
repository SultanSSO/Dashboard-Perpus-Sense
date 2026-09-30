import json
from pathlib import Path

import pytest

from cctv_mcp_service import CCTVPaths, CCTVService, CCTVServiceError


def build_service(tmp_path: Path) -> CCTVService:
    catalog = tmp_path / "catalog.json"
    vision = tmp_path / "vision.json"
    events = tmp_path / "events.jsonl"
    catalog.write_text(
        json.dumps(
            {
                "cameras": [
                    {
                        "camera_id": "CAM-01",
                        "catalog_id": "cam-01",
                        "device_id": "DVR-01",
                        "ip": "192.0.2.1",
                        "channel": 1,
                        "source_type": "snapshot",
                        "snapshot_url_template": "http://USER:PASS@192.0.2.1/snapshot",
                        "rtsp_url_template": "rtsp://USER:PASS@192.0.2.1/stream",
                        "operational_status": "active",
                        "visual_status": "Jelas",
                        "location": "Lobby",
                        "description": "Main entrance",
                    },
                    {
                        "camera_id": "CAM-02",
                        "catalog_id": "cam-02",
                        "device_id": "DVR-01",
                        "ip": "192.0.2.2",
                        "channel": 2,
                        "source_type": "snapshot",
                        "operational_status": "inactive",
                        "visual_status": "Mati",
                        "location": "Archive",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    vision.write_text(
        json.dumps(
            {
                "analysis_cameras": [
                    {"camera_id": "CAM-01", "enabled": True, "profile": "balanced", "purpose": "occupancy"}
                ]
            }
        ),
        encoding="utf-8",
    )
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "evt-1",
                        "event_type": "occupancy_update",
                        "observed_at": "2026-01-01T10:00:00+00:00",
                        "source": {"camera_id": "CAM-01", "stream": "rtsp://USER:SECRET@192.0.2.1/stream"},
                        "measurement": {"person_count": 4},
                        "quality": {"stream_ok": True},
                    }
                ),
                json.dumps(
                    {
                        "event_id": "evt-unscoped",
                        "event_type": "occupancy_update",
                        "observed_at": "2026-01-01T10:01:00+00:00",
                        "source": {"stream": "rtsp://USER:SECRET@192.0.2.9/stream"},
                        "measurement": {"person_count": 99},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    return CCTVService(CCTVPaths(catalog, vision, events, tmp_path / "tasks.json", tmp_path / "audit.jsonl"))


def test_metadata_is_allowlisted_and_analysis_filter_is_configured(tmp_path):
    service = build_service(tmp_path)

    metadata = service.get_metadata("CAM-01")
    assert metadata["analysis_enabled"] is True
    assert metadata["vision_profile"] == "balanced"
    assert "rtsp_url_template" not in metadata
    assert "snapshot_url_template" not in metadata
    assert "SECRET" not in json.dumps(metadata)
    assert service.list_cameras(analysis_only=True)["total"] == 1


def test_observation_does_not_attach_unscoped_event(tmp_path):
    service = build_service(tmp_path)

    observation = service.current_observation("CAM-01")
    assert observation["measurement"]["person_count"] == 4
    assert observation["fresh"] is False
    assert observation["age_seconds"] > 30
    assert service.current_observation("CAM-02")["available"] is False


def test_camera_status_does_not_call_stale_observation_online(tmp_path):
    service = build_service(tmp_path)

    status = service.get_status("CAM-01")

    assert status["stream_status"] == "stale"
    assert status["live_worker_connected"] is False
    assert status["age_seconds"] > 30


def test_events_are_bounded_and_redacted(tmp_path):
    service = build_service(tmp_path)

    result = service.events(camera_id="CAM-01", limit=1)
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert "SECRET" not in json.dumps(result)
    assert "***" in result["items"][0]["source"]["stream"]


def test_task_lifecycle_is_persisted_and_audited(tmp_path):
    service = build_service(tmp_path)

    task, audit_id = service.create_task(
        name="Monitor lobby",
        goal="Alert when occupancy exceeds threshold",
        camera_ids=["CAM-01"],
        task_type="MONITOR",
        actor_id="operator-1",
        rule={"type": "PEOPLE_THRESHOLD_EXCEEDED", "threshold": 10},
    )
    assert task["status"] == "CREATED"
    assert audit_id.startswith("AUD-")
    assert service.get_task(task["task_id"])["task_id"] == task["task_id"]

    updated, transition_audit = service.transition_task(
        task_id=task["task_id"], target_status="RUNNING", actor_id="operator-1"
    )
    assert updated["status"] == "RUNNING"
    assert transition_audit.startswith("AUD-")

    with pytest.raises(CCTVServiceError, match="State mutasi tidak didukung"):
        service.transition_task(task_id=task["task_id"], target_status="COMPLETED", actor_id="operator-1")


def test_configure_task_updates_rule_and_running_state_atomically(tmp_path):
    service = build_service(tmp_path)
    task, _ = service.create_task(
        name="Monitor lobby",
        goal="Alert when occupancy exceeds threshold",
        camera_ids=["CAM-01"],
        task_type="STANDING_MONITOR",
        actor_id="operator-1",
        rule={"type": "PEOPLE_THRESHOLD_EXCEEDED", "threshold": 10},
    )

    updated, audit_id = service.configure_task(
        task_id=task["task_id"],
        enabled=True,
        actor_id="operator-1",
        rule={
            "type": "PEOPLE_THRESHOLD_EXCEEDED",
            "threshold": 7,
            "persistence_seconds": 15,
            "resolution_seconds": 20,
            "cooldown_seconds": 300,
            "severity": "critical",
        },
    )

    assert updated["status"] == "RUNNING"
    assert updated["rule"]["threshold"] == 7
    assert updated["rule"]["severity"] == "critical"
    assert audit_id.startswith("AUD-")

    with pytest.raises(CCTVServiceError, match="threshold harus angka non-negatif"):
        service.configure_task(
            task_id=task["task_id"],
            enabled=True,
            actor_id="operator-1",
            rule={"type": "PEOPLE_THRESHOLD_EXCEEDED", "threshold": -1},
        )


def test_default_all_tasks_runs_supported_tasks_and_blocks_pause(tmp_path):
    service = build_service(tmp_path)
    first, _ = service.create_task(
        name="Monitor lobby",
        goal="Monitor people",
        camera_ids=["CAM-01"],
        task_type="STANDING_MONITOR",
        actor_id="operator-1",
        rule={"type": "PEOPLE_THRESHOLD_EXCEEDED", "threshold": 5},
    )
    assert first["status"] == "CREATED"

    settings, audit_id = service.configure_agent_settings(
        run_all_tasks=True,
        actor_id="operator-1",
    )
    assert settings["run_all_tasks"] is True
    assert settings["activated_task_ids"] == [first["task_id"]]
    assert audit_id.startswith("AUD-")
    assert service.get_task(first["task_id"])["status"] == "RUNNING"

    with pytest.raises(CCTVServiceError, match="Mode default semua task aktif"):
        service.transition_task(task_id=first["task_id"], target_status="PAUSED", actor_id="operator-1")

    second, _ = service.create_task(
        name="Monitor archive",
        goal="Monitor people",
        camera_ids=["CAM-01"],
        task_type="MONITOR",
        actor_id="operator-1",
        rule={"type": "PEOPLE_THRESHOLD_EXCEEDED", "threshold": 3},
    )
    assert second["status"] == "RUNNING"

    service.configure_agent_settings(run_all_tasks=False, actor_id="operator-1")
    paused, _ = service.configure_task(
        task_id=first["task_id"],
        enabled=False,
        actor_id="operator-1",
        rule=first["rule"],
    )
    assert paused["status"] == "PAUSED"


def test_supported_vision_agent_rules_are_validated_and_persisted(tmp_path):
    service = build_service(tmp_path)
    rules = [
        {
            "type": "PEOPLE_COUNT_ANALYTICS",
            "reporting": {"dashboard_enabled": True, "hermes_schedule": "06:15"},
        },
        {
            "type": "CROWD_LEVEL_MONITOR",
            "medium_threshold": 5,
            "high_threshold": 10,
            "critical_threshold": 15,
            "persistence_seconds": 15,
            "resolution_seconds": 15,
            "cooldown_seconds": 300,
            "camera_overrides": {"CAM-01": {"high_threshold": 12}},
        },
        {
            "type": "CAMERA_HEALTH_MONITOR",
            "degraded_after_seconds": 30,
            "offline_after_seconds": 60,
            "recovery_observations": 3,
            "camera_overrides": {"CAM-01": {"offline_after_seconds": 90}},
        },
        {
            "type": "AFTER_HOURS_PRESENCE",
            "start_time": "22:00",
            "end_time": "06:00",
            "timezone": "Asia/Jakarta",
            "person_threshold": 1,
            "persistence_seconds": 15,
            "resolution_seconds": 15,
            "cooldown_seconds": 300,
            "camera_overrides": {"CAM-01": {"mode": "monitor_only"}},
        },
    ]

    for index, rule in enumerate(rules):
        task, _ = service.create_task(
            name=f"Task {index}",
            goal="Vision Agent rule",
            camera_ids=["CAM-01"],
            task_type="STANDING_MONITOR",
            actor_id="operator-1",
            rule=rule,
        )
        assert task["rule"]["type"] == rule["type"]


def test_crowd_thresholds_must_be_strictly_increasing(tmp_path):
    service = build_service(tmp_path)

    with pytest.raises(CCTVServiceError, match="medium_threshold < high_threshold < critical_threshold"):
        service.create_task(
            name="Crowd",
            goal="Classify crowd level",
            camera_ids=["CAM-01"],
            task_type="STANDING_MONITOR",
            actor_id="operator-1",
            rule={
                "type": "CROWD_LEVEL_MONITOR",
                "medium_threshold": 10,
                "high_threshold": 10,
                "critical_threshold": 20,
            },
        )


def test_camera_override_rejects_unknown_camera(tmp_path):
    service = build_service(tmp_path)

    with pytest.raises(CCTVServiceError, match="Kamera tidak ditemukan"):
        service.create_task(
            name="After hours",
            goal="Monitor after-hours presence",
            camera_ids=["CAM-01"],
            task_type="STANDING_MONITOR",
            actor_id="operator-1",
            rule={
                "type": "AFTER_HOURS_PRESENCE",
                "start_time": "22:00",
                "end_time": "06:00",
                "timezone": "Asia/Jakarta",
                "camera_overrides": {"CAM-99": {"mode": "disabled"}},
            },
        )
