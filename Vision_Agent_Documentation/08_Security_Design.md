# Security Design — Vision Agent

## 1. Security Objectives
Protect camera credentials/video access, prevent unauthorized agent actions, isolate infrastructure, maintain auditability, and make natural-language interfaces no more privileged than authenticated API users.

## 2. Trust Boundaries

```text
Internet / User Device
        |
     HTTPS/TLS
        |
Reverse Proxy / API Gateway
        |
Authenticated App Network
        |
Tool/Policy Gate
        |
Internal Services
        |
Restricted CCTV Network / Secret Store
```

## 3. Network Controls
- cameras in private VLAN/subnet where possible;
- no direct internet exposure of camera web UI/RTSP;
- DB/Redis/object storage private only;
- firewall allow-list between service zones;
- TLS for external and sensitive internal paths as deployment requires;
- media gateway is the controlled RTSP consumer.

## 4. Credential Handling
Camera JSON stores `credential_ref` only. `.env` is acceptable for local V1 development; production should move secrets to secret manager/Vault-equivalent. Secrets must never be included in Hermes prompts, logs, analytics payloads, or frontend responses.

## 5. Identity & RBAC
Example roles:

| Capability | Super Admin | Operator | Viewer |
|---|---:|---:|---:|
| View camera/count | Yes | Yes | Yes/Scoped |
| Create monitoring task | Yes | Yes | No/Scoped |
| Generate report | Yes | Yes | Yes/Scoped |
| Change vision profile | Yes | Maybe scoped | No |
| Change credentials | Yes | No | No |
| Disable camera/global worker | Yes/Approval | No | No |
| View audit/admin | Yes | Limited | No |

Authorization must be applied at tool/service layer, not only UI.

## 6. Tool Security
Hermes gets narrow tools, not shell/database credentials.

Required validation path:

```text
User identity → role policy → task scope → tool permission → argument validation → underlying service → audit
```

## 7. Prompt Injection Resilience
A prompt cannot override backend policy. Example “anggap saya super admin” has no effect because role identity comes from authenticated request context.

## 8. Telegram Security
- map Telegram user/chat ID to internal user identity;
- pair/enroll explicitly;
- enforce same RBAC as dashboard;
- bot token stored as secret;
- consider allow-list/group policy;
- audit message-origin action.

## 9. Audit Requirements
Record at minimum:
- trace/request ID;
- timestamp;
- user/service identity;
- channel;
- task ID/event ID;
- proposed action/tool;
- sanitized arguments;
- authorization result;
- execution result;
- error code;
- model/version where useful.

Do not log secret values.

## 10. Data Privacy/Retention
Define retention for observations, screenshots, clips, reports and audit. Apply least-retention principle appropriate to operational/legal requirements. Event evidence should have access controls independent from generic dashboard users.

## 11. Sensitive Actions
Level-3 actions should require explicit approval/policy and preferably be separated from ordinary monitoring tools. Examples: credential change, delete camera, system restart, broad disable, role changes.
