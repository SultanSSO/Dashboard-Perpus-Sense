# Development Roadmap — Vision Agent

## Phase 0 — Architecture & Benchmark

**Goal:** validate assumptions before building agent complexity.

Deliverables:
- representative CCTV test set;
- benchmark shortlisted Ultralytics model sizes;
- camera JSON schema;
- task/rule/event contracts;
- database baseline;
- security/RBAC model;
- repository/container skeleton.

Exit criteria: one selected V1 model/profile and agreed initial camera capacity target.

## Phase 1 — Vision Foundation

- camera registry;
- credential reference handling;
- RTSP ingestion/reconnect;
- media gateway path;
- VisionModelAdapter;
- people detection/count;
- current observation API;
- worker health metrics.

## Phase 2 — Persistent Control Plane

- PostgreSQL schemas;
- Task Engine;
- scheduler;
- task lifecycle/recovery;
- Rule Engine;
- threshold + after-hours + camera health;
- Redis event flow;
- audit logging.

## Phase 3 — Hermes V1

- Hermes soul/system policy;
- natural language → task proposal;
- tool gateway;
- autonomy levels 0–1;
- camera resolution by metadata;
- natural confirmations/errors;
- task follow-ups.

## Phase 4 — Analytics & Reporting

- observation aggregates;
- moving baseline/simple spike;
- daily/task reports;
- open/update/resolved event lifecycle;
- non-spam notification policy.

## Phase 5 — Channels & Dashboard

- enhanced dashboard;
- bounding box visualization toggle;
- charts/task/event views;
- Telegram identity/RBAC integration;
- CLI commands;
- report views.

## V1 Release Gate

- recovery test after Hermes/control restart;
- camera disconnect test;
- GPU overload/degraded behavior test;
- authorization/prompt-injection tests;
- alert dedup/cooldown tests;
- report numeric consistency tests;
- secret leakage tests;
- representative multi-camera soak test.

## V1.5
- tracker integration;
- ROI/zones;
- virtual line entry/exit;
- event snapshots/clips;
- better statistical baseline;
- MemoryProvider richer implementation (optional Mnemosyne);
- more scheduling/policy presets.

## V2
- learned historical anomaly;
- dwell/loitering;
- resource scheduler;
- multi-GPU workers;
- advanced memory curation;
- more domain-specific detectors if justified by benchmark.

## V3
- cross-camera reasoning;
- re-identification only when privacy/business case justifies it;
- multi-site control;
- advanced planning/workflows;
- predictive analytics;
- high-availability/distributed control plane as needed.

## Principle for Every Upgrade
New versions should prefer adding:

```text
Capability → Observation/Event → Tool → Hermes understanding
```

rather than bypassing existing boundaries.
