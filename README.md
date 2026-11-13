# PerpusSense — Dashboard Okupansi Perpustakaan

Build **dashboard-only** dari platform Vision Agent CCTV. Repositori ini hanya
berisi framework dashboard: server API + frontend statis + data demo. Mesin
deteksi (YOLO/OpenCV/torch), worker kamera, task engine, dan MCP server
dijalankan sebagai layanan terpisah dan sudah dihapus dari sini.

Dashboard tetap berjalan penuh tanpa mesin deteksi: ia membaca event store
(`outputs/events.jsonl`) dan snapshot JPEG, lalu menampilkannya sebagai
okupansi, riwayat, alert, dan status runtime.

## Status

- Build: dashboard-only, tanpa inference.
- Data: event demo dari `scripts/seed_demo_events.py` (bukan kamera asli).
- Snapshot: JPEG placeholder dari `scripts/seed_demo_snapshots.py`.
- Autentikasi: sisi klien, statis (demo `admin` / `admin123`). Belum JWT.
- Belum production-ready.

## Kebutuhan

- Python 3.10+ (diuji pada 3.14)
- Tanpa GPU, torch, atau OpenCV

## Instalasi

```bash
cd perpus_occupancy
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

`.env` hanya berisi path data dan kebijakan mutasi. Tidak ada credential kamera
di build ini.

## Menjalankan dashboard

Cara utama (v2):

```bash
dashboard-perpus-v2
```

Perintah itu menjalankan `.venv/bin/dashboard-perpus-v2`, yang meneruskan ke
`scripts/dashboard_v2_cli.py`. Opsi yang tersedia:

```bash
dashboard-perpus-v2 --port 8080        # port lain
dashboard-perpus-v2 --host 0.0.0.0     # akses dari perangkat lain di LAN
```

Bila `~/.local/bin` belum ada di PATH, panggil langsung:

```bash
.venv/bin/dashboard-perpus-v2
```

Cara lama masih berlaku:

```bash
.venv/bin/python -m vision_agent.dashboard.server --host 127.0.0.1 --port 4173
```

Arah desain dan alasan setiap keputusan visual ada di `DESIGN.md`. Rencana
perubahan v2 ada di `prd.md`.

Buka:

```text
http://127.0.0.1:4173/desain-awal-dashboard/login.html
```

| Halaman | Path |
|---|---|
| Login | `/desain-awal-dashboard/login.html` |
| Dashboard okupansi | `/desain-awal-dashboard/index.html` |
| Live Monitoring | `/desain-awal-dashboard/live.html` |
| Riwayat & Analitik | `/desain-awal-dashboard/analytics.html` |
| Pengaturan | `/desain-awal-dashboard/settings.html` |

## Data demo

Event store kosong pada build ini, jadi dashboard menampilkan "Belum tersedia"
sampai event diisi. Dua skrip berikut menyediakan data contoh:

```bash
# event untuk semua kamera di config/camera_catalog.json
.venv/bin/python scripts/seed_demo_events.py

# event baru tiap 15 detik (jalankan di terminal terpisah)
.venv/bin/python scripts/seed_demo_events.py --count 2 --interval 15 --watch

# snapshot JPEG placeholder untuk panel Live Monitoring
.venv/bin/python scripts/seed_demo_snapshots.py

# bersihkan event demo
.venv/bin/python scripts/seed_demo_events.py --reset
```

Observation ditandai **stale** bila lebih tua dari ambang di
`config/vision_agent.json`. Dashboard tidak menghitung observation stale sebagai
kondisi saat ini — itu perilaku yang benar, bukan bug.

## API

Server menyajikan frontend statis dan Dashboard API dari `CCTVService`.

```text
GET  /api/v1/health
GET  /api/v1/overview
GET  /api/v1/cameras?analysis_only=true
GET  /api/v1/cameras/{camera_id}/observation
GET  /api/v1/cameras/{camera_id}/status
GET  /api/v1/cameras/{camera_id}/metadata
GET  /api/v1/cameras/{camera_id}/snapshot
GET  /api/v1/events?limit=200
GET  /api/v1/summary?camera_ids=...
GET  /api/v1/tasks
GET  /api/v1/agent/settings
GET  /api/v1/runtime/status
```

Endpoint mutasi hanya menerima request dari localhost dan hanya aktif bila
`MCP_ENABLE_MUTATIONS=true`:

```text
POST /api/v1/agent/settings
POST /api/v1/runtime/start | stop | restart
POST /api/v1/runtime/{camera_id}/start | stop | restart
POST /api/v1/tasks/{task_id}/settings
```

Pada build ini `POST /api/v1/runtime/*` menjawab `ENGINE_UNAVAILABLE` karena
`vision_cctv.py` tidak ada. Panel runtime di halaman Pengaturan tetap tampil dan
melaporkan `engine_available: false`.

## Konfigurasi

| File | Isi |
|---|---|
| `.env` | Path data, actor audit, izin mutasi |
| `config/camera_catalog.json` | Daftar kamera (id, device, lokasi, status) |
| `config/vision_agent.json` | Profil analisis, ambang stale, zona |
| `desain-awal-dashboard/assets/js/cctv-data.js` | Katalog kamera untuk halaman Live |

`config/*.json` dan `cctv-data.js` bersifat lokal (lihat `.gitignore`); versi
contohnya berakhiran `.example.json`.

## Struktur

```text
config/                      # katalog kamera, profil vision agent
vision_agent/
  mcp/service.py             # domain service: event store, observation, audit
  dashboard/server.py        # HTTP server: static UI + Dashboard API
  runtime_manager.py         # lifecycle worker (no-op tanpa mesin deteksi)
desain-awal-dashboard/       # frontend statis (HTML/CSS/JS)
scripts/                     # seed event & snapshot demo
tests/                       # pengujian service dan runtime manager
outputs/                     # event store, snapshot, log runtime
cctv_mcp_service.py          # alias import kompatibel
```

## Pengujian

```bash
.venv/bin/python -m pytest tests -q
```

## Yang tidak termasuk

Dihapus dari repositori ini karena berjalan sebagai layanan terpisah:

- `vision_cctv.py`, `vision_cctv_modes.py`, `person_counter.py`, `video_worker.py`
- `vision_agent/cv/` (person counter, video worker, mode analisis)
- `vision_agent/task_engine.py`
- `mcp_cctv_server.py`, `compare_models.py`, `models.json`
- Dependensi torch, ultralytics, opencv, streamlit

Dashboard tidak mengirim frame mentah ke mana pun. Bila mesin deteksi dipasang
kembali, letakkan worker di repositori terpisah dan arahkan ia menulis event
`vision.event.v1` ke `outputs/events.jsonl` yang sama.

## Keamanan

Lihat `SECURITY.md`. Jangan commit `.env`, credential kamera, snapshot asli,
atau output runtime.
