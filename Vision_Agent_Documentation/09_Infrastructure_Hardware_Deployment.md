# Infrastructure, Hardware & Deployment

## 1. Workload Characteristics
Primary resource drivers:
1. RTSP/video decoding;
2. image preprocessing;
3. GPU inference;
4. optional tracking/embedding later;
5. browser stream distribution;
6. observation/event persistence.

Hermes text reasoning is not expected to dominate local GPU workload unless the LLM itself is hosted on the same GPU. Prefer capacity isolation if local LLM is used.

## 2. Development Baseline

| Resource | Baseline |
|---|---|
| CPU | Modern 8+ cores |
| RAM | 32 GB |
| GPU | NVIDIA 8–12 GB VRAM |
| Storage | 1 TB NVMe |
| Network | 1 GbE |
| OS | Linux recommended |
| Runtime | Docker Compose |

## 3. Pilot / V1 Production Baseline

| Resource | Recommended starting point |
|---|---|
| CPU | 12–16+ modern cores |
| RAM | 64 GB |
| GPU | NVIDIA 16–24 GB VRAM |
| OS/App disk | ~1 TB NVMe |
| Data/evidence disk | 2 TB+ NVMe/SSD according to retention |
| Network | 1 GbE minimum; 2.5 GbE preferable for larger deployments |
| Power | Quality PSU + UPS recommended |

These are planning ranges, not guarantees of camera count.

## 4. Capacity Variables
Never promise “GPU X = N cameras” without benchmark. Capacity depends on:
- stream resolution;
- source FPS;
- codec;
- decode path;
- inference input size;
- model size;
- inference FPS;
- tracking/ROI/extra models;
- batching strategy;
- scene density;
- rendering/transcoding.

## 5. FPS Strategy

```text
Source stream: 25 FPS
Display:       25 FPS (or media path dependent)
Inference:      2–10 FPS according to profile
```

This is a primary optimization lever.

## 6. Memory Strategy
- bounded frame queue;
- latest-frame preference;
- no unbounded backlog;
- keep raw frame lifetime short;
- monitor process RSS and GPU allocation;
- avoid co-locating too many memory-heavy services on GPU node.

## 7. Storage Strategy
Full video is expensive; keep it on existing NVR by default. Vision Agent stores semantic time-series, event metadata, snapshots and optional short clips. Object storage should implement retention/lifecycle policies.

## 8. Deployment V1
One host can run logical containers:
- reverse proxy
- API/Hermes/control services
- Postgres
- Redis
- MinIO
- media gateway
- GPU vision worker
- metrics stack

Use persistent volumes and explicit backup strategy.

## 9. Scale-Out V2+
Separate control/data from GPU workers. Introduce multiple GPU nodes and camera-to-worker assignment. Only consider Kubernetes when multi-node scheduling, HA, rolling updates, and operational complexity justify it.

## 10. Observability
Monitor:
- CPU/RAM/disk/network;
- GPU utilization/temperature/VRAM;
- decode FPS;
- inference FPS/latency;
- dropped frames;
- RTSP reconnects;
- worker heartbeat;
- event queue lag;
- DB connection/latency;
- notification delivery;
- active/degraded tasks.

## 11. Backup & Recovery
Back up PostgreSQL and critical object metadata. Task definitions, rules, users, roles, configuration and audit must survive host failure according to target RPO/RTO. Redis should not be the only copy of critical state.
