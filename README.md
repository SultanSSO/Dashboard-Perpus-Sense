# Vision Agent CCTV

Platform lokal untuk observasi CCTV berbasis computer vision, people counting, structured events, task/rule engine, dashboard, dan integrasi MCP untuk Hermes.

Status: prototype engineering / local pilot. Belum production-ready dan belum menyediakan bukti live CCTV berkelanjutan.

## Status

- Implementasi awal: occupancy, people counting, flow crossing.
- Mode identitas: anonymous.
- Face recognition: tidak digunakan.
- Output: `outputs/events.jsonl` dan `outputs/annotated.mp4`.
- URL dashboard `https://dts-lab.web.id/cctv-live/cctv-wall.html` belum dipakai sebagai input karena hanya halaman wall dan saat diuji mengembalikan `401 Authorization Required`.

## Jalankan dari VS Code

1. Buka folder ini di VS Code.
2. Buat virtual environment:

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Salin `.env.example` menjadi `.env`.
4. Isi `STREAM_URL` dengan endpoint stream asli dari pengelola CCTV. Gunakan akun read-only, bukan credential admin utama.
5. Jalankan smoke test 30 frame tanpa window:

```bash
python vision_cctv.py --max-frames 30 --no-window
```

6. Jalankan live preview:

```bash
python vision_cctv.py
```

Tekan `q` atau `Esc` untuk berhenti.

## Input yang didukung

- RTSP: `rtsp://USER:PASSWORD@HOST:554/PATH`
- HLS: `https://HOST/PATH/stream.m3u8`
- MJPEG: URL stream MJPEG
- Webcam: `0`
- File video: `C:\\path\\video.mp4`

Jika RTSP tidak terbuka, periksa VPN, firewall, port, codec, izin stream, dan apakah NVR/VMS mengizinkan koneksi read-only.

## Zona dan flow line

Contoh `.env`:

```text
ZONE_POLYGON=100,100;900,100;900,650;100,650
FLOW_LINE=500,100;500,650
```

Koordinat mengikuti resolusi frame asli. Audit kamera perlu dilakukan sebelum menetapkan polygon/line produksi.

## Output event

`outputs/events.jsonl` memakai schema `vision.event.v1`. Dashboard API
membaca event store ini secara read-only dan menyediakan observation aktual
untuk dashboard web; Hermes tetap mengakses domain yang sama melalui MCP.

## Detector dengan pilihan model dan task

File terpisah agar `vision_cctv.py` lama tetap aman:

```text
vision_cctv_modes.py
```

Jalankan menu interaktif:

```powershell
.\.venv\Scripts\python.exe vision_cctv_modes.py
```

Program menampilkan pilihan model `.pt`, lalu task:

```text
a. Deteksi orang
b. Deteksi kursi
c. Deteksi orang dan kursi
d. Deteksi kepadatan
```

Mode command-line tanpa menu:

```powershell
.\.venv\Scripts\python.exe vision_cctv_modes.py --model yolo11n.pt --mode a --no-window --max-frames 30
.\.venv\Scripts\python.exe vision_cctv_modes.py --model yolo11n.pt --mode b --no-window --max-frames 30
.\.venv\Scripts\python.exe vision_cctv_modes.py --model yolo11n.pt --mode c --no-window --max-frames 30
.\.venv\Scripts\python.exe vision_cctv_modes.py --model yolo11n.pt --mode d --capacity 20 --no-window --max-frames 30
```

Mode `d` memakai rasio orang terhadap `--capacity`:

```text
<50%   low
50-79% medium
80-99% high
>=100% critical
```

Output tersimpan di `outputs/modes/<mode>/`. Mode kursi kosong lama tetap tersedia sebagai `--mode empty-chair`.

Catatan: deteksi kursi kosong memakai jarak titik tengah bbox kursi dan orang. Ini heuristik; validasi kamera dan ground truth tetap perlu.

## Dashboard live video RTSP

Versi video live memakai RTSP/HLS/MJPEG dan latest-frame policy. Frame lama dibuang agar dashboard tidak tertinggal saat YOLO lebih lambat daripada kamera.

Isi `.env` dengan endpoint RTSP resmi:

```text
RTSP_URL=rtsp://USERNAME:PASSWORD@HOST:554/STREAM_PATH
RTSP_CAMERAS=
CAMERA_ID=library-camera
```

Multi-camera:

```text
RTSP_CAMERAS=dvr01_ch01=rtsp://HOST/stream1,dvr01_ch02=rtsp://HOST/stream2
```

Jalankan:

```bash
.venv\\Scripts\\python.exe -m streamlit run dashboard_video.py
```

Buka:

```text
http://localhost:8501
```

RTSP tidak bisa ditebak dari URL snapshot. Minta endpoint RTSP dari admin CCTV. Dashboard tidak merekam raw video.

## Dashboard CCTV

Jalankan dashboard wall melalui VS Code terminal:

```bash
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -m streamlit run dashboard.py
```

Buka URL yang ditampilkan Streamlit, biasanya:

```text
http://localhost:8501
```

Dashboard mengambil snapshot terautentikasi, menjalankan YOLO untuk `person` dan `chair`, lalu menampilkan frame anotasi. Pilih kamera dari sidebar. Default menampilkan 6 kamera pertama; tombol `Pilih semua kamera` tersedia, tetapi pemrosesan banyak kamera lebih lambat.

Parameter sidebar:

- Model.
- Confidence.
- Image size.
- Jumlah kolom.
- Kamera.
- Interval auto-refresh.

Untuk menjalankan melalui debugger VS Code, buka `Run and Debug` lalu pilih `Vision Agent CCTV Dashboard`.

## Dashboard terintegrasi Vision Agent

Dashboard utama menggunakan server yang menyajikan frontend static dan
Dashboard API dari `CCTVService`:

```powershell
& ".\venv\Scripts\python.exe" `
  -m vision_agent.dashboard.server `
  --host 127.0.0.1 `
  --port 4173
```

Buka:

```text
http://127.0.0.1:4173/desain-awal-dashboard/login.html
```

Endpoint utama:

```text
GET /api/v1/health
GET /api/v1/overview
GET /api/v1/cameras?analysis_only=true
GET /api/v1/events?limit=200
GET /api/v1/cameras/{camera_id}/observation
GET /api/v1/cameras/{camera_id}/snapshot
```

Live Monitoring melakukan polling observation dan snapshot setiap 5 detik.
Panel kamera aktif menampilkan waktu update terakhir serta usia observation
dibandingkan waktu browser saat ini.

UI membaca event dan observation aktual. Nilai occupancy hanya ditampilkan
jika `occupancy_rate` tersedia; dashboard tidak mengarang persentase dari
jumlah orang.

Catatan: dashboard masih memakai snapshot JPEG. Tampilan bukan video kontinu. RTSP/HLS diperlukan untuk video mulus.

## Konfigurasi model Hermes

Model LLM/VLM Hermes dapat diarahkan ke provider atau endpoint OpenAI-compatible melalui `.env` lokal. Template tersedia di `.env.example`:

```text
HERMES_MODEL_PROVIDER=custom
HERMES_MODEL_NAME=your-model-id
HERMES_MODEL_BASE_URL=https://api.example.com/v1
HERMES_MODEL_API_KEY=
HERMES_MODEL_API_KEY_ENV=HERMES_MODEL_API_KEY
HERMES_MODEL_CONTEXT_LENGTH=
HERMES_MODEL_TEMPERATURE=
HERMES_MODEL_ENABLE_VISION=false
HERMES_MODEL_FALLBACKS=
```

Variabel ini menjadi konfigurasi proyek dan tidak otomatis mengubah profile Hermes. Terapkan nilainya ke profile Hermes aktif menggunakan CLI, bukan dengan mengedit `config.yaml` secara manual:

```powershell
hermes config set model.provider custom
hermes config set model.default your-model-id
hermes config set model.base_url https://api.example.com/v1
hermes config set model.api_key "${HERMES_MODEL_API_KEY}"
```

Untuk endpoint custom, verifikasi `GET /v1/models` dan gunakan `id` model yang benar-benar dikembalikan endpoint. API key tetap di environment/secret manager. Jangan menaruh key asli di `.env.example`, dokumentasi, Git, atau chat. Jika endpoint bukan OpenAI-compatible, diperlukan adapter/provider Hermes khusus; variabel ini saja tidak mengubah protokol.

## MCP CCTV server

`mcp_cctv_server.py` menyediakan tool MCP typed untuk Hermes. Server membaca
metadata kamera dari `config/camera_catalog.json`, structured event dari
`outputs/events.jsonl`, dan registry task lokal yang diaudit. Credential CCTV,
template URL, shell, dan raw SQL tidak pernah diekspos ke MCP client.

Install dependency:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Jalankan Inspector untuk pengujian lokal:

```powershell
.\venv\Scripts\mcp.exe dev mcp_cctv_server.py
```

Tool read-only:

- `service.health`
- `agent.settings.get`
- `camera.list`
- `camera.get_metadata`
- `camera.get_status`
- `vision.get_current_observation`
- `analytics.events`
- `analytics.summary`
- `task.list`
- `task.get`

Tool mutation (`agent.settings.configure`, `task.create`, `task.configure`,
`task.transition`) memerlukan intent user yang eksplisit dan
`MCP_ENABLE_MUTATIONS=true`. Set actor khusus agar setiap perubahan dapat
ditelusuri di audit:

```text
MCP_ENABLE_MUTATIONS=true
MCP_ACTOR_ID=hermes-agent
```

Profil Hermes lokal tersedia sebagai `vision-agent`. Jalankan dari workspace
proyek:

```powershell
hermes --profile vision-agent --in "C:\path\to\agentic-ai-vision"
```

Jalankan Streamable HTTP setelah reverse proxy dan auth gateway siap:

```powershell
.\venv\Scripts\mcp.exe run mcp_cctv_server.py --transport streamable-http
```

Observation live belum otomatis tersedia hanya karena MCP aktif. `video_worker.py`
tetap harus menjalankan inference dan mendaftarkan latest observation ke state
store/event bus. Sampai integrasi itu dibuat, `vision_get_current_observation`
akan mengembalikan `available=false` bila tidak ada event dengan
`source.camera_id` yang cocok.

## Perbandingan model

Bandingkan model pada satu snapshot kamera yang sama:

```bash
.venv\\Scripts\\python.exe compare_models.py
```

Output:

```text
outputs/model-comparison/results.json
outputs/model-comparison/yolo11n.jpg
```

Model default:

```text
yolo11n.pt, yolov8n.pt, yolov10n.pt, yolov9t.pt, dfine-n.pt, dfine-s.pt, rtdetr-l.pt
```

Batasi model yang diuji melalui `.env`:

```text
COMPARE_MODELS=yolo11n.pt,yolov8n.pt,dfine-n.pt,dfine-s.pt
```

Parameter sama untuk semua model: `CONFIDENCE`, `IOU`, `IMG_SIZE`, `DEVICE`. Hasil belum merupakan evaluasi akurasi karena belum memakai ground truth. Bandingkan `person_count`, `chair_count`, `inference_seconds`, dan `fps_estimate`.

Model gagal download/load dicatat di `results.json`; model lain tetap diuji.

## Batasan penting

- Counting bergantung pada sudut kamera, occlusion, cahaya, resolusi, dan kualitas model.
- Flow memakai ID ByteTrack dan bersifat perkiraan; ID dapat berubah setelah occlusion.
- Output tanpa ground truth adalah inference deployment, bukan klaim precision/recall/mAP.
- Jangan mengaktifkan face recognition tanpa persetujuan kebijakan, legal review, DPIA, dan kontrol biometrik.
- Jangan commit `.env`, password, rekaman, atau output CCTV ke Git.

## Struktur

```text
config/                    # catalog kamera, source CCTV, profil Vision Agent
vision_agent/
  cv/                      # worker dan logic computer vision internal
  mcp/                     # domain service MCP CCTV internal
  dashboard/               # Dashboard API dan static UI server
desain-awal-dashboard/     # frontend dashboard static
Vision_Agent_Documentation/ # PRD, arsitektur, kontrak, dan roadmap
tests/                     # pengujian behavior dan security boundary
outputs/                   # event, artifact, task registry, dan audit runtime

vision_cctv.py             # entrypoint pipeline CCTV lama
vision_cctv_modes.py       # wrapper entrypoint mode analisis
person_counter.py          # wrapper entrypoint penghitung orang
video_worker.py            # wrapper import LatestFrameWorker
mcp_cctv_server.py         # entrypoint MCP CCTV
compare_models.py          # entrypoint benchmark model
```

Entry point root dipertahankan sebagai wrapper kompatibilitas. Implementasi
internal berada di package `vision_agent/` sehingga import lama dan perintah
lama tetap dapat digunakan.

## Deteksi dan hitung orang dengan RT-DETR

File khusus:

```text
person_counter.py
```

Hitung orang yang terlihat pada setiap frame. Tidak menghitung orang unik sepanjang waktu. Tidak memakai face recognition.

Uji video tanpa window:

```bash
.venv\\Scripts\\python.exe person_counter.py --source "E:\\path\\video.mp4" --no-window --max-frames 30
```

Uji webcam:

```bash
.venv\\Scripts\\python.exe person_counter.py --source 0
```

Device otomatis: GPU CUDA jika tersedia, CPU jika tidak tersedia.

Konfigurasi source native CCTV di `.env`:

```text
CCTV_HOST=CAMERA_HOST
CCTV_CHANNEL=13
CCTV_USERNAME=USERNAME
CCTV_PASSWORD=PASSWORD
PERSON_SOURCE=
DEVICE=auto
```

Program membangun RTSP sub-stream Hikvision:

```text
rtsp://USERNAME:PASSWORD@CAMERA_HOST:554/Streaming/Channels/1302
```

Jalankan uji RTSP native secara eksplisit:

```bash
.venv\\Scripts\\python.exe person_counter.py --rtsp --device auto --no-window --max-frames 30
```

`--rtsp` mengabaikan `SNAPSHOT_URL` dan memaksa sumber RTSP yang dibangun dari `CCTV_HOST`, `CCTV_CHANNEL`, `CCTV_USERNAME`, dan `CCTV_PASSWORD`. Alternatif permanen: set `CCTV_USE_RTSP=true` di `.env`.

Override source langsung jika perlu:

```bash
.venv\\Scripts\\python.exe person_counter.py --source "rtsp://USERNAME:PASSWORD@IP:554/Streaming/Channels/1302" --device auto --no-window --max-frames 30
```

`SNAPSHOT_URL` tidak dipakai saat native RTSP berhasil dikonfigurasi.

Gunakan RT-DETR-L dengan parameter berbeda:

```bash
.venv\\Scripts\\python.exe person_counter.py --source "E:\\path\\video.mp4" --model rtdetr-l.pt --conf 0.35 --imgsz 960
```

Output:

```text
outputs/person-counter/people_annotated.mp4
outputs/person-counter/people_counts.jsonl
outputs/person-counter/summary.json
```

`summary.json` berisi peak count, rata-rata count, FPS pemrosesan, parameter, dan status `ground_truth: false`.

## Next step

Ambil satu endpoint RTSP/HLS resmi dari pengelola CCTV, lalu uji:

```bash
ffplay "STREAM_URL"
```

Jika stream tampil, masukkan URL sama ke `.env` dan jalankan smoke test.

**Catatan keamanan:** kredensial stream dikirim hanya melalui `.env` lokal. Jangan menuliskannya di chat, source code, atau commit.

**Sumber dashboard CCTV:** https://dts-lab.web.id/cctv-live/cctv-wall.html

**Status akses dashboard saat pengecekan:** `401 Authorization Required`.

**Tanggal:** 31 Agustus 2026

---

## Catatan integrasi Windows/VS Code

Gunakan Python interpreter `.venv\\Scripts\\python.exe` melalui `Ctrl+Shift+P` → `Python: Select Interpreter`. Jika GPU NVIDIA tersedia, ubah `DEVICE=0` setelah `torch.cuda.is_available()` terverifikasi; default aman adalah CPU.

Jalankan dengan path project:

```bash
cd "C:\\path\\to\\agentic-ai-vision"
code .
```

`code .` membuka folder project di VS Code jika command `code` sudah masuk PATH.

## Lisensi/model

Periksa lisensi Ultralytics dan model yang digunakan sebelum deployment institusional atau komersial.

## Future API contract

Event minimal yang perlu dipertahankan saat migrasi ke dashboard utama:

- `schema_version`
- `event_id`
- `event_type`
- `observed_at`
- `source.camera_id` atau stream identifier terkontrol
- `source.zone_id`
- `measurement`
- `confidence`
- `quality`
- `privacy`
- `model.name` dan `model.version`
- `evidence_ref` bila evidence diizinkan
- `correlation_id` untuk orkestrasi lintas-agent

Jangan kirim raw video ke agent utama secara terus-menerus. Kirim metadata terstruktur dan evidence terbatas sesuai izin.

## Troubleshooting

- `Stream gagal dibuka`: endpoint bukan stream, URL salah, 401/403, VPN/firewall, atau codec tidak cocok.
- `Frame gagal dibaca`: koneksi putus, NVR membatasi sesi, atau stream tidak kompatibel.
- `CUDA tidak dipakai`: ubah `DEVICE=0` hanya setelah instalasi PyTorch CUDA dan driver terverifikasi.
- `Tidak ada crossing`: line belum tepat, track ID belum tersedia, atau video tidak melintasi garis.
- `Window tidak muncul`: jalankan tanpa `--no-window`; pastikan VS Code berjalan pada desktop Windows.

Jangan menyimpulkan model gagal sebelum membandingkan frame tetap, stream health, dan kualitas kamera.

## Fase berikutnya

1. Tambah `camera_id`, `site_id`, dan `zone_id` dari registry resmi.
2. Tambah queue ROI dan dwell time setelah definisi operasional disetujui.
3. Tambah event rules dengan operator verification.
4. Tambah API gateway/event bus.
5. Tambah monitoring model, drift, latency, dan audit.
6. Validasi akurasi memakai ground truth lokal.
7. Lakukan privacy/security review sebelum pilot operasional.

Jangan memakai data ini sebagai sistem keamanan operasional sebelum semua gate selesai.

## API integration placeholder

Contoh future payload HTTP setelah gateway siap:

```python
# Jangan aktifkan sebelum endpoint, authentication, retry policy, dan data contract disetujui.
# requests.post(VISION_AGENT_URL, json=event, timeout=5)
```

## Development notes

Output JSONL tetap menjadi event store lokal yang dibaca read-only oleh Dashboard API dan MCP service. Ini menjaga auditability tanpa mengirim credential atau frame mentah ke dashboard/Hermes.

## Verification

```bash
python -m py_compile vision_cctv.py
```

Smoke test live memerlukan endpoint stream resmi. URL dashboard publik belum memenuhi syarat tersebut.

## Ownership

Pemilik use case, data, akses CCTV, kebijakan retensi, dan persetujuan pilot harus ditetapkan oleh UGM sebelum deployment.

## Change log

- 2026-08-31: pipeline awal YOLO/OpenCV ditambahkan.
- 2026-08-31: anonymous-first dan structured event output ditetapkan.
- 2026-08-31: dashboard CCTV diuji, akses `401`.

## End

File ini menjadi panduan kerja awal untuk Vision Agent CCTV.
