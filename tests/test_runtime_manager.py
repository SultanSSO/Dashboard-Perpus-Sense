import json
from pathlib import Path

import pytest

from vision_agent.runtime_manager import RuntimeManager
from vision_agent.mcp.service import CCTVServiceError


class FakeProcess:
    next_pid = 1000

    def __init__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs
        self.pid = FakeProcess.next_pid
        FakeProcess.next_pid += 1
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


def build_manager(tmp_path: Path) -> RuntimeManager:
    catalog = tmp_path / "camera_catalog.json"
    vision = tmp_path / "vision_agent.json"
    catalog.write_text(
        json.dumps(
            {
                "cameras": [
                    {
                        "camera_id": "1.145-CH13",
                        "catalog_id": "dvr-02_ch13",
                        "snapshot_url_template": "http://192.0.2.1/snapshot",
                        "operational_status": "active",
                    },
                    {
                        "camera_id": "1.145-CH01",
                        "catalog_id": "dvr-02_ch01",
                        "snapshot_url_template": "http://192.0.2.1/snapshot2",
                        "operational_status": "active",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    vision.write_text(
        json.dumps(
            {
                "model": "yolo11n.pt",
                "device": "auto",
                "analysis_cameras": [
                    {"camera_id": "1.145-CH13", "enabled": True},
                    {"camera_id": "1.145-CH01", "enabled": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "yolo11n.pt").write_bytes(b"model")
    return RuntimeManager(
        tmp_path,
        catalog_path=catalog,
        vision_path=vision,
        process_factory=FakeProcess,
        environment={
            "SNAPSHOT_URL": "https://host/snap_cache/dvr02_ch13.jpg",
            "CCTV_USERNAME": "user",
            "CCTV_PASSWORD": "secret",
        },
    )


def test_start_camera_uses_allowlisted_source_and_prevents_duplicates(tmp_path):
    manager = build_manager(tmp_path)

    result = manager.start_camera("1.145-CH13")
    duplicate = manager.start_camera("1.145-CH13")

    assert result["running"] is True
    assert result["pid"] == duplicate["pid"]
    assert "secret" not in json.dumps(result)
    assert "https://host/snap_cache/dvr02_ch13.jpg" in manager._workers["1.145-CH13"].command


def test_start_camera_rejects_unconfigured_camera(tmp_path):
    manager = build_manager(tmp_path)

    with pytest.raises(CCTVServiceError, match="Kamera tidak dikonfigurasi"):
        manager.start_camera("UNKNOWN")


def test_stop_camera_and_status_report_real_process_state(tmp_path):
    manager = build_manager(tmp_path)
    manager.start_camera("1.145-CH13")

    stopped = manager.stop_camera("1.145-CH13")
    status = manager.status()

    assert stopped["running"] is False
    assert status["workers_running"] == 0
    assert status["system_status"] == "STOPPED"


def test_start_all_starts_enabled_cameras_and_task_engine(tmp_path):
    manager = build_manager(tmp_path)

    result = manager.start_all(batch_size=1, batch_delay=0)

    assert result["workers_running"] == 2
    assert result["task_engine"]["running"] is True
    assert result["system_status"] == "RUNNING"


def test_stop_all_stops_task_engine_before_workers(tmp_path):
    manager = build_manager(tmp_path)
    manager.start_all(batch_size=2, batch_delay=0)

    result = manager.stop_all()

    assert result["workers_running"] == 0
    assert result["task_engine"]["running"] is False
    assert result["system_status"] == "STOPPED"
