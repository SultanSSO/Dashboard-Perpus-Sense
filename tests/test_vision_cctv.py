from vision_cctv import resolve_source, snapshot_retry_delay


def test_snapshot_retry_delay_uses_bounded_exponential_backoff():
    assert [snapshot_retry_delay(attempt) for attempt in range(1, 7)] == [1, 2, 4, 8, 16, 30]


def test_source_precedence_prefers_cli_over_snapshot_and_stream():
    assert resolve_source("rtsp://explicit", "https://snapshot", "https://wall") == "rtsp://explicit"
    assert resolve_source("", "https://snapshot", "rtsp://stream") == "https://snapshot"
    assert resolve_source("", "", "rtsp://stream") == "rtsp://stream"
