# Kajian Pembangunan Agentic AI Vision
## Integrasi Awal dengan CCTV untuk Ekosistem UGM Agent

**Status:** Draf kajian awal untuk pembahasan strategis dan teknis
**Versi:** 1.0
**Tanggal:** 31 Agustus 2026
**Lokasi pilot:** Perpustakaan — cakupan kamera belum dipetakan

> Dokumen ini merupakan kajian konseptual dan rancangan pilot. Angka biaya, akurasi, kapasitas, dan durasi yang belum dikonfirmasi lapangan ditulis sebagai estimasi atau asumsi, bukan fakta.

---

## Ringkasan Eksekutif

UGM Agent memerlukan kemampuan memahami lingkungan fisik kampus, bukan hanya teks, dokumen, dan data administrasi. **Vision Agent** diusulkan sebagai sub-agent yang menerima sinyal visual dari CCTV, mengubahnya menjadi metadata serta peristiwa terstruktur, lalu menghasilkan insight yang dapat dikonsumsi dashboard AI Agent utama.

CCTV perpustakaan telah tersedia dan tim penyusun memiliki akses administrator. Namun, inventaris kamera, akses stream, kualitas visual, topologi jaringan, serta kesiapan NVR/VMS belum dipetakan. Karena itu, audit teknis dan tata kelola menjadi tahap nol sebelum pemilihan model serta perangkat.

Rekomendasi utama:

1. Mulai dari analitik anonim: occupancy, people counting, flow, dan zone utilization.
2. Bangun Vision Agent sebagai layanan mandiri dengan API, event schema, dan audit trail yang netral terhadap platform dashboard utama.
3. Bandingkan on-premise, edge, cloud, dan hybrid; rekomendasi awal adalah **hybrid dengan inferensi sedekat mungkin ke sumber video**.
4. Tunda face recognition dan identifikasi individu sampai ada dasar tujuan yang jelas, persetujuan kebijakan, penilaian dampak perlindungan data, serta pengamanan biometrik.
5. Kembangkan bertahap: baseline → analitik dasar → queue → event detection → reasoning lintas-agent.
6. Ukur bukan hanya akurasi model, tetapi manfaat operasional, kesiapan integrasi, keamanan, privasi, dan biaya per kamera.

Vision Agent tidak boleh diposisikan sebagai sistem pengawasan tanpa batas. Nilai utamanya adalah menyediakan observasi ruang yang terukur untuk keputusan fasilitas, pelayanan, keselamatan, dan efisiensi energi, dengan human oversight pada keputusan berisiko tinggi.

---

## 1. Latar Belakang

Kampus memiliki ruang fisik dengan dinamika tinggi: perpustakaan, ruang kuliah, laboratorium, layanan mahasiswa, koridor, parkir, dan ruang publik. Informasi pemanfaatan ruang sering dikumpulkan melalui observasi manual, laporan periodik, atau asumsi. CCTV yang telah tersedia dapat menjadi sumber data operasional jika diproses secara proporsional dan aman.

Computer vision modern mampu melakukan deteksi objek, pelacakan, counting, pemetaan zona, dan analisis peristiwa. Akan tetapi, deteksi objek saja belum menjadi kecerdasan agentik. Agent perlu menerima data terstruktur, memahami konteks, memakai tool, menghubungkan observasi dengan tujuan operasional, menjelaskan dasar insight, dan menyerahkan tindakan tertentu kepada manusia.

Dalam ekosistem UGM Agent, Vision Agent berperan sebagai sumber observasi multimodal. Agent lain dapat menyediakan konteks jadwal, kapasitas ruang, kalender akademik, data fasilitas, cuaca, atau laporan layanan. Dashboard AI Agent utama kelak mengorkestrasi hasil tersebut.

### 1.1 Fakta awal yang tersedia

- CCTV perpustakaan tersedia.
- Tim penyusun memiliki akses administrator CCTV.
- Dashboard AI Agent utama belum dibangun.
- Vision Agent dikaji lebih awal sebagai salah satu agent dalam ekosistem multi-agent.
- Cakupan fisik dan inventaris kamera belum dipetakan.
- Kapabilitas ditargetkan dibangun bertahap.
- Horizon pilot, model pelaksana, dan anggaran belum ditetapkan.

### 1.2 Asumsi yang wajib diverifikasi

- Kamera menyediakan stream yang sah untuk integrasi, misalnya RTSP atau API VMS.
- NVR/VMS mengizinkan akses bersamaan tanpa mengganggu operasi keamanan.
- Sudut pandang, resolusi, FPS, pencahayaan, dan retensi memadai untuk use case tertentu.
- Jaringan kampus memiliki kapasitas dan segmentasi yang memadai.
- Penggunaan data untuk analitik telah memiliki dasar tujuan, otorisasi, dan pemberitahuan yang sesuai.

---

## 2. Rumusan Masalah

1. Bagaimana mengubah stream CCTV menjadi data terstruktur yang berguna bagi agent dan pengelola?
2. Kapabilitas vision apa yang paling layak dibangun lebih dahulu di perpustakaan?
3. Bagaimana merancang Vision Agent agar dapat berdiri mandiri tetapi siap masuk platform multi-agent?
4. Arsitektur pemrosesan mana yang paling seimbang antara privasi, latensi, biaya, keandalan, dan skalabilitas?
5. Bagaimana memastikan output model cukup akurat untuk keputusan operasional?
6. Bagaimana mencegah perluasan penggunaan menjadi pengawasan individu yang tidak proporsional?

---

## 3. Tujuan dan Manfaat

### 3.1 Tujuan

- Menyusun rancangan konseptual dan teknis Vision Agent.
- Menilai kelayakan integrasi CCTV perpustakaan.
- Menentukan roadmap pembangunan bertahap.
- Menyiapkan kontrak data dan API bagi dashboard multi-agent masa depan.
- Menyusun kerangka evaluasi, privasi, keamanan, tata kelola, biaya, dan skalabilitas.

### 3.2 Manfaat yang diharapkan

- Informasi occupancy dan pemanfaatan ruang berbasis data.
- Pemahaman jam sibuk dan pola arus pengunjung.
- Identifikasi area kurang termanfaatkan.
- Dukungan evaluasi antrean dan mutu layanan.
- Peringatan peristiwa tertentu dengan human verification.
- Dasar perencanaan kapasitas, tata letak, fasilitas, dan energi.

---

## 4. Ruang Lingkup dan Batasan

### Dalam ruang lingkup

- CCTV/NVR/VMS perpustakaan.
- Video ingestion, deteksi, tracking, counting, zone, flow, queue, dan event analytics.
- Vision Agent dan integrasi konseptual dengan dashboard AI Agent utama.
- API, event schema, penyimpanan metadata, evidence terbatas, monitoring, dan audit.
- Privasi, keamanan, etika, kepatuhan, organisasi, KPI, biaya, dan roadmap.

### Di luar ruang lingkup pilot awal

- Face recognition atau identifikasi individu.
- Keputusan disipliner otomatis.
- Tindakan fisik otomatis tanpa persetujuan manusia.
- Pengawasan atribut sensitif seperti emosi, ras, agama, atau kondisi kesehatan.
- Penggantian total sistem CCTV keamanan.
- Klaim akurasi final sebelum data lapangan tersedia.

---

## 5. Metodologi Kajian

Kajian memakai empat metode:

1. **Studi literatur:** paper, benchmark, standar, regulasi, dokumentasi teknis, dan praktik industri.
2. **Audit lapangan:** inventaris kamera, stream, zona, jaringan, kualitas video, dan proses operasional.
3. **Analisis arsitektur:** perbandingan on-premise, edge, cloud, dan hybrid berdasarkan kriteria terukur.
4. **Validasi pilot:** pengukuran akurasi, latensi, availability, false alarm, manfaat, privasi, dan biaya.

Setiap klaim dibedakan menjadi fakta terverifikasi, temuan literatur, asumsi, rekomendasi, atau isu terbuka.

---

## 6. Konsep Agentic AI Vision

### 6.1 Definisi operasional

Vision Agent adalah layanan agentik yang:

- menerima observasi visual dan metadata kamera;
- memakai pipeline computer vision untuk menghasilkan observasi terukur;
- mengubah observasi menjadi structured events;
- memvalidasi kualitas dan confidence;
- memakai konteks operasional melalui tool/API;
- menyusun insight dan rekomendasi dengan evidence;
- mengirim output ke dashboard atau agent lain;
- menyimpan audit trail dan menerapkan kontrol akses.

LLM/VLM bukan pengganti pipeline pengukuran. Counting dan tracking harus berasal dari model vision yang dapat diuji. Model bahasa dipakai untuk interpretasi, dialog, peringkasan, dan orkestrasi tool; bukan untuk mengarang angka.

### 6.2 Batas tanggung jawab

| Komponen | Tanggung jawab | Bukan tanggung jawab |
|---|---|---|
| Ingestion | Mengambil stream sah, sinkronisasi waktu, health check | Menetapkan makna kejadian |
| Vision pipeline | Deteksi, tracking, counting, zona, flow | Menentukan kebijakan kampus |
| Event processor | Agregasi, confidence, deduplikasi, validasi | Identifikasi personal |
| Vision Agent | Konteks, reasoning, insight, query, evidence | Tindakan berisiko tanpa manusia |
| Dashboard utama | Orkestrasi lintas-agent, visualisasi, role access | Mengubah fakta sumber |
| Operator | Verifikasi, tindak lanjut, koreksi, eskalasi | Mengabaikan audit dan kebijakan |

### 6.3 Kapabilitas target

1. **Occupancy:** jumlah orang per area dan status kapasitas.
2. **Flow:** arah, volume, dan pola masuk-keluar.
3. **Queue:** panjang antrean, waktu tunggu, dan service time jika kamera memadai.
4. **Zone utilization:** dwell time, tingkat pemakaian, dan area mati.
5. **Event detection:** kepadatan berlebih, area terlarang, objek tertinggal, atau peristiwa lain yang disetujui.
6. **Agentic insight:** penjelasan, perbandingan periode, korelasi konteks, rekomendasi, dan laporan.

---

## 7. Tinjauan Pustaka dan Teknologi

### 7.1 Deteksi, tracking, dan counting

Deteksi dan tracking merupakan fondasi video analytics. SORT menunjukkan tracking online dapat memakai Kalman filter dan Hungarian assignment dengan komputasi ringan [1]. Deep SORT menambahkan appearance information untuk mengurangi identity switch [2]. ByteTrack mempertahankan deteksi berconfidence rendah agar objek yang tertutup sebagian tetap dapat dilacak [3]. Untuk kerumunan padat, pendekatan crowd counting berbasis density map seperti CSRNet relevan ketika deteksi individu sulit [4].

Implikasi: pilihan model harus mengikuti sudut kamera dan kepadatan, bukan popularitas model. Kamera pintu masuk cenderung cocok untuk line crossing dan counting; ruang padat mungkin memerlukan density estimation; kamera koridor membutuhkan tracking dan zona.

### 7.2 Occupancy, flow, queue, dan zone

Occupancy dapat dihitung dari objek yang berada di polygon zona pada interval waktu. Flow memakai virtual line, entry/exit direction, dan track lifecycle. Queue memerlukan definisi area antrean, titik layanan, ambang waktu, serta pemisahan orang yang menunggu dari orang yang lewat. Zone utilization membutuhkan dwell time, bukan hanya jumlah deteksi sesaat.

Semua metrik bergantung pada kalibrasi kamera, definisi ground truth, occlusion, perubahan layout, dan pencahayaan. Angka harus memiliki timestamp, camera ID, zone ID, confidence, dan status kualitas.

### 7.3 Event dan anomaly detection

Event detection dapat bersifat rule-based, model supervised, atau anomaly detection. Rule-based event lebih mudah diaudit, misalnya occupancy melewati kapasitas atau track memasuki zona terlarang. Anomaly model lebih fleksibel tetapi sulit dijelaskan dan rentan false positive. Pilot sebaiknya memulai event terdefinisi jelas, dengan verifikasi operator dan tanpa inferensi atribut personal.

### 7.4 Vision-language model dan agent reasoning

LLaVA menunjukkan pola penggabungan vision encoder dan language model untuk instruksi multimodal [5]. ReAct memperkenalkan pola reasoning dan action melalui tool [6]. Dalam Vision Agent, pola ini diterapkan secara konservatif: model menerima event terstruktur, memanggil API konteks, menyusun jawaban, dan menunjuk evidence. VLM dapat membantu analisis cuplikan terbatas, tetapi output numerik utama harus berasal dari pipeline terukur.

Risiko utama reasoning agent: hallucination, prompt injection dari data eksternal, overclaim confidence, dan tindakan yang melampaui izin. Mitigasi: structured tools, schema validation, allow-list tool, confidence propagation, evidence requirement, output policy, dan human approval.

### 7.5 Edge, on-premise, cloud, hybrid

Pemrosesan lokal mengurangi perpindahan video dan ketergantungan koneksi, tetapi memerlukan GPU, operasi, dan pemeliharaan. Cloud mempercepat elastisitas, tetapi meningkatkan biaya egress, risiko privasi, dan kebutuhan koneksi. Edge mengurangi bandwidth dan latensi; hybrid membagi inferensi video di lingkungan kampus dan reasoning/dashboard pada layanan terkontrol.

Rekomendasi awal: uji hybrid dengan raw video tetap lokal, metadata dikirim ke event store/API, dan snapshot atau clip hanya diambil berdasarkan izin serta kebutuhan evidence.

---

## 8. Analisis Kebutuhan Perpustakaan

### 8.1 Pemangku kepentingan

- Pengelola perpustakaan: keputusan ruang, layanan, dan kapasitas.
- Petugas layanan: antrean, kepadatan, dan verifikasi event.
- Unit TI: jaringan, integrasi, keamanan, dan operasi.
- Pengelola keamanan: hubungan dengan sistem CCTV eksisting.
- Pimpinan: manfaat, risiko, anggaran, dan skalabilitas.
- Pemustaka: transparansi, privasi, dan kualitas layanan.
- Tim data/AI: model, evaluasi, MLOps, dan governance.

### 8.2 Use case prioritas

| Prioritas | Use case | Nilai | Ketergantungan |
|---|---|---|---|
| 1 | Occupancy ruang baca | Tinggi | Kamera menghadap area, kapasitas zona |
| 1 | Counting pintu masuk/keluar | Tinggi | Kamera pintu, line crossing |
| 1 | Zone utilization | Tinggi | Polygon zona, dwell time |
| 2 | Flow koridor | Menengah-tinggi | Tracking, arah, overlap |
| 2 | Queue meja layanan | Menengah | Sudut kamera dan definisi antrean |
| 3 | Event kepadatan berlebih | Menengah | Threshold, alarm policy, operator |
| 3 | Area terlarang/objek tertinggal | Menengah | Data uji, SOP respons |

### 8.3 Output operasional

- Kondisi saat ini dan tren per jam/hari/minggu.
- Peringatan kapasitas dengan threshold yang dikonfigurasi.
- Peta pemanfaatan zona.
- Perbandingan antarperiode.
- Ringkasan natural language dengan sumber event.
- Rekomendasi operasional yang tidak otomatis mengikat.

---

## 9. Arsitektur Konseptual

```text
CCTV → NVR/VMS → Video Gateway → Vision Inference
                                  ↓
                    Detection / Tracking / Zone / Rules
                                  ↓
                         Structured Event Store
                                  ↓
                           Vision Agent API
                  ↙              ↓                ↘
          Pilot Dashboard   Event Bus/API    Evidence Store
                                  ↓
                       Dashboard AI Agent Utama
                         (multi-agent platform)
```

### 9.1 Lapisan sistem

1. **Source layer:** CCTV, NVR/VMS, time synchronization.
2. **Ingestion layer:** RTSP/API connector, buffering, reconnect, stream health.
3. **Inference layer:** detector, tracker, classifier terbatas, zone/line rules.
4. **Event layer:** schema, validation, aggregation, retention, lineage.
5. **Agent layer:** tools, context retrieval, reasoning, insight, guardrails.
6. **Experience layer:** pilot dashboard, API gateway, dashboard utama masa depan.
7. **Governance layer:** IAM, audit, model registry, monitoring, incident response.

### 9.2 Perbandingan arsitektur

| Kriteria | On-premise | Edge | Cloud | Hybrid |
|---|---|---|---|---|
| Privasi video | Tinggi | Sangat tinggi | Bergantung provider | Tinggi |
| Latensi | Rendah | Sangat rendah | Bergantung jaringan | Rendah |
| Skalabilitas | Sedang | Per kamera | Tinggi | Tinggi |
| Biaya awal | Tinggi | Sedang per titik | Rendah awal | Sedang |
| Operasi | Tim kampus | Terdistribusi | Vendor/cloud | Gabungan |
| Rekomendasi | Cocok bila server siap | Cocok untuk inference | Cocok untuk kebutuhan tertentu | Pilihan awal |

### 9.3 Kontrak integrasi

Vision Agent harus menyediakan:

- REST/gRPC API untuk query dan command non-destruktif.
- Event bus untuk event real-time.
- OpenAPI terdokumentasi.
- Schema versioning.
- Capability registry: kemampuan agent, tool, batasan, confidence.
- OAuth2/OIDC atau mekanisme IAM kampus.
- Idempotency key dan correlation ID.
- Audit log untuk setiap query, event, dan rekomendasi.

---

## 10. Data Pipeline dan Event Schema

### 10.1 Prinsip data

- Raw video dipisahkan dari metadata.
- Anonymous track ID hanya berlaku dalam scope dan periode yang ditentukan.
- Timestamp memakai zona waktu dan sinkronisasi konsisten.
- Confidence dan kualitas stream selalu dibawa ke output.
- Data agregat dipertahankan lebih lama daripada video mentah.
- Evidence disimpan terbatas, terenkripsi, dan berbasis izin.

### 10.2 Contoh schema event

```json
{
  "schema_version": "vision.event.v1",
  "event_id": "evt-20260831-000001",
  "event_type": "occupancy_update",
  "observed_at": "2026-08-31T10:15:00+07:00",
  "source": {
    "camera_id": "cam-lib-02",
    "site_id": "library",
    "zone_id": "reading-room-floor-2"
  },
  "measurement": {
    "count": 42,
    "capacity": 60,
    "occupancy_ratio": 0.70
  },
  "confidence": 0.93,
  "quality": {
    "stream_ok": true,
    "occlusion_level": "medium",
    "lighting": "acceptable"
  },
  "privacy": {
    "identity_mode": "anonymous",
    "face_recognition": false
  },
  "evidence_ref": null,
  "model": {
    "name": "<model-registry-name>",
    "version": "<version>"
  }
}
```

Placeholder model registry wajib diisi sebelum implementasi produksi. Schema contoh bukan klaim bahwa ID kamera atau model tersebut sudah tersedia.

### 10.3 Event quality states

- `valid`: stream dan confidence memenuhi ambang.
- `degraded`: event tersedia tetapi ada occlusion/lighting issue.
- `unavailable`: stream atau model gagal.
- `needs_review`: event berisiko atau confidence rendah.

Agent utama tidak boleh menyajikan `degraded` sebagai fakta pasti.

---

## 11. Audit CCTV dan Infrastruktur

### 11.1 Inventaris minimum

| Area audit | Data yang dicatat |
|---|---|
| Kamera | ID, merek, model, lokasi, firmware, resolusi, FPS |
| Stream | RTSP/ONVIF/API, codec, bitrate, autentikasi, concurrency |
| NVR/VMS | model, retensi, API, ekspor, beban, hak akses |
| Jaringan | VLAN, bandwidth, latency, firewall, jalur ke server |
| Visual | sudut, tinggi, overlap, glare, night condition, occlusion |
| Operasi | SOP, jam layanan, layout, kapasitas zona, respons alarm |
| Data | retensi, backup, akses, enkripsi, penghapusan |

### 11.2 Pemilihan kamera pilot

Pilih 3–5 kamera representatif setelah audit:

1. pintu masuk/keluar;
2. ruang baca;
3. meja layanan;
4. koridor;
5. area dengan tantangan visual.

Pemilihan harus berbasis matriks kamera–use case, bukan jumlah kamera semata.

### 11.3 Kebutuhan komputasi

Spesifikasi final menunggu resolusi, FPS, jumlah stream, model, dan target latency. Uji harus mengukur throughput stream per GPU/CPU, penggunaan VRAM/RAM, dropped frames, dan thermal stability. Jangan menetapkan jumlah GPU dari jumlah kamera tanpa benchmark.

---

## 12. Privasi, Etika, Keamanan, dan Kepatuhan

### 12.1 Prinsip

- Tujuan spesifik dan proporsional.
- Data minimization.
- Privacy by design/default.
- Transparansi dan pemberitahuan.
- Pembatasan akses.
- Retensi minimum.
- Akurasi dan mekanisme koreksi.
- Human oversight.
- Auditability.
- Keamanan sejak ingestion sampai deletion.

### 12.2 Identitas dan biometrik

Kebijakan identitas masih terbuka. Kajian membandingkan tiga mode:

1. **Anonim:** deteksi dan tracking tanpa identifikasi.
2. **Verifikasi terbatas:** hanya untuk tujuan yang sangat spesifik dan terotorisasi.
3. **Pengenalan wajah:** data biometrik dengan risiko dan kewajiban tertinggi.

Rekomendasi pilot: mode anonim. Face recognition tidak boleh diaktifkan hanya karena kamera atau model mendukungnya. Sebelum dipertimbangkan diperlukan tujuan tertulis, legal review, penilaian dampak, dasar pemrosesan, pemberitahuan, kontrol akses kuat, retensi, prosedur keberatan/koreksi, dan persetujuan pimpinan yang berwenang.

### 12.3 Dasar regulasi

UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi perlu menjadi rujukan utama. Data biometrik termasuk data pribadi yang bersifat spesifik. Penerapan CCTV dan analitik harus ditinjau bersama unit hukum, keamanan informasi, dan pengelola data. Dokumen ini bukan opini hukum final.

Rujukan tata kelola internasional: NIST AI RMF 1.0, ISO/IEC 42001:2023, ISO/IEC 23894:2023, dan prinsip security/privacy engineering. Standar tersebut membantu struktur governance, tetapi tidak menggantikan kewajiban hukum Indonesia.

### 12.4 Ancaman keamanan

- Kredensial kamera/NVR bocor.
- Stream disadap.
- Model endpoint dieksploitasi.
- Prompt injection melalui metadata atau event.
- Evidence diakses tanpa kewenangan.
- Data event dimanipulasi.
- Denial of service pada ingestion.
- Model drift menghasilkan alarm salah.

Kontrol: secret vault, rotasi kredensial, VLAN, firewall allow-list, TLS, encryption at rest, mTLS bila memungkinkan, least privilege, signed event, immutable audit, rate limit, patching, backup, penetration test, dan incident response.

---

## 13. Desain Pembangunan Bertahap

### Fase 0 — Audit dan baseline

Durasi indikatif: 3–4 minggu. Keluaran: inventaris, peta kamera, uji stream, privacy impact pre-assessment, definisi zona, ground truth plan, dan pilihan kamera.

### Fase 1 — Analitik dasar

Occupancy, people counting, entry/exit flow, zone utilization. Keluaran: dashboard pilot, event schema v1, model baseline, dan laporan akurasi.

### Fase 2 — Analitik layanan

Queue length, waktu tunggu, dwell time, peak-hour analysis. Hanya aktif pada kamera dengan sudut dan kualitas memadai.

### Fase 3 — Event detection terbatas

Kepadatan berlebih, area terlarang, objek tertinggal, atau event lain yang disetujui. Semua alert berisiko memerlukan verifikasi petugas.

### Fase 4 — Agentic intelligence

Natural-language query, korelasi kalender/jadwal/fasilitas, ringkasan, rekomendasi, dan laporan berkala. Semua insight menyertakan sumber, waktu, confidence, dan keterbatasan.

### Fase 5 — Integrasi operasional

Integrasi dengan sistem fasilitas atau notifikasi. Tidak ada tindakan fisik otomatis tanpa human approval dan SOP yang disahkan.

### Gate antar fase

Fase berikutnya hanya boleh dimulai jika fase sebelumnya memenuhi ambang teknis, manfaat, keamanan, privasi, dan kesiapan operasi. Kegagalan satu kamera tidak boleh disamarkan sebagai keberhasilan sistem.

---

## 14. Evaluasi dan KPI

### 14.1 Dimensi dan bobot awal

| Dimensi | Bobot |
|---|---:|
| Manfaat operasional | 35% |
| Kinerja teknis | 30% |
| Kesiapan integrasi | 20% |
| Skalabilitas dan investasi | 15% |

### 14.2 KPI teknis

- MAE/RMSE counting terhadap ground truth.
- Precision, recall, F1 untuk event.
- ID switch dan tracking continuity.
- Queue estimation error dan waiting-time error.
- Latensi end-to-end.
- Stream availability dan dropped-frame rate.
- False alarm per jam/kamera.
- Biaya komputasi per kamera per bulan.

Ambang angka ditetapkan setelah baseline. Jangan memakai target akurasi generik tanpa mempertimbangkan sudut kamera dan definisi metrik.

### 14.3 KPI operasional

- Waktu pengelola memperoleh informasi.
- Frekuensi keputusan berbasis dashboard.
- Ketepatan identifikasi jam sibuk.
- Perubahan pemanfaatan zona.
- Perbaikan waktu respons atau antrean jika use case aktif.
- Kepuasan operator dan pemustaka.
- Jumlah insight yang dapat ditindaklanjuti.

### 14.4 Kriteria keberhasilan awal

Pilot direkomendasikan berlanjut bila:

- Tidak ada insiden privasi/keamanan kritis.
- Data valid tersedia pada mayoritas jam operasi yang disepakati.
- Minimal satu use case menghasilkan manfaat terukur.
- Event schema dan API dapat dikonsumsi client independen.
- Operator memahami confidence dan batasan output.
- Biaya serta kebutuhan operasi dapat diproyeksikan.

Skor gabungan 75/100 dapat digunakan sebagai indikator awal, tetapi tidak mengalahkan stop condition keamanan atau kepatuhan.

---

## 15. Model Organisasi dan Pelaksana

Model awal yang direkomendasikan: kolaborasi tim internal dengan vendor/mitra riset.

### Pemilik internal

- Product owner: tujuan dan prioritas manfaat.
- Data owner: tujuan, akses, retensi, dan persetujuan penggunaan.
- TI/platform: jaringan, IAM, deployment, reliability.
- AI/ML: model, evaluasi, registry, drift.
- Legal/privacy/security: review dan kontrol.
- Perpustakaan: SOP, ground truth, verifikasi event, feedback.

### Prinsip pengadaan/kemitraan

- Hak akses dan hak atas data tetap jelas.
- Source/configuration/API terdokumentasi.
- Ada transfer knowledge dan exit plan.
- Tidak ada vendor lock-in yang menghalangi ekspor event.
- Model dan data pelatihan memiliki provenance.
- SLA, patching, incident response, dan biaya ekspansi terukur.

---

## 16. Analisis Biaya dan Manfaat

### Komponen biaya

1. Audit dan desain.
2. Video gateway dan konektor NVR/VMS.
3. Server/edge/GPU atau cloud compute.
4. Storage metadata dan evidence.
5. Pengembangan model, API, dashboard, dan agent.
6. Network/security/IAM/monitoring.
7. Labeling dan ground truth.
8. Operasi, pemeliharaan, retraining, dan support.
9. Legal/privacy assessment dan sosialisasi.

Anggaran nominal belum dapat dihitung secara bertanggung jawab sebelum jumlah kamera, resolusi/FPS, retensi, target latency, pilihan deployment, dan model pelaksana diketahui. Buat tiga skenario anggaran setelah Fase 0: minimum, recommended, dan scale-up.

### Manfaat

- Penghematan waktu observasi dan pelaporan.
- Penggunaan ruang lebih optimal.
- Dasar perencanaan fasilitas.
- Potensi efisiensi energi, jika dihubungkan dengan kontrol fasilitas melalui proses aman.
- Peningkatan kualitas layanan.
- Reusable platform untuk unit kampus lain.

Perhitungan manfaat harus memakai baseline sebelum pilot dan tidak mengklaim penghematan energi tanpa pengukuran meter serta perubahan operasi yang dapat diatribusikan.

---

## 17. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Akses admin tidak menyediakan stream | Tinggi | Uji RTSP/API resmi pada Fase 0 |
| Occlusion/pencahayaan buruk | Tinggi | Audit visual, reposisi, confidence state |
| False count/event | Tinggi | Ground truth, threshold, operator review |
| Pelanggaran privasi | Sangat tinggi | Anonymous default, DPIA, minimization |
| Kebocoran credential | Sangat tinggi | Vault, rotation, least privilege |
| Vendor lock-in | Menengah-tinggi | API/schema terbuka, exit plan |
| Model drift/layout berubah | Menengah | Monitoring, recalibration, retraining |
| Agent hallucination | Tinggi | Tool-only facts, evidence, schema validation |
| Dashboard belum tersedia | Menengah | Pilot dashboard + integration gateway |
| Biaya scale-up tinggi | Menengah | Benchmark per kamera, edge/hybrid |
| Penolakan pengguna | Menengah-tinggi | Transparansi, konsultasi, batas tujuan |
| Sistem mengganggu CCTV keamanan | Tinggi | Read-only integration, rate limit, isolasi |

---

## 18. Roadmap Rekomendasi

### 0–1 bulan

Audit CCTV, stakeholder workshop, use-case charter, privacy/security review awal, dan definisi ground truth.

### 2–3 bulan

PoC 1–2 kamera, occupancy/counting, event schema, pilot dashboard, benchmark model dan komputasi.

### 4–6 bulan

Pilot operasional 3–5 kamera, zone/flow, evaluasi manfaat, hardening keamanan, dan dokumentasi API.

### 7–9 bulan

Queue serta event detection terbatas, jika gate sebelumnya lulus. Uji operator, false alarm, dan SOP respons.

### 10–12 bulan

Agentic query, reasoning berbasis event, integrasi konteks nonvisual, dan rekomendasi skalabilitas.

### Setelah 12 bulan

Keputusan scale-up berdasarkan bukti; perluasan ke unit lain hanya setelah template governance, deployment, dan evaluasi siap.

---

## 19. Keputusan yang Diminta

1. Menyetujui kajian dan audit Fase 0.
2. Menetapkan perpustakaan sebagai lokasi pilot awal.
3. Menunjuk product owner, data owner, dan tim lintas fungsi.
4. Menyetujui prinsip anonymous-first dan larangan face recognition pada pilot tanpa persetujuan khusus.
5. Menyetujui pembangunan Vision Agent mandiri dengan API/schema versioned.
6. Menyetujui pembandingan arsitektur deployment sebelum pengadaan.
7. Menetapkan mekanisme anggaran dan model pelaksana untuk PoC.
8. Menetapkan gate evaluasi sebelum perluasan use case.

---

## 20. Kesimpulan

Vision Agent layak dikaji lebih awal sebagai fondasi persepsi fisik dalam UGM Agent. CCTV eksisting memberi titik masuk pragmatis, tetapi keberhasilan tidak ditentukan oleh model AI saja. Audit stream, kualitas kamera, definisi ground truth, tata kelola data, privacy-by-design, dan integrasi terbuka sama pentingnya.

Pendekatan paling aman dan bernilai adalah membangun pipeline terukur mulai dari occupancy, flow, dan zone utilization; mengirim metadata terstruktur ke agent utama; lalu menambah queue, event detection, dan reasoning secara bertahap. Identifikasi wajah tidak diperlukan untuk membuktikan manfaat awal dan sebaiknya tidak menjadi bagian pilot.

Keputusan pertama yang paling penting bukan memilih model, melainkan menyetujui Fase 0 yang menghasilkan fakta teknis dan operasional. Setelah itu UGM dapat memilih arsitektur dan anggaran berdasarkan bukti lapangan.

---

# Daftar Pustaka Pilihan

[1] A. Bewley et al., “Simple Online and Realtime Tracking,” *2016 IEEE International Conference on Image Processing (ICIP)*, 2016. DOI: https://doi.org/10.1109/ICIP.2016.7533003

[2] N. Wojke, A. Bewley, and D. Paulus, “Simple Online and Realtime Tracking with a Deep Association Metric,” *2017 IEEE International Conference on Image Processing (ICIP)*, 2017. DOI: https://doi.org/10.1109/ICIP.2017.8296962

[3] Y. Zhang et al., “ByteTrack: Multi-Object Tracking by Associating Every Detection Box,” *ECCV*, 2022. DOI: https://doi.org/10.1007/978-3-031-20047-2_1

[4] Y. Li, X. Zhang, and D. Chen, “Csrnet: Dilated Convolutional Neural Networks for Understanding the Highly Congested Scenes,” *CVPR*, 2018. DOI: https://doi.org/10.1109/CVPR.2018.00440

[5] H. Liu et al., “Visual Instruction Tuning,” arXiv:2304.08485, 2023. URL: https://arxiv.org/abs/2304.08485

[6] S. Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” arXiv:2210.03629, 2022. URL: https://arxiv.org/abs/2210.03629

[7] National Institute of Standards and Technology, “Artificial Intelligence Risk Management Framework (AI RMF 1.0),” NIST AI 100-1, 2023. URL: https://www.nist.gov/itl/ai-risk-management-framework

[8] ISO/IEC, “ISO/IEC 42001:2023 Information technology — Artificial intelligence — Management system,” 2023. URL: https://www.iso.org/standard/81230.html

[9] ISO/IEC, “ISO/IEC 23894:2023 Information technology — Artificial intelligence — Guidance on risk management,” 2023. URL: https://www.iso.org/standard/77304.html

[10] Republik Indonesia, “Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi.” URL: https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022

[11] OWASP Foundation, “OWASP Top 10 for Large Language Model Applications,” 2025. URL: https://owasp.org/www-project-top-10-for-large-language-model-applications/

[12] ONVIF, “ONVIF Profile S — IP-based video systems,” official documentation. URL: https://www.onvif.org/profiles/profile-s/

[13] C. Zhang, H. Li, X. Wang, and X. Yang, “Single-Image Crowd Counting via Multi-Column Convolutional Neural Network,” *CVPR*, 2016. DOI: https://doi.org/10.1109/CVPR.2016.70

[14] V. A. Sindagi, R. Yasarla, and V. M. Patel, “Pushing the Frontiers of Unconstrained Crowd Counting: New Dataset and Benchmark Method,” *ICCV*, 2019. DOI: https://doi.org/10.1109/ICCV.2019.00131

[15] P. Dendorfer et al., “MOT20: A Benchmark for Multi Object Tracking in Crowded Scenes,” arXiv:2003.09003, 2020. URL: https://arxiv.org/abs/2003.09003

[16] W. Sultani, C. Chen, and M. Shah, “Real-world Anomaly Detection in Surveillance Videos,” *CVPR*, 2018. DOI: https://doi.org/10.1109/CVPR.2018.00675

[17] S. Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” arXiv:2210.03629, 2022. DOI: https://doi.org/10.48550/arXiv.2210.03629

[18] D. Driess et al., “PaLM-E: An Embodied Multimodal Language Model,” arXiv:2303.03378, 2023. DOI: https://doi.org/10.48550/arXiv.2303.03378

[19] S. Liu et al., “LLaVA-Plus: Learning to Use Tools for Creating Multimodal Agents,” arXiv:2311.05437, 2023. URL: https://arxiv.org/abs/2311.05437

[20] Q. Wu et al., “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation,” arXiv:2308.08155, 2023. URL: https://arxiv.org/abs/2308.08155

[21] European Data Protection Board, “Guidelines 3/2019 on processing of personal data through video devices,” final version, 2020. URL: https://www.edpb.europa.eu/documents/guideline/guidelines-32019-on-processing-of-personal-data-through-video-devices_en

[22] Republik Indonesia, “Peraturan Pemerintah Nomor 71 Tahun 2019 tentang Penyelenggaraan Sistem dan Transaksi Elektronik.” URL: https://peraturan.bpk.go.id/Details/122030/pp-no-71-tahun-2019

[23] Kementerian Komunikasi dan Informatika Republik Indonesia, “Surat Edaran Menteri Komunikasi dan Informatika Nomor 9 Tahun 2023 tentang Etika Kecerdasan Artifisial.” URL: https://jdih.komdigi.go.id/produk_hukum/view/id/883/t/surat+edaran+menteri+komunikasi+dan+informatika+nomor+9+tahun+2023+tentang+etika+kecerdasan+artifisial

[24] NIST, “Privacy Framework: A Tool for Improving Privacy through Enterprise Risk Management,” 2020. URL: https://www.nist.gov/privacy-framework

[25] NIST, “Cybersecurity Framework 2.0,” 2024. URL: https://www.nist.gov/cyberframework

[26] NIST, “Zero Trust Architecture,” SP 800-207, 2020. URL: https://csrc.nist.gov/pubs/sp/800/207/final

[27] ISO/IEC, “ISO/IEC 38507:2022 Governance implications of the use of artificial intelligence by organizations,” 2022. URL: https://www.iso.org/standard/81230.html

[28] ISO/IEC, “ISO/IEC 29134:2017 Guidelines for privacy impact assessment,” 2017. URL: https://www.iso.org/standard/62289.html

---

# Lampiran A — Checklist Audit CCTV

- [ ] Daftar semua kamera dan lokasi.
- [ ] Model, firmware, resolusi, FPS, codec, bitrate.
- [ ] RTSP/ONVIF/API berhasil diuji secara read-only.
- [ ] NVR/VMS concurrency dan dampak integrasi diuji.
- [ ] Peta jaringan, VLAN, firewall, dan jalur server tersedia.
- [ ] Kualitas siang/malam, glare, occlusion, dan blind spot dinilai.
- [ ] Zona dan kapasitas perpustakaan disahkan pengelola.
- [ ] Retensi raw video, metadata, dan evidence ditetapkan.
- [ ] Role access dan audit log ditetapkan.
- [ ] SOP respons event ditetapkan.
- [ ] Pemberitahuan/policy privasi ditinjau.

# Lampiran B — Matriks Uji Model

| Uji | Ground truth | Metrik | Kondisi |
|---|---|---|---|
| Counting pintu | Hitungan manual berinterval | MAE, RMSE | Rendah/sedang/tinggi |
| Occupancy zona | Sampling manual | MAE, occupancy error | Siang/malam |
| Flow | Log crossing manual | Precision/recall | Dua arah |
| Queue | Timestamp antrean manual | Length/time error | Jam sibuk |
| Event | Label operator | Precision, recall, F1 | Normal/anomali |
| Operasi | Monitoring sistem | Availability, latency | Beban target |

# Lampiran C — Pertanyaan Terbuka

1. Berapa total kamera dan berapa yang mencakup zona target?
2. Apakah NVR/VMS menyediakan RTSP, ONVIF, API, atau SDK resmi?
3. Berapa retensi video dan kebijakan akses yang berlaku?
4. Siapa data owner dan siapa yang berwenang menyetujui penggunaan analitik?
5. Berapa target latency dan jam operasi?
6. Apakah server GPU/edge tersedia?
7. Apakah ada sistem tiket, jadwal ruang, atau fasilitas untuk integrasi konteks?
8. Model pengadaan dan pelaksana mana yang dipilih?
9. Bagaimana pengguna diberi informasi dan kanal keberatan?
10. Apa stop condition bila akurasi atau risiko tidak memenuhi ambang?

# Lampiran D — Glosarium

- **Agentic AI:** sistem AI yang dapat merencanakan, memakai tool, dan menjalankan langkah terbatas menuju tujuan.
- **Anonymous track ID:** ID sementara untuk mempertahankan jejak tanpa mengetahui identitas orang.
- **Edge inference:** inferensi dekat sumber data.
- **Event schema:** struktur standar untuk merepresentasikan peristiwa.
- **Flow:** arus pergerakan melalui garis atau koridor.
- **Occupancy:** jumlah atau rasio orang dalam area.
- **VLM:** vision-language model.
- **Zone utilization:** tingkat dan pola pemakaian area.
- **DPIA:** data protection impact assessment/penilaian dampak perlindungan data.
- **NVR/VMS:** network video recorder/video management system.

*Catatan: URL dan status regulasi/standar perlu diperiksa ulang oleh tim sebelum dokumen resmi diterbitkan.*
## Penutup

Dokumen ini menjadi dasar diskusi Fase 0, bukan spesifikasi pengadaan final.
