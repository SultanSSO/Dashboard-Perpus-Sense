# Task, Rule & Event Specification

## 1. Task Types

### QUERY
Immediate read-only request.

### MONITOR
Time-bound monitoring task.

### STANDING_MONITOR
Recurring/persistent schedule.

### REPORT
Generate report for task/time range.

Future task types may include incident review, cross-camera search, or investigation workflows.

## 2. Task Schema

```json
{
  "task_id": "TASK-20260910-001",
  "name": "Night Lobby Monitoring",
  "type": "MONITOR",
  "status": "RUNNING",
  "created_by": "USER-001",
  "created_via": "telegram",
  "goal": "Monitor after-hours lobby activity",
  "camera_ids": ["CAM_LOBBY_01"],
  "schedule": {
    "start_at": "2026-09-10T20:00:00+07:00",
    "end_at": "2026-09-10T23:00:00+07:00",
    "timezone": "Asia/Jakarta"
  },
  "autonomy_level": 1,
  "allowed_actions": ["notify", "report", "read_snapshot"],
  "vision_profile": "balanced",
  "notification_channels": ["dashboard", "telegram"]
}
```

## 3. Task Lifecycle

```text
CREATED → VALIDATING → SCHEDULED/RUNNING
                       ├→ PAUSED → RUNNING
                       ├→ DEGRADED → RUNNING
                       ├→ FAILED
                       ├→ CANCELLED
                       ├→ EXPIRED
                       └→ COMPLETED
```

Task state transitions must be persisted and audited.

## 4. V1 Rule Types

### PEOPLE_THRESHOLD
```text
people_count > threshold for duration
```

### AFTER_HOURS_PRESENCE
```text
local_time within restricted window AND people_count > threshold
```

### VISITOR_SPIKE
Example deterministic strategy:
```text
current smoothed count >= max(min_count, baseline * multiplier)
for persistence window
```

### CAMERA_HEALTH
```text
health != ONLINE for configured duration
```

## 5. Rule Common Fields

```json
{
  "rule_id": "RULE-001",
  "task_id": "TASK-...",
  "type": "AFTER_HOURS_PRESENCE",
  "enabled": true,
  "camera_ids": ["CAM_ROOM_01"],
  "severity": "warning",
  "persistence_seconds": 60,
  "cooldown_seconds": 300,
  "resolution_seconds": 30,
  "conditions": {},
  "actions": ["notify"]
}
```

## 6. Event Lifecycle

Events are stateful, not stateless notifications.

```text
CANDIDATE
   ↓ passes persistence
OPEN
   ↓ meaningful changes
UPDATED
   ↓ normal condition sustained
RESOLVED
```

`OPEN` and `RESOLVED` should usually create notifications. `UPDATED` is notification-worthy only if materially changed.

## 7. Event Schema

```json
{
  "event_id": "EVT-001",
  "event_type": "VISITOR_SPIKE",
  "state": "OPEN",
  "severity": "warning",
  "task_id": "TASK-001",
  "camera_id": "CAM_LOBBY_01",
  "opened_at": "...",
  "updated_at": "...",
  "resolved_at": null,
  "data": {
    "current_count": 27,
    "baseline": 8.4,
    "multiplier": 3.21
  },
  "evidence_refs": []
}
```

## 8. Deduplication
Event key can be based on `task_id + rule_id + camera_id + event_type`; repeated samples update the same open event rather than creating a new alert.

## 9. Future Rule/Events
Tracking, line crossing, ROI intrusion, dwell/loitering, queue length, learned anomaly, cross-camera correlation. These should preserve the common event envelope.
