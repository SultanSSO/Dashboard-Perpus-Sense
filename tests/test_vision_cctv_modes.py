from vision_cctv_modes import (
    MODE_CLASSES,
    TASK_MENU,
    available_models,
    classify_density,
    count_empty_chairs,
    normalize_mode,
    resolve_source,
    startup_info,
)


def test_normalize_mode_supports_letter_and_name():
    assert normalize_mode("a") == "person"
    assert normalize_mode("D") == "density"
    assert normalize_mode("both") == "both"


def test_task_menu_contains_requested_tasks():
    assert [item[0] for item in TASK_MENU] == ["a", "b", "c", "d"]
    assert [item[1] for item in TASK_MENU] == ["person", "chair", "both", "density"]


def test_mode_classes_match_requested_detection():
    assert MODE_CLASSES["person"] == [0]
    assert MODE_CLASSES["chair"] == [56]
    assert MODE_CLASSES["both"] == [0, 56]
    assert MODE_CLASSES["density"] == [0]


def test_empty_chair_is_chair_without_nearby_person():
    chairs = [(10, 10, 50, 50), (100, 100, 140, 140)]
    people = [(12, 12, 48, 48)]
    assert count_empty_chairs(chairs, people, max_distance=20) == 1


def test_density_levels_use_occupancy_ratio():
    assert classify_density(0, capacity=10)["level"] == "low"
    assert classify_density(5, capacity=10)["level"] == "medium"
    assert classify_density(9, capacity=10)["level"] == "high"
    assert classify_density(10, capacity=10)["level"] == "critical"


def test_density_rejects_invalid_capacity():
    try:
        classify_density(1, capacity=0)
    except ValueError as exc:
        assert "capacity" in str(exc)
    else:
        raise AssertionError("capacity=0 harus ditolak")


def test_source_priority_prefers_explicit_then_snapshot_then_stream():
    assert resolve_source("rtsp://explicit", "https://snapshot", "https://wall") == "rtsp://explicit"
    assert resolve_source("", "https://snapshot", "https://wall") == "https://snapshot"
    assert resolve_source("", "", "rtsp://stream") == "rtsp://stream"
    assert resolve_source("", "", "") == ""


def test_available_models_returns_local_pt_files(tmp_path):
    (tmp_path / "yolo11n.pt").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("x")
    assert available_models(tmp_path) == ["yolo11n.pt"]


def test_available_models_returns_empty_when_no_weights(tmp_path):
    assert available_models(tmp_path) == []


def test_startup_info_redacts_source_and_contains_runtime_fields():
    info = startup_info("person", "yolo11n.pt", "rtsp://user:secret@camera/stream", "cpu")
    assert info["status"] == "VIDEO AKTIF"
    assert info["task"] == "person"
    assert "secret" not in info["source"]
    assert info["device"] == "cpu"
