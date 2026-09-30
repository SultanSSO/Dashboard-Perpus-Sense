# Vision Agent — Documentation Pack

**Status:** Initial Concept / Architecture Baseline
**Date:** 2026-09-10
**Primary Agent:** Hermes
**Primary Vision Strategy:** Official pretrained Ultralytics models; no fine-tuning required for V1

## Purpose

Folder ini adalah paket dokumentasi awal untuk mengembangkan **Vision Agent**: platform CCTV + computer vision + persistent task + event/anomaly detection + reporting yang diorkestrasi oleh agent pusat bernama **Hermes**.

Prinsip utamanya adalah menjaga kompleksitas konsep dari V1 sampai versi lanjutan, tetapi mengimplementasikan kemampuan secara bertahap. Dengan demikian, V1 dapat tetap realistis untuk dibangun tanpa mengunci arsitektur pada fitur sederhana saja.

## Core Principles

1. **Powerful reasoning, narrow authority.** Hermes boleh memiliki reasoning yang kuat, tetapi hanya dapat bertindak melalui tool dan scope yang telah diotorisasi.
2. **Hermes does not own system state. Hermes reasons over system state.** PostgreSQL dan service deterministik adalah sumber kebenaran operasional.
3. **Vision perceives; Hermes understands and orchestrates.** Model Ultralytics tidak dibebani task management atau reasoning.
4. **Persistent tasks live outside the LLM.** Task Engine/Scheduler tetap berjalan walaupun Hermes restart.
5. **Event-driven, not frame-driven.** Hermes menerima observation, event, summary, dan system health — bukan semua video frame.
6. **Operational truth is separate from cognitive memory.** Memory agent tidak boleh menggantikan database operasional.
7. **Security is enforced in code, not prompt.** Soul/prompt membentuk perilaku; Policy/RBAC/Tool Gate membatasi tindakan.
8. **V1 simple in capability, extensible in architecture.** Tracking, line crossing, learned anomaly, dan cross-camera reasoning dapat ditambahkan tanpa redesign besar.

## Document Index

| File | Purpose |
|---|---|
| `01_Rangkuman_Diskusi_Vision_Agent.docx` | Dokumen Word lengkap yang merangkum seluruh diskusi dan keputusan desain |
| `01_Rangkuman_Diskusi_Vision_Agent.md` | Versi Markdown dari rangkuman lengkap |
| `02_Blueprint_Vision_Agent.md` | Blueprint platform dan hubungan antarkomponen |
| `03_PRD_Vision_Agent.md` | PRD yang telah diperluas berdasarkan diskusi |
| `04_Architecture_Design.md` | Software/system architecture dan service boundaries |
| `05_Hermes_Agent_Spec.md` | Soul, autonomy, scope, behavior, reporting, dan tool policy Hermes |
| `06_Task_Rule_Event_Spec.md` | Spesifikasi persistent task, rule, event, anomaly, lifecycle |
| `07_Data_Memory_Design.md` | Database, analytics history, agent memory, retention |
| `08_Security_Design.md` | Security model, RBAC, secrets, network isolation, audit |
| `09_Infrastructure_Hardware_Deployment.md` | Hardware, GPU/RAM/storage/network dan deployment V1→scale-out |
| `10_API_Tool_Contracts.md` | Kontrak tools/API yang dapat digunakan Hermes |
| `11_Roadmap_Development.md` | Roadmap implementasi V1, V1.5, V2, V3 |
| `12_Config_Schemas.md` | Contoh schema konfigurasi camera, vision profile, task, rule, event |
| `13_Hermes_CCTV_Instructions.md` | Instruksi operasional Hermes untuk MCP CCTV berbasis snapshot berkala |

## Recommended Reading Order

Untuk engineering kickoff: `02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 12 → 11`.

Untuk stakeholder/product discussion: `01 → 02 → 03 → 11`.
