# Rangkuman Lengkap Diskusi Awal — Vision Agent & Hermes

**Tanggal baseline:** 10 September 2026
**Status:** Concept baseline sebelum technical implementation
**Tujuan dokumen:** Menjaga seluruh insight, keputusan, prinsip, opsi pengembangan, dan batasan yang dibahas agar tidak hilang ketika proyek masuk fase implementasi.

---

## 1. Konteks Awal Produk

Vision Agent dirancang sebagai sistem yang mengintegrasikan CCTV yang sudah ada dengan computer vision untuk mendeteksi dan menghitung manusia, lalu mengelola monitoring melalui agent pusat bernama **Hermes**. Sistem ditujukan agar tidak hanya menjadi dashboard CCTV dengan bounding box, tetapi berkembang menjadi **operator virtual** yang dapat menerima instruksi, membuat task yang terus berjalan, mengamati kondisi, melaporkan kejadian penting, membuat ringkasan, dan berinteraksi melalui Dashboard, CLI, serta Telegram.

Pengembangan awal berfokus pada **Super Admin**, sementara role lain seperti operator/security/user biasa dapat ditambahkan kemudian. Credential CCTV saat ini dapat tetap berasal dari `.env`, tetapi metadata kamera dipisahkan ke konfigurasi JSON yang menjelaskan identitas, lokasi, konteks, kemampuan, dan vision profile kamera.

Model vision direncanakan mendukung beberapa model seperti YOLOv8, YOLO11, YOLO26 dan DF-DETR/RT-DETR-family melalui adapter, tetapi implementasi V1 tidak perlu memasang semua model. Model pretrained resmi Ultralytics dinilai sudah lebih dari cukup untuk kebutuhan deteksi manusia dasar sehingga **fine-tuning bukan requirement V1**.

---

## 2. Definisi Fundamental: Hermes Bukan Object Detector

Pemisahan konsep terpenting adalah:

```text
Vision Model / Vision Worker
= perception / melihat

Rule & Analytics Engine
= evaluation / menghitung kondisi

Task Engine
= execution / menjaga pekerjaan tetap hidup

Hermes
= understanding + reasoning + orchestration + communication
```

YOLO menerima frame dan menghasilkan detection seperti class `person`, confidence, bounding box, dan jumlah manusia pada observation tertentu. Hermes **tidak menerima dan menganalisis semua frame**. Hermes seharusnya menerima representasi yang sudah mempunyai makna: observation, event, analytics summary, task state, dan health state.

Contoh:

```text
CCTV frame
   ↓
Vision Worker / YOLO
   ↓
people_count = 14
   ↓
Rule Engine
   ↓
after_hours_presence
   ↓
Hermes
   ↓
"Masih terdeteksi 14 orang di Lobby Utama setelah jam operasional."
```

Dengan pembagian ini, Hermes tetap dapat diganti model LLM-nya tanpa mengubah vision pipeline; demikian juga YOLO dapat diganti model lain tanpa mengubah konsep Hermes.

---

## 3. Kapan Sistem Layak Disebut Agent

Assistant sederhana bersifat request-response:

```text
User → Question → Answer
```

Hermes harus mempunyai kemampuan lebih jauh:

```text
Request
  ↓
Understand
  ↓
Resolve context
  ↓
Create / update task
  ↓
Task continues running
  ↓
Observe events / system state
  ↓
Evaluate / verify
  ↓
Act or report
  ↓
Continue / complete / fail
```

Contoh task:

> Pantau Meeting Room A sampai pukul 22:00. Jika setelah pukul 19:00 masih ada lebih dari 5 orang selama 30 detik, beri tahu saya.

Hermes tidak perlu tetap aktif sebagai loop LLM. Hermes menerjemahkan perintah menjadi **task + rule terstruktur**, Task Engine menjalankannya, dan Hermes dipanggil kembali saat perlu menjelaskan event atau menerima follow-up.

Hal inilah yang membuat Vision Agent terasa seperti agent meskipun vision model V1 masih melakukan people detection/counting yang relatif sederhana.

---

## 4. Persistent Task dan Standing Task

Dibahas dua kategori task:

### 4.1 Ad-hoc Task
Task mempunyai akhir tertentu.

Contoh:

> Pantau lobby sampai pukul 17:00.

Task selesai atau expire pada akhir periode.

### 4.2 Standing / Persistent Task
Task berulang dan tetap ada hingga dinonaktifkan.

Contoh:

> Setiap hari setelah pukul 21:00, laporkan jika masih ada orang di ruang server.

Task semacam ini tidak boleh bergantung pada conversation context LLM. Ia harus disimpan di database dan dieksekusi Task Engine/Scheduler.

Lifecycle yang dibahas:

```text
CREATED
   ↓
VALIDATING
   ↓
RUNNING
   ├── PAUSED
   ├── DEGRADED
   └── FAILED
   ↓
COMPLETED / EXPIRED / CANCELLED
```

Jika kamera offline, task dapat menjadi `DEGRADED` tanpa harus hilang. Hermes kemudian dapat melaporkan bahwa coverage task berkurang.

---

## 5. Agent Harus Proaktif, Tetapi Hanya di Dalam Scope

Konsep utama yang disepakati:

> **Powerful reasoning, narrow authority.**

Hermes boleh proaktif **di dalam task**, tetapi tidak boleh menciptakan objective baru sendiri.

Jika user berkata:

> Pantau lobby.

Hermes tidak boleh memutuskan sendiri untuk memonitor seluruh gedung hanya karena melihat lobby ramai. Namun bila task memberi izin untuk mengirim alert, Hermes tidak perlu bertanya lagi ketika threshold terpenuhi.

Prinsip soul penting:

> **You do not create objectives for yourself.**

Inisiatif diperbolehkan untuk verifikasi, observasi, reporting, dan tindakan reversible yang memang termasuk allowed actions task.

---

## 6. Autonomy Levels

Untuk mencegah Hermes terlalu overpower, dibahas autonomy level:

### Level 0 — Advisory
Read/analyse/report. Tidak mengubah state.

### Level 1 — Monitoring
Observe, create/consume event, create report, notify. Ini cocok sebagai default V1.

### Level 2 — Limited Action
Tindakan reversible dan terbatas, misalnya request snapshot, start event clip, atau mengubah inference profile jika task/policy mengizinkan.

### Level 3 — Approval Required / Sensitive
Tindakan seperti disable camera, restart sistem, ubah credential, atau perubahan global harus membutuhkan approval Super Admin dan/atau policy eksplisit.

V1 sebaiknya mayoritas Level 0–1, dengan sedikit Level 2 bila benar-benar diperlukan.

---

## 7. Soul Hermes

Soul diperlukan, tetapi **bukan security boundary**. Soul menentukan identitas, tujuan, gaya kerja, dan komunikasi.

Substansi yang dibahas:

```text
You are Hermes, the control agent of Vision Agent.

Your primary purpose is to execute and monitor authorized
vision-monitoring tasks.

You are proactive within an active task,
but you do not create objectives for yourself.

You may observe broadly enough to complete a task,
but may only act within the task's authorized scope.

Prefer reliable system data over assumptions.
Never invent camera observations, events, counts,
system states, or task results.

Distinguish clearly between:
- observed
- inferred
- unknown

Use tools to obtain operational facts.
Report important events naturally and concisely.
Avoid unnecessary alerts.
Continue persistent tasks until completion,
cancellation, expiration, or failure.
Do not expand a user's task without authorization.
```

Communication Hermes sebaiknya natural, profesional, ringkas, tenang, dan contextual. Bukan robotic, tetapi juga bukan terlalu casual.

Contoh yang dihindari:

```text
ANOMALY DETECTED. PEOPLE_COUNT_THRESHOLD_EXCEEDED.
```

Contoh yang diinginkan:

> Ada kenaikan aktivitas di Lobby Utama. Saat ini terdeteksi 26 orang, melewati batas 20 orang. Saya masih memantau kondisi ini.

Policy tindakan tetap strict; bahasa boleh fleksibel:

```text
ACTION POLICY = STRICT
LANGUAGE = FLEXIBLE
```

---

## 8. Hermes Harus Tahu Kapan Diam

Agent yang bagus tidak spam notification. Event perlu state, persistence, cooldown, dan meaningful-change logic.

Contoh:

```text
EVENT START → notify
condition continues → silent
meaningful change → update
condition resolved → resolution notification
```

Contoh behavior:

- 21:05: 8 orang setelah jam operasional → satu alert.
- 21:06–21:25: kondisi sama → tidak spam.
- 21:32: jumlah naik menjadi 24 → meaningful update.
- 21:47: ruangan kosong → resolution report.

---

## 9. Anomaly V1: Rule-Based dan Statistik Sederhana

Tidak perlu learned anomaly model untuk membuat V1 berguna. V1 dapat mulai dari:

1. **Threshold:** `people_count > X`.
2. **Time-based / after-hours:** `time > curfew AND people_count > 0`.
3. **Simple visitor spike:** current count jauh di atas moving average/baseline pendek.
4. **Camera health:** offline, RTSP error, inference stopped/degraded.

Gunakan persistence, misalnya kondisi harus bertahan 30–60 detik, dan cooldown agar tidak terjadi alert storm.

Future capabilities yang sengaja ditunda tetapi disiapkan arsitekturnya:

- ROI / zones
- tracking
- line crossing
- entry / exit count
- unique visitor approximation
- dwell time / loitering
- crowd density
- wrong-way movement
- restricted-zone intrusion
- historical learned baseline
- behavior anomaly
- cross-camera reasoning
- re-identification
- predictive analytics

---

## 10. People Counting Bukan Satu Definisi

Dibahas pentingnya membedakan:

```text
Current occupancy
= berapa orang terlihat sekarang

Entry count
= berapa crossing masuk

Exit count
= berapa crossing keluar

Unique visitors
= berapa identitas berbeda (jauh lebih sulit)
```

YOLO object detection langsung mendukung `current visible people count`, tetapi entry/exit membutuhkan tracker + virtual line + direction. Unique visitors dan cross-camera identity lebih kompleks dan bukan target V1.

---

## 11. Strategi Model Vision

Keputusan desain:

- Gunakan **official pretrained Ultralytics model** untuk V1.
- Tidak melakukan fine-tuning kecuali benchmark data nyata menunjukkan kebutuhan.
- Fine-tuning dianggap **optional capability**, bukan requirement arsitektur.
- Implementasikan `VisionModelAdapter` sehingga backend tidak terkunci pada satu model.
- V1 sebaiknya menjalankan satu model utama yang sudah teruji pada CCTV aktual, bukan empat model sekaligus.

Model dipilih berdasarkan benchmark domain CCTV sendiri, bukan hanya “model terbaru”. Ukur:

- people count accuracy
- false positive / false negative
- inference latency
- inference FPS
- VRAM usage
- crowded-scene behavior
- low-light / backlight / high-angle stability

Model output dinormalisasi ke unified detection format.

---

## 12. Vision Profile dan Resource Control

Video display FPS dan inference FPS tidak harus sama.

Contoh:

```text
CCTV stream = 25 FPS
AI inference = 5 FPS
Dashboard video = 25 FPS
```

Vision profile lebih baik daripada sekadar refresh rate:

```json
{
  "profile_id": "balanced",
  "model": "yolo11s.pt",
  "device": "cuda:0",
  "classes": ["person"],
  "confidence_threshold": 0.45,
  "iou_threshold": 0.50,
  "inference_fps": 5,
  "input_size": 640,
  "tracking": false
}
```

Contoh profile:

- LOW_RESOURCE: nano/small + 1–2 FPS
- BALANCED: small + ±5 FPS
- REALTIME: small + ±10 FPS
- HIGH_ACCURACY: medium/heavier model + controlled FPS

Camera dapat mempunyai priority sehingga Resource Manager kelak dapat menurunkan inference kamera low-priority bila GPU overload.

Bounding box toggle hanya mengubah **visualization**, bukan mematikan detection/tracking/counting.

---

## 13. Architecture: Control Plane vs Vision/Data Plane

Arsitektur sebaiknya modular dan memisahkan:

### Control Plane
- API Gateway
- Hermes Agent Runtime
- Task Engine/Scheduler
- Rule Engine
- Analytics/Report Engine
- Camera Manager
- Vision Manager
- Resource Manager
- Notification service
- Authentication/RBAC/Policy

### Vision/Data Plane
- Media Gateway
- RTSP ingestion
- video decode
- Vision Workers
- model inference
- future tracking/ROI/line-crossing
- observation production

Manfaatnya: jika GPU worker bermasalah, Hermes/API tidak ikut mati dan masih dapat menjelaskan kondisi degraded.

---

## 14. Media Flow

CCTV tidak sebaiknya dikirim langsung ke browser dan credential kamera tidak boleh bocor ke frontend.

Target flow:

```text
CCTV / RTSP
    ↓
Media Gateway
   ├── Vision Worker
   └── WebRTC/HLS → Dashboard
```

Media Gateway dapat menggunakan FFmpeg/GStreamer dan media server yang sesuai. Credential hanya diketahui service yang berwenang.

---

## 15. Event-Driven Architecture

Hermes tidak memproses semua frame dan tidak perlu polling database secara agresif.

Vision Worker menghasilkan observation/event ke event layer. Untuk skala V1, Redis/Redis Streams dinilai cukup sebagai cache/event/queue layer, sedangkan PostgreSQL menjadi persistent source-of-truth.

Contoh event:

```text
VISITOR_SPIKE
AFTER_HOURS_PERSON
THRESHOLD_EXCEEDED
CAMERA_OFFLINE
CAMERA_RECOVERED
TASK_COMPLETED
VISION_WORKER_DEGRADED
```

Kafka/NATS/Pulsar dapat dipertimbangkan kelak bila scale menjadi ratusan/ribuan kamera atau event throughput memerlukan distributed streaming platform lebih besar.

---

## 16. Database dan Storage

### PostgreSQL — Source of Truth
Menyimpan:

- users, roles, permissions
- cameras, metadata, vision profiles
- tasks dan task rules
- observations / aggregates
- events dan alert state
- reports
- audit logs
- tool calls / agent actions
- configuration references

### Redis — Ephemeral / Realtime
Digunakan untuk:

- event stream
- queues
- current state/cache
- latest count
- worker heartbeats
- distributed locks jika dibutuhkan

Redis bukan database permanen utama.

### Object Storage
Snapshot, event clip, report export, dan artifacts sebaiknya disimpan di MinIO/S3-compatible storage. PostgreSQL hanya menyimpan metadata/path/reference.

### Video Recording
Vision Agent tidak harus menggantikan NVR. Continuous recording sebaiknya tetap di CCTV/NVR existing bila sudah ada. Vision Agent menyimpan observation, event, selected snapshot, dan optional short event clip. Ini menghindari storage video yang dapat tumbuh menjadi puluhan GB per kamera per hari.

---

## 17. Hardware dan Memory

Beban utama sistem diperkirakan berada pada **video decode + GPU inference**, bukan pada Hermes/LLM.

Baseline development yang dibahas:

- CPU modern 8+ core
- RAM 32 GB
- NVIDIA GPU 8–12 GB VRAM
- NVMe 1 TB
- 1 GbE

Pilot/V1 production yang lebih nyaman:

- CPU 12–16+ core
- RAM 64 GB
- NVIDIA GPU 16–24 GB VRAM
- OS/app NVMe ±1 TB
- data NVMe 2 TB+
- 1 GbE minimum; 2.5 GbE preferable bila traffic bertambah
- UPS direkomendasikan

Tidak ada klaim jumlah kamera tetap per GPU karena tergantung resolution, codec, inference FPS, model size, preprocessing, batching, tracking, dan scene complexity. Benchmark CCTV nyata diperlukan.

Vision Worker harus memakai **bounded/latest-frame queue**. Jika inference tertinggal, frame lama dibuang daripada membangun backlog real-time yang panjang.

---

## 18. Scale-Out Hardware

V1 dapat dimulai di satu server menggunakan Docker Compose. Service boundaries tetap dibuat agar nantinya dapat dipindah menjadi beberapa node:

```text
Control/API/Task/DB node
       │
 internal network/event bus
       │
 ┌─────┼─────────────┐
 ↓     ↓             ↓
GPU-01 GPU-02       GPU-03
```

Camera assignment dapat dikelola Vision/Resource Manager. Kubernetes tidak perlu V1, tetapi containerization menjaga jalan migrasi tetap tersedia jika scale membutuhkan orchestration cluster.

---

## 19. Security Principles

Security harus dianggap requirement V1 karena sumber data adalah CCTV.

### Network
- Internet tidak langsung mengakses RTSP, camera web admin, PostgreSQL, Redis, atau worker.
- CCTV sebaiknya berada di VLAN/private segment.
- Media gateway/service tertentu menjadi bridge terkontrol.
- External access masuk melalui HTTPS/TLS reverse proxy/API gateway.

### Secret
Metadata camera memakai `credential_ref`, bukan password langsung. Development dapat memakai `.env`; production idealnya menggunakan Secret Manager/Vault.

Hermes tidak boleh memiliki tool untuk membaca credential mentah.

### Tool Boundary
Jangan berikan arbitrary `execute_shell(command)` kepada Hermes. Gunakan capability khusus seperti `camera.status`, `vision.change_profile`, `task.create`, dan `report.generate`.

### RBAC / Policy
Authorization harus dicek sebelum Hermes dan dicek lagi di tool/backend. Memory atau prompt tidak dapat menciptakan privilege.

### Telegram
Telegram user ID harus dipetakan ke system user/role. Pesan bot tidak otomatis trusted. Bot token adalah secret.

### Audit
Catat user/channel/request, proposed action, tool invocation, task/event, result, dan status. Audit log penting untuk debugging dan governance.

---

## 20. Hermes Memory dan Persistence

Persistent memory dinilai berguna tetapi **tidak wajib untuk V1**.

Pemisahan wajib:

```text
Operational State = PostgreSQL
Analytical History = PostgreSQL/time-series layer
Working Context = runtime/session
Cognitive Long-Term Memory = optional memory provider (mis. Mnemosyne)
```

Prinsip:

> **PostgreSQL = what IS true**
> **Analytics = what HAPPENED**
> **Cognitive memory = what Hermes REMEMBERS / LEARNED**
> **Task Engine = what must be DONE**
> **Policy Engine = what Hermes MAY do**
> **Hermes = what it all MEANS**

Task aktif, status kamera, count, rules, permission dan event tidak boleh hanya disimpan sebagai memory agent.

Mnemosyne atau persistent memory layer cocok untuk:

- durable user/reporting preferences
- operator corrections
- validated lessons
- known quirks kamera
- prior decision context
- recurring operational knowledge

Tidak cocok untuk:

- password/token/secret
- raw CCTV frames/detection stream
- latest people count
- authoritative task state
- permission
- setiap chat turn
- asumsi yang belum tervalidasi

Sebaiknya dibuat interface `MemoryProvider` dari V1 sehingga SimpleMemory dapat diganti Mnemosyne/alternative provider di V1.5/V2.

Memory write idealnya menggunakan **promotion policy**: observation → candidate → repeated/confirmed → long-term memory. Memory tidak dapat mengubah authorization.

---

## 21. Data untuk Reporting

Agar reporting tidak mahal dan tidak bergantung pada LLM menghitung jutaan row, backend menghitung aggregate seperti:

- average occupancy
- peak occupancy
- peak time
- event count
- visitor spike count
- after-hours activity duration
- camera downtime
- task success/degraded/failure

Hermes menerima structured summary dan mengubahnya menjadi bahasa manusia.

Contoh:

> Aktivitas tertinggi hari ini terjadi pada pukul 12:34 dengan 31 orang. Dua lonjakan pengunjung terdeteksi dan satu kamera mengalami gangguan selama 53 detik. Tidak ada aktivitas setelah batas operasional yang memenuhi rule aktif.

---

## 22. Natural Language sebagai Interface, Bukan Source of Truth

User dapat memberi perintah natural:

> Pantau seluruh kamera lantai 2 sampai malam. Kalau ada orang setelah jam 21:00 atau salah satu kamera offline, kabari saya.

Hermes menerjemahkannya menjadi structured task/rule. Setelah itu execution deterministic.

Follow-up natural tetap didukung:

- “Pantau saja dulu.” → acknowledgement + continue task
- “Hentikan.” → cancel task jika authorized
- “Buatkan rangkumannya.” → generate report dari data task/event

Hal ini membuat pengalaman agent natural tanpa membuat sistem operasional bergantung pada generative text.

---

## 23. Tooling Hermes

Kategori tool yang dibahas:

### Camera
- list cameras
- get metadata
- get health/status
- snapshot

### Vision
- start/stop processing sesuai policy
- get current observation/count
- change vision profile (restricted)
- future ROI/tracking capability

### Task
- create/list/get/pause/resume/cancel task

### Analytics
- current count
- history
- average/peak
- anomaly summary

### Reporting & Notification
- generate report
- send dashboard/Telegram notification

Tool harus typed, auditable, authorization-aware dan tidak mengekspos secret.

---

## 24. Configuration Structure

Camera JSON sebaiknya berisi descriptive metadata dan reference, bukan credential:

```json
{
  "camera_id": "CAM_LOBBY_01",
  "name": "Main Lobby",
  "location": {
    "building": "Building A",
    "floor": "Ground Floor",
    "zone": "Lobby"
  },
  "description": "Memantau pintu masuk utama dan resepsionis.",
  "stream": {
    "credential_ref": "cctv/cam_lobby_01"
  },
  "vision": {
    "profile": "balanced"
  },
  "priority": "high",
  "enabled": true
}
```

Schema harus siap menerima ROI, counting lines, tracking, dan capability flag pada versi berikutnya.

---

## 25. Technology Direction yang Dibahas

Baseline stack yang disarankan:

- Backend/API: Python + FastAPI
- Vision: PyTorch / Ultralytics
- Media: FFmpeg/GStreamer + media gateway/server
- Database: PostgreSQL
- Realtime/cache/event: Redis Streams
- Object storage: MinIO/S3-compatible
- Dashboard: React/Next.js
- Realtime UI: WebSocket
- Browser stream: WebRTC/HLS
- Auth: session/JWT + RBAC
- Reverse proxy: Nginx/Traefik
- Container: Docker / Docker Compose untuk V1
- Metrics: Prometheus
- Infrastructure dashboard: Grafana
- Logs: structured logs
- Secret V1: `.env`; production: secret manager

Pilihan teknologi dapat berubah, tetapi **service boundary dan contracts** sebaiknya dijaga.

---

## 26. Roadmap Konseptual

### Vision Agent V1
- CCTV integration
- pretrained people detection/count
- camera metadata/registry
- vision profile
- Task Engine + scheduler
- persistent/standing tasks
- threshold rule
- after-hours presence
- simple visitor spike
- camera health
- events
- dashboard / CLI / Telegram
- Hermes natural command + reporting
- PostgreSQL + Redis
- audit/security

### Vision Agent V1.5
- tracking
- ROI
- virtual line
- entry/exit
- occupancy zones
- event clips
- better analytics/statistical baselines
- advanced scheduling
- optional richer persistent memory

### Vision Agent V2
- historical pattern learning
- learned anomaly
- loitering / dwell time
- zone behavior
- resource scheduling
- multiple GPU workers
- richer cognitive memory

### Vision Agent V3
- cross-camera reasoning
- re-identification where justified
- multi-camera tasks
- behavior understanding
- predictive analytics
- advanced planning
- multi-site deployment

Arsitektur dasar tetap sama. Versi baru idealnya hanya menambahkan:

```text
new Vision capability
+ new Analytics capability
+ new Event type
+ new Hermes tool
```

---

## 27. Prinsip Final yang Menjadi Baseline Proyek

1. **Hermes does not own system state. Hermes reasons over system state.**
2. **Powerful reasoning, narrow authority.**
3. **Hermes does not create objectives for itself.**
4. **Vision perceives; deterministic services evaluate and execute; Hermes orchestrates and communicates.**
5. **Task persistence must survive Hermes/model restart.**
6. **Operational truth must never depend on cognitive memory.**
7. **Memory cannot grant authority.**
8. **Security and authorization are backend-enforced, not prompt-enforced.**
9. **Do not fine-tune unless benchmark proves it is necessary.**
10. **Do not process every frame with Hermes; promote frames into observations/events.**
11. **Keep V1 achievable while preserving the architecture required by V2/V3.**
12. **Reports should be computed deterministically and narrated naturally.**
13. **Hermes should communicate like a capable operator: concise, calm, natural, contextual, and non-spammy.**
14. **Continuous video storage is optional and should normally remain the responsibility of the existing NVR; Vision Agent stores semantic data and event evidence.**
15. **Every significant action must be auditable.**

Dokumen ini menjadi baseline konseptual. Bila implementasi nanti menyimpang dari prinsip-prinsip ini, perubahan tersebut sebaiknya dilakukan sebagai keputusan arsitektur yang eksplisit, bukan secara tidak sengaja selama coding.
