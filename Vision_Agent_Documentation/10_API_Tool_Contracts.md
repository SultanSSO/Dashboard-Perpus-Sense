# Hermes Tool & API Contracts

## 1. Design Rule
Hermes interacts with the platform only through **typed, narrow, authorization-aware tools**. Tools are capabilities, not generic command execution.

## 2. Common Request Context
Every mutating call should receive server-attached context:

```json
{
  "request_id": "REQ-...",
  "user_id": "USER-...",
  "role": "operator",
  "channel": "telegram",
  "task_id": "TASK-..."
}
```

Hermes must not be trusted to invent these identity fields; gateway/runtime attaches them.

## 3. Camera Tools

### `camera.list`
Filters by location/status/capability.

### `camera.get_metadata`
Returns sanitized metadata, no secrets.

### `camera.get_status`
Returns health, last_seen, stream/inference state.

### `camera.snapshot`
Returns evidence reference; policy may restrict.

## 4. Vision Tools

### `vision.get_current_observation`
Returns current people count and quality metadata.

### `vision.get_profile`
Read profile.

### `vision.set_profile`
Restricted mutation; requires task/user policy.

### `vision.start_processing` / `vision.stop_processing`
Administrative/controlled; not default autonomy.

## 5. Task Tools

### `task.create`
Input: structured task spec. Must validate camera scope, schedule, rules and allowed actions.

### `task.get`
Authoritative state.

### `task.list`
Filter active/history.

### `task.pause/resume/cancel`
Authorization and owner/role checks.

## 6. Analytics Tools

### `analytics.current_count(camera_id)`

### `analytics.summary(camera_ids, start, end)`
Returns deterministic aggregates.

### `analytics.events(filters)`
Returns structured events.

### `analytics.history(...)`
Downsampled series by requested interval.

## 7. Report Tools

### `report.generate`
Input task/date-range/template/channel. Returns structured report and optional artifact reference.

## 8. Notification Tools

### `notification.send`
Should normally be called by workflow/event logic rather than unrestricted free-form user targets. Channel destinations are policy-resolved.

## 9. Memory Tools

### `memory.recall`
Contextual only.

### `memory.propose`
Creates candidate memory subject to memory-write policy.

Avoid unrestricted raw `remember(anything)` in production.

## 10. Tool Result Envelope

```json
{
  "ok": true,
  "request_id": "REQ-...",
  "data": {},
  "error": null,
  "audit_id": "AUD-..."
}
```

On denial:

```json
{
  "ok": false,
  "error": {
    "code": "ACTION_DENIED",
    "reason": "outside_task_scope"
  }
}
```

## 11. Tool Safety Properties
- idempotency key for appropriate operations;
- schema validation;
- no raw SQL/tool shell;
- no raw secrets in result;
- bounded query ranges;
- authorization at service boundary;
- complete audit trail.
