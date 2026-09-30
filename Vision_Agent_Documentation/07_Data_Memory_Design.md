# Data & Memory Design

## 1. Data Classification

### Operational Truth — PostgreSQL
Authoritative and auditable.

### Realtime State — Redis
Ephemeral, cache/event transport, rebuildable.

### Evidence/Artifacts — Object Storage
Snapshots, event clips, generated reports.

### Cognitive Memory — MemoryProvider
Long-lived preferences/lessons/context; non-authoritative.

### Continuous Footage — Existing NVR
Default owner of full raw recording.

## 2. Suggested PostgreSQL Entities

- `users`
- `roles`
- `role_permissions`
- `channel_identities`
- `cameras`
- `camera_locations`
- `camera_capabilities`
- `vision_profiles`
- `workers`
- `tasks`
- `task_cameras`
- `rules`
- `observations` or time-bucketed observation tables
- `events`
- `event_evidence`
- `notifications`
- `reports`
- `tool_invocations`
- `audit_logs`
- `system_health_samples` (or external metrics store)

## 3. Observation Storage Strategy
Do not necessarily store every detection/bbox forever. V1 can persist sampled people count or time buckets plus event evidence. Retention should be configurable.

Potential tiers:
- latest state: Redis;
- recent fine-grain observations: PostgreSQL for N days;
- downsampled aggregates: longer retention;
- events/audit: longer retention per policy;
- images/clips: object storage lifecycle.

## 4. Cognitive Memory

### Suitable memories
- stable report style preference;
- confirmed camera quirk;
- validated operator correction;
- reusable task preference;
- operational lesson not represented as source-of-truth config.

### Unsuitable memories
- passwords/tokens;
- task current status;
- permission;
- raw detections/frames;
- transient counts;
- unverified guesses.

## 5. MemoryProvider Contract

```text
recall(query, context, limit)
remember(memory_candidate)
update(memory_id, patch)
forget(memory_id)
search(filters)
```

V1 can implement `SimpleMemory`; V1.5/V2 can implement `MnemosyneMemory` or another provider.

## 6. Memory Promotion

```text
Observation / conversation insight
        ↓
Candidate memory
        ↓
Durable? useful? non-secret? non-authoritative?
        ↓
Repeated / explicitly confirmed / validated?
        ↓
Long-term memory
```

## 7. Retrieval Safety
Retrieved memory is **context**, not permission and not guaranteed current truth. Hermes must query operational services before making actions that depend on current state.

## 8. Reporting Data Contract
Analytics produces structured numeric results; Hermes narrates them. This minimizes hallucinated math and keeps reports reproducible.
