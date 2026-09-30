# Configuration & Schema Examples

## 1. Camera Metadata

```json
{
  "camera_id": "CAM_LOBBY_01",
  "name": "Main Lobby",
  "enabled": true,
  "priority": "high",
  "location": {
    "site": "HQ",
    "building": "Building A",
    "floor": "Ground Floor",
    "zone": "Lobby"
  },
  "description": "Memantau pintu masuk utama dan area resepsionis.",
  "stream": {
    "credential_ref": "cctv/cam_lobby_01",
    "transport": "rtsp"
  },
  "vision": {
    "profile_id": "balanced",
    "roi_ids": [],
    "counting_line_ids": []
  },
  "capabilities": {
    "people_detection": true,
    "tracking": false,
    "entry_exit": false
  }
}
```

## 2. Development Secret Mapping

```env
CCTV_CAM_LOBBY_01_URL=rtsp://...
CCTV_CAM_LOBBY_01_USERNAME=...
CCTV_CAM_LOBBY_01_PASSWORD=...
TELEGRAM_BOT_TOKEN=...
DATABASE_URL=...
REDIS_URL=...
```

Do not commit `.env`.

## 3. Vision Profile

```json
{
  "profile_id": "balanced",
  "model_adapter": "ultralytics",
  "model": "yolo11s.pt",
  "device": "cuda:0",
  "classes": ["person"],
  "confidence_threshold": 0.45,
  "iou_threshold": 0.50,
  "input_size": 640,
  "inference_fps": 5,
  "tracking": {
    "enabled": false,
    "tracker": null
  }
}
```

## 4. Task

```json
{
  "task_id": "TASK-001",
  "type": "MONITOR",
  "goal": "Monitor lobby after hours",
  "camera_ids": ["CAM_LOBBY_01"],
  "schedule": {
    "start_at": "2026-09-10T20:00:00+07:00",
    "end_at": "2026-09-10T23:00:00+07:00"
  },
  "autonomy_level": 1,
  "rule_ids": ["RULE-001"],
  "notification_channels": ["dashboard", "telegram"]
}
```

## 5. After-Hours Rule

```json
{
  "rule_id": "RULE-001",
  "type": "AFTER_HOURS_PRESENCE",
  "camera_ids": ["CAM_LOBBY_01"],
  "conditions": {
    "after": "21:00",
    "people_count": {"operator": ">", "value": 0}
  },
  "persistence_seconds": 60,
  "cooldown_seconds": 300,
  "resolution_seconds": 30,
  "severity": "warning"
}
```

## 6. Visitor Spike Rule

```json
{
  "rule_id": "RULE-002",
  "type": "VISITOR_SPIKE",
  "conditions": {
    "baseline_window_minutes": 10,
    "multiplier": 2.0,
    "minimum_count": 10
  },
  "persistence_seconds": 30,
  "cooldown_seconds": 300
}
```

## 7. Unified Detection (future-proof)

```json
{
  "frame_time": "...",
  "objects": [
    {
      "class": "person",
      "confidence": 0.91,
      "bbox_xyxy": [100, 90, 220, 400],
      "track_id": null
    }
  ]
}
```

## 8. Observation

```json
{
  "observation_id": "OBS-001",
  "camera_id": "CAM_LOBBY_01",
  "timestamp": "...",
  "people_count": 8,
  "model": "yolo11s.pt",
  "inference_ms": 31.2,
  "quality": {"status": "normal"}
}
```

## 9. Event

```json
{
  "event_id": "EVT-001",
  "event_type": "AFTER_HOURS_PRESENCE",
  "state": "OPEN",
  "severity": "warning",
  "camera_id": "CAM_LOBBY_01",
  "task_id": "TASK-001",
  "data": {
    "people_count": 3,
    "duration_seconds": 61
  },
  "evidence_refs": []
}
```

## 10. Report Summary Payload

```json
{
  "period": {"start": "...", "end": "..."},
  "cameras": ["CAM_LOBBY_01"],
  "metrics": {
    "average_people_count": 8.7,
    "peak_people_count": 31,
    "peak_time": "12:34",
    "event_count": 4,
    "camera_downtime_seconds": 53
  },
  "events_by_type": {
    "VISITOR_SPIKE": 2,
    "AFTER_HOURS_PRESENCE": 1,
    "CAMERA_OFFLINE": 1
  }
}
```
