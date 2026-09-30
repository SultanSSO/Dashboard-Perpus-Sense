# System Architecture Design — Vision Agent

## 1. Architecture Style
Modular service architecture with event-driven coordination. V1 may deploy services in a single Docker Compose host, while logical boundaries are preserved for future scale-out.

## 2. Service Map

```text
[Experience]
Dashboard | CLI | Telegram
        |
[Edge/API]
Reverse Proxy / API Gateway / Auth
        |
[Agent & Control]
Hermes Runtime
Tool & Policy Gateway
Camera Manager
Vision Manager
Task Engine / Scheduler
Rule Engine
Analytics / Report
Notification
Resource Manager
        |
[Realtime]
Redis Streams / cache / heartbeat
        |
[Vision]
Media Gateway -> Vision Worker(s) -> Unified Observations
        |
[Data]
PostgreSQL | Object Storage | Existing NVR
```

## 3. Service Responsibilities

### API Gateway
- external authentication context;
- request ID / trace ID;
- role/user/channel identity;
- rate limits and API routing.

### Hermes Runtime
- natural-language interpretation;
- goal/scope extraction;
- tool selection;
- follow-up conversation;
- natural language generation.

Not responsible for scheduler, direct DB mutation, raw credential access, raw frame processing.

### Tool & Policy Gateway
- expose typed tools;
- validate arguments;
- authorization and task-scope checks;
- record tool audit;
- call underlying service.

### Camera Manager
- metadata registry;
- credential reference resolution through secure backend;
- health state;
- camera lookup by name/location/capability.

### Media Gateway
- connect RTSP;
- isolate credentials;
- distribute video to vision worker and browser stream path;
- reconnect/backoff.

### Vision Worker
- receive sampled/latest frames;
- model adapter inference;
- optional future tracker/ROI;
- emit unified observation;
- never make permission/business decisions.

### Vision Manager
- assign cameras to workers;
- apply profiles;
- expose controlled start/stop/profile changes;
- coordinate resource manager.

### Task Engine / Scheduler
- persist task definition and lifecycle;
- recurring schedules;
- start/expire/cancel/pause/resume;
- restore active task after restart.

### Rule Engine
- bind observations to active task rules;
- duration/persistence/cooldown;
- event start/update/resolution lifecycle;
- deterministic V1 conditions.

### Analytics Engine
- aggregation windows;
- average/peak/trend;
- simple spike baseline;
- report data payload.

### Report Engine
- structured report data;
- artifact generation/export;
- Hermes may narrate structured output.

### Notification Service
- dashboard websocket;
- Telegram adapter;
- retry/delivery record;
- channel preferences.

### Resource Manager
V1 minimal metrics/alerts; later adaptive worker assignment and inference throttling.

## 4. Internal Contracts

### Unified Observation
```json
{
  "observation_id": "OBS-...",
  "camera_id": "CAM_LOBBY_01",
  "timestamp": "2026-09-10T21:15:04+07:00",
  "people_count": 8,
  "model": "yolo11s.pt",
  "inference_ms": 31.2,
  "source_fps": 25,
  "inference_fps": 5,
  "quality": {
    "status": "normal"
  }
}
```

### Event
```json
{
  "event_id": "EVT-...",
  "event_type": "AFTER_HOURS_PRESENCE",
  "state": "OPEN",
  "severity": "warning",
  "camera_id": "CAM_LOBBY_01",
  "task_id": "TASK-104",
  "opened_at": "...",
  "last_observed_at": "...",
  "data": {
    "people_count": 8,
    "threshold": 0,
    "after": "21:00",
    "duration_seconds": 61
  }
}
```

## 5. Concurrency Model

- Each camera ingestion path should use bounded/latest-frame buffers.
- Vision workers may process cameras asynchronously.
- Heavy CPU decode/preprocessing must not block API/Hermes loop.
- Task/rule evaluation should be independent of LLM availability.
- Event delivery should be idempotent where practical.

## 6. Persistence Guarantees

Persist before claiming task creation success. Critical lifecycle transitions should be transactional. Redis may accelerate realtime communication, but persistent task/event state should be recoverable from PostgreSQL.

## 7. Deployment Boundaries V1

Suggested containers:

```text
reverse-proxy
api
hermes-runtime
task-worker
rule-analytics-worker
vision-worker-gpu
media-gateway
postgres
redis
minio
prometheus
grafana
```

Containers may initially share one physical host; avoid coding assumptions that they always do.

## 8. Evolution Strategy

V1.5 adds tracker/ROI/line-crossing modules inside/beside Vision Worker while preserving observation/event contracts. V2 adds statistical/ML anomaly detectors behind `AnomalyDetector` interfaces. V3 adds cross-camera services but Hermes continues operating through typed tools and events.
