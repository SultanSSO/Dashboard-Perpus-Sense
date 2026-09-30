# Product Requirements Document (PRD) — Vision Agent

## 1. Product Name
**Vision Agent**

## 2. Product Vision
Vision Agent adalah platform monitoring cerdas yang mengintegrasikan CCTV existing dengan computer vision dan persistent agent orchestration. Agent pusat **Hermes** menerjemahkan instruksi natural-language menjadi monitoring tasks yang aman, persistent, terukur, dan dapat dilaporkan melalui Dashboard, CLI, dan Telegram.

## 3. Product Goals

- Menggunakan CCTV existing tanpa mengganti NVR/infra video bila tidak diperlukan.
- Menyediakan people detection/counting real-time atau sampled inference.
- Memungkinkan user membuat ad-hoc dan standing monitoring task dengan bahasa natural.
- Menghasilkan alert anomaly operasional secara proaktif namun tidak spammy.
- Menghasilkan task report dan daily report berdasarkan data deterministic.
- Menjaga security, auditability, dan least privilege sejak V1.
- Menyediakan foundation yang dapat berkembang ke tracking, entry/exit, learned anomaly dan multi-camera reasoning.

## 4. Non-Goals V1

- Person re-identification lintas kamera.
- Full behavior understanding.
- Fight/suspicious-behavior classifier khusus.
- ML anomaly model yang belajar sendiri secara penuh.
- Menggantikan NVR sebagai continuous video recorder.
- Fine-tuning model vision kecuali benchmark menunjukkan kebutuhan.
- Autonomous infrastructure administration oleh Hermes.

## 5. Primary Users

### Super Admin
Akses penuh ke configuration, model/profile, cameras, tasks, audit, dan Hermes advanced operations sesuai policy.

### Future Roles
- Operator / Security
- Viewer / Business user
- System integrator / service account

## 6. Key User Stories

- Sebagai Super Admin, saya dapat bertanya berapa jumlah orang yang terlihat di kamera tertentu.
- Saya dapat berkata “pantau lobby sampai jam 10 malam” dan task tetap berjalan walau sesi chat selesai.
- Saya dapat membuat standing task untuk after-hours monitoring.
- Saya mendapat alert bila threshold/presence/spike/camera-health condition terpenuhi.
- Saya mendapat notification resolution ketika kondisi kembali normal.
- Saya dapat meminta report task/hari tertentu dalam bahasa natural.
- Saya dapat mengetahui alasan sebuah alert melalui data source, time, count, threshold, dan task ID.
- Saya dapat mengubah bounding-box visualization tanpa mematikan inference.
- Saya dapat mengatur vision profile per kamera tanpa hardcoding model.
- Saya dapat meninjau audit trail tindakan Hermes.

## 7. Functional Requirements

### 7.1 Camera Registry
- CRUD camera metadata sesuai role.
- `credential_ref`, bukan raw secret di metadata public.
- camera location/context/priority/profile/capabilities.
- health status dan last seen.

### 7.2 Media Ingestion
- RTSP source.
- reconnect/backoff.
- latest-frame sampling untuk inference.
- browser-safe playback via media gateway.

### 7.3 Vision V1
- Official pretrained Ultralytics model.
- class filter `person`.
- configurable confidence/IOU/input size/inference FPS.
- unified detection output.
- people count current observation.
- no mandatory fine-tuning.

### 7.4 Task Engine
- ad-hoc task.
- recurring/standing task.
- start/end schedule.
- camera scope.
- rules.
- allowed actions.
- autonomy level.
- state lifecycle.
- persistence across restart.

### 7.5 Rule / Event Engine
V1 event types minimum:
- `PEOPLE_THRESHOLD_EXCEEDED`
- `AFTER_HOURS_PRESENCE`
- `VISITOR_SPIKE`
- `CAMERA_OFFLINE`
- `CAMERA_RECOVERED`
- `VISION_DEGRADED`
- `TASK_COMPLETED/FAILED/DEGRADED`

Rules support duration/persistence, cooldown, severity, schedule, and resolution.

### 7.6 Hermes
- memahami user request menjadi structured intent/task proposal;
- resolve camera dari name/location metadata;
- tool calling melalui policy gate;
- task-bound behavior;
- tidak menciptakan objective baru;
- tidak mengarang observation/state;
- natural confirmation/alert/report/follow-up;
- membedakan observed/inferred/unknown ketika perlu.

### 7.7 Analytics & Reporting
- average occupancy;
- peak count/time;
- event counts;
- after-hours activity;
- camera downtime;
- task result/status;
- report daily/task/custom range;
- structured computation before LLM narration.

### 7.8 Notifications
- dashboard realtime event;
- Telegram;
- CLI result/event view;
- dedup/cooldown/stateful event lifecycle.

### 7.9 Dashboard
- camera view;
- bounding box on/off visualization;
- people count;
- camera/Hermes/task status;
- active task list;
- event feed;
- analytics charts;
- report view;
- audit/admin pages sesuai role.

## 8. Non-Functional Requirements

### Reliability
- Task state survives process restart.
- Camera failure does not crash control plane.
- latest-frame queues are bounded.
- health checks and worker heartbeat.

### Security
- TLS external traffic.
- RBAC and backend authorization.
- secret isolation.
- audit trail.
- no arbitrary shell for Hermes.

### Performance
- inference FPS configurable independently from video playback FPS.
- per-camera vision profiles.
- ability to reduce low-priority inference under load.

### Observability
- CPU/RAM/GPU/VRAM.
- inference latency/FPS.
- dropped frames.
- stream status.
- task/event/notification metrics.
- DB/Redis health.

### Extensibility
Stable contracts for ModelAdapter, Task, Rule, Event, Tool, MemoryProvider, and NotificationProvider.

## 9. Success Metrics V1

- Stable people counting on representative CCTV scenes at accepted accuracy threshold established by internal benchmark.
- Persistent tasks recover correctly after service restart.
- Event alert false-spam suppressed by duration/cooldown.
- No unauthorized action can be executed through natural-language bypass.
- Reporting values match deterministic analytics output.
- Camera credential never reaches browser/Hermes prompt.
- V1.5 tracking can be integrated without redesigning core Task/Event schema.

## 10. Open Decisions Before Implementation

- Exact Ultralytics model/size after benchmark.
- Expected initial camera count and resolution/codec.
- Required video playback method (WebRTC/HLS).
- Existing NVR capabilities.
- Telegram authorization workflow.
- Retention periods for observations/events/snapshots/audit.
- LLM deployment choice for Hermes (local/API) and latency/cost target.
