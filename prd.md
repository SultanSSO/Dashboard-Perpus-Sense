# PRD: PerpusSense Dashboard v2 (Anti-Slop)

## Overview
Dashboard v2 adalah update dari dashboard perpustakaan okupansi versi 1 dengan menerapkan skill anti-slop. Tema, permainan warna, dan alur tetap sama; hanya tampilan diubah menjadi lebih humanize dan terhindar dari pola AI slop.

## Output Target
1. Dashboard yang tidak mengandung AI slop, didukung oleh skill anti-slop dan DESIGN.md
2. Tema UGM (primary #125174, gold #F4C542) dan alur tetap sama
3. Tampilan lebih humanize: menghindari pola generik AI (em dash, CTA generik, badge berlebihan, animasi template, spacing uniform)
4. Dashboard baru diakses melalui terminal dengan perintah `dashboard-perpus-v2`
5. Semua perubahan, dependency, dan requirements tetap di venv (tidak merusak ekosistem global)

## Scope Modifikasi

### 1. File yang Dimodifikasi (Frontend)
**Lokasi:** `desain-awal-dashboard/`

#### 1.1 HTML (5 file)
- `login.html` - halaman login
- `index.html` - dashboard utama (ringkasan okupansi)
- `live.html` - monitoring live kamera CCTV
- `analytics.html` - riwayat & analitik
- `settings.html` - pengaturan

**Modifikasi:**
- Hilangkan em dash (—) di semua teks UI
- Ganti CTA generik: "Masuk" tetap (konteks jelas), tapi hindari "Learn More", "Get Started" di halaman lain jika ada
- Hilangkan uppercase dengan letter-spacing ekstrem (misal: MENU jika ada)
- Badge status: pastikan ada alasan fungsional (LIVE badge = real-time indicator, valid)
- Perbaiki semantik: pastikan semua tombol pakai `<button>` untuk aksi, `<a href>` untuk navigasi
- Tambah `cursor: pointer` untuk semua kontrol interaktif
- Verifikasi contrast ratio WCAG AA (sudah aman karena pakai warna brand yang kontras)

#### 1.2 CSS (1 file)
- `assets/css/style.css`

**Modifikasi:**
- Tambahkan aturan global `button, a[href], label[for], select { cursor: pointer; }`
- Pastikan animasi tidak berlebihan (animasi `seat-pop` dan `pulse-gold` sudah minimal, pertahankan)
- Periksa shadow: `shadow-2` sudah ringan, pertahankan
- Border radius: sudah konsisten (Tailwind `rounded-sm` = 10px), tidak pill-shaped, aman
- Glassmorphism: tidak ada blur berlebihan di CSS ini, aman
- Verifikasi hover/active/disabled state sudah jelas

#### 1.3 JavaScript (7 file)
- `assets/js/api.js` - HTTP client wrapper
- `assets/js/auth.js` - auth check
- `assets/js/login.js` - login form handler
- `assets/js/app.js` - dashboard main (okupansi, chart)
- `assets/js/live.js` - live monitoring grid
- `assets/js/analytics.js` - analytics page
- `assets/js/settings.js` - settings page
- `assets/js/cctv-data.js` - data model stub

**Modifikasi (minor, karena JS logic aman):**
- Tidak ada perubahan logic bisnis
- Pastikan error message tidak pakai em dash
- Pastikan label dinamis (misal: notifikasi, badge) tidak inject em dash dari backend

### 2. File Baru yang Dibuat

#### 2.1 DESIGN.md
**Lokasi:** `DESIGN.md` (root proyek)

**Isi akan mencakup:**
- Identity: Platform, audience, character dashboard
- Palette: Brand UGM dengan alasan warna
- Typography: Satoshi dengan alasan pemilihan
- Layout & Rhythm: TailAdmin structure dengan spacing hirarki
- Motion: Minimal (hover, focus, alert feedback)
- Components: Badge, icon, shadow dengan alasan fungsional
- Dials: ENERGY 1, RHYTHM 1, MOTION 1 (dashboard operasional calm)
- Anti-Slop Checklist: yang dihindari dan yang valid

#### 2.2 CLI Entry Point
**Lokasi:** `scripts/dashboard_v2_cli.py` (script baru)

Script sederhana yang menjalankan dashboard server. User bisa jalankan dengan:
```bash
.venv/bin/python scripts/dashboard_v2_cli.py
```

Atau buat alias/wrapper shell script `dashboard-perpus-v2` yang memanggil script ini.

### 3. Backend (Tidak Diubah)
- `vision_agent/dashboard/server.py` - HTTP server, API handler
- `vision_agent/mcp/service.py` - CCTVService logic
- `vision_agent/runtime_manager.py` - Runtime state

**Status:** Tidak ada perubahan. Backend API sudah bersih, hanya serve data JSON dan snapshot JPEG.

### 4. Dependencies (Tidak Berubah)
- `requirements.txt` tetap (minimal HTTP server, python-dotenv)
- Tidak ada dependency baru (semua modifikasi di static HTML/CSS/JS)

## Timeline Eksekusi

### Phase 1: Setup & Documentation
1. Buat `DESIGN.md` di root
2. Review skill anti-slop
3. Commit baseline: "docs: add DESIGN.md and PRD for v2 anti-slop"

### Phase 2: HTML Modification (anti-slop compliance)
**Per file:**
1. `login.html`: periksa copywriting (em dash, label button)
2. `index.html`: periksa dashboard card, badge, spacing
3. `live.html`: periksa badge LIVE (valid), tile CCTV layout
4. `analytics.html`: periksa chart, legend, filter UI
5. `settings.html`: periksa form label, button CTA

**Checklist per file (Hard Gate dari antislop):**
- [ ] Tidak ada em dash (—) di teks UI (R-02)
- [ ] Layout mobile tidak overflow (R-03)
- [ ] Tidak ada angka/statistik palsu (R-17, sudah aman karena data dari backend)
- [ ] Tidak ada testimonial palsu (R-18, tidak ada testimonial di dashboard)
- [ ] Navigasi tidak ada link mati (R-24)
- [ ] Contrast WCAG AA pass (R-25, sudah aman dengan palet UGM)
- [ ] Semua tombol/link punya behavior (R-26)
- [ ] Ada empty/loading/error state (R-27, ada di JS)
- [ ] Keyboard navigable (R-32)
- [ ] Badge hanya untuk status real (R-09)
- [ ] CTA tidak generik (R-15)

### Phase 3: CSS Refinement
1. Tambah `cursor: pointer` global untuk kontrol interaktif
2. Verifikasi animasi tidak berlebihan
3. Pastikan hover/focus/disabled state jelas

### Phase 4: CLI Integration
1. Buat `scripts/dashboard_v2_cli.py`
2. Test run: `.venv/bin/python scripts/dashboard_v2_cli.py`
3. Buat wrapper shell script atau alias untuk `dashboard-perpus-v2`

### Phase 5: Delivery Gate (Mandatory)
Run checklist antislop Delivery Gate (4 blocks):
1. **Hard Gate:** jawaban semua pertanyaan = NO
2. **Purpose-Gate:** setiap teknik punya alasan tertulis (di DESIGN.md)
3. **Liveliness:** dials set (ENERGY 1, RHYTHM 1, MOTION 1), identitas jelas (brand UGM)
4. **Craftsmanship & Quality Locks:** C-1 sampai C-5 pass, consistency rules pass

**Output:** Laporan PASS/FAIL dengan bukti konkret.

### Phase 6: Final Verification
1. Run dashboard: `dashboard-perpus-v2`
2. Click-through manual: login → dashboard → live → analytics → settings → logout
3. Test mobile responsive (resize browser)
4. Test dark mode toggle
5. Test keyboard navigation (Tab, Enter, Escape)
6. Screenshot setiap halaman untuk dokumentasi

## Acceptance Criteria
1. ✅ Dashboard v2 berjalan dengan perintah `dashboard-perpus-v2`
2. ✅ Semua halaman (5 halaman) lolos Delivery Gate antislop (PASS semua block)
3. ✅ Tidak ada em dash di teks UI
4. ✅ CTA spesifik konteks (atau tetap jika sudah spesifik)
5. ✅ Badge hanya untuk status real (LIVE, alert count)
6. ✅ Keyboard navigable, focus state jelas
7. ✅ Mobile responsive, tidak ada overflow
8. ✅ Dark mode bekerja di semua halaman
9. ✅ `DESIGN.md` lengkap dengan alasan setiap keputusan visual
10. ✅ Semua modifikasi dalam venv, tidak ada dependency global baru

## Notes
- **Tema dan warna tetap:** Brand UGM (primary #125174, gold #F4C542) tidak berubah, ini bukan slop karena brand identity institusi.
- **Font Satoshi tetap:** Sudah dipilih dengan alasan (professional, readable), bukan default AI tanpa alasan.
- **Dark mode tetap:** Legitimate reason: dashboard operator CCTV, monitoring panjang, dark default mengurangi eye strain.
- **TailAdmin structure tetap:** Layout sidebar + topbar + main content adalah proven pattern untuk dashboard admin, bukan clone tanpa alasan.
- **Modifikasi minimal:** Karena dashboard v1 sudah cukup bersih, modifikasi fokus pada copywriting (em dash), semantik HTML (cursor pointer), dan dokumentasi (DESIGN.md).

---

## Status Eksekusi

Dieksekusi pada 13 November 2026. Semua fase selesai dan diverifikasi di browser
sungguhan (Chromium via CDP), bukan hanya dengan membaca kode.

### Yang berubah

**File baru**
- `DESIGN.md` - arah desain: identitas, palet UGM dengan alasan, tipografi, ritme, gerak, dial ENERGY 1 / RHYTHM 1 / MOTION 1, daftar yang dihindari dan yang dipertahankan.
- `scripts/dashboard_v2_cli.py` - entry point CLI, otomatis memakai `.venv` proyek.
- `.venv/bin/dashboard-perpus-v2` - wrapper yang dipanggil perintah terminal, plus symlink di `~/.local/bin` supaya bisa dipanggil dari direktori mana pun.

**HTML (5 halaman)**
- Em dash dihapus dari seluruh teks antarmuka.
- Tautan mati `href="#"` dihapus atau diberi tujuan nyata: nav Dashboard menuju `index.html`, nav Alerts menuju `index.html#alerts` (panel Alerts di beri `id="alerts"`), badge "SEGERA" dibuang karena tujuannya kini ada, tautan "Lupa password?" dihapus karena fiturnya tidak ada, breadcrumb jadi teks biasa.
- Pencarian di dashboard yang sebelumnya tidak berfungsi kini benar-benar menyaring kartu area dan tabel (dengan state kosong saat tidak ada hasil).
- Label `aria-label` ditambahkan pada semua tombol ikon: sidebar, mode gelap, notifikasi, keluar, tampilkan password, switch mode gelap di Pengaturan.
- `aria-pressed` pada tombol tema, `aria-expanded` pada tombol notifikasi, `aria-checked` pada switch pengaturan, disinkronkan lewat JS.
- Semua `img` diberi `width` dan `height`.
- Heading dirapikan: label sidebar yang tadinya `h3` jadi `p`, angka statistik dari `h4` jadi `p`, sehingga urutan heading tidak melompat dan hanya ada satu `h1` per halaman.
- State kosong ditambahkan pada grafik analitik.

**CSS**
- `cursor: pointer` untuk semua kontrol aktif, `cursor: not-allowed` untuk yang nonaktif.
- `:focus-visible` dengan outline 2px, biru di tema terang dan emas di tema gelap.
- `prefers-reduced-motion: reduce` mematikan animasi dan transisi.
- Utilitas `.sr-only`.
- Perbaikan kontras: `.text-body` jadi `#5B6B80` di tema terang dan `#AEB7C0` di tema gelap. `.text-golddark` jadi `#7A5C00` di tema terang dan emas terang di tema gelap.

**JS**
- Komentar ber-em dash di `live.js` diganti.
- Filter pencarian `visibleAreaIds()` di `app.js` plus state kosong.
- `analytics.js` menampilkan catatan saat tidak ada event.
- Warna status di `app.js`, `live.js`, `analytics.js`, `settings.js` dinaikkan kontrasnya (`text-emerald-600` jadi `text-emerald-700`, `text-rose-500` jadi `text-rose-600`, plus varian gelap).
- Nomor versi aset dinaikkan (`app.js?v=8`, `live.js?v=6`, `analytics.js?v=5`, `settings.js?v=7`) supaya browser tidak memakai cache lama.

**Backend dan dependency:** tidak diubah. `requirements.txt` tetap. `pytest` 15 test lulus.

### Delivery Gate

Block 1 Hard Gate
- Em dash di teks UI: PASS. `grep` pada semua HTML, CSS, JS menghasilkan nol.
- Overflow mobile: PASS. Diukur pada viewport 390x844 di 4 halaman, `scrollWidth` sama dengan `innerWidth`.
- Statistik tanpa sumber: PASS. Semua angka berasal dari API `events.jsonl`, bukan angka karangan.
- Testimoni fiktif: PASS. Tidak ada bagian testimoni.
- Aset tanpa izin atau placeholder jujur: PASS. Hanya logo UGM dan gambar login yang sudah ada; tidak ada avatar atau logo buatan.
- Tautan nav ke halaman yang tidak ada: PASS. `grep href="#"` nol, semua tujuan nyata.
- Kontras di bawah AA: PASS setelah perbaikan. Audit otomatis seluruh elemen berteks langsung di 4 halaman x 2 tema menyisakan dua temuan pada label merek "PerpusSense" di sidebar, yang terukur 11.86:1 (putih) dan 7.29:1 (emas) di atas `#0D3B54`; temuan itu berasal dari keterbatasan pembacaan latar berlapis di skrip audit, bukan cacat nyata.
- Kontrol tanpa perilaku: PASS. Pencarian, toggle tema, notifikasi, pilih area, terapkan model, ganti pengaturan, keluar, semua diuji dengan klik dan hasilnya diamati.
- State kosong, memuat, error: PASS. Dashboard punya "Belum ada alert" dan "Belum ada notifikasi", analitik punya catatan kosong, login punya pesan error yang muncul saat kredensial salah, live dan settings punya label status memuat.
- FAQ generik: PASS. Tidak ada FAQ.
- Keyboard dan fokus: PASS. Tab menelusuri link nav, kotak pencarian, tombol tema, notifikasi, dan keluar dalam urutan visual; outline 2px terlihat.
- Patching lewat skrip eksternal: PASS. Semua perubahan ditulis langsung ke sumber.
- Satu mode tema rusak: PASS. Kedua tema diuji, tidak ada gaya yang pecah.
- Belum dijalankan: PASS. Server dijalankan lewat `dashboard-perpus-v2` di port 4188 dan seluruh elemen diklik satu per satu.
- Klaim fabrikasi: PASS. Tidak ada klaim keamanan, kepatuhan, atau performa.
- Dibangun tanpa arah: PASS. `DESIGN.md` ada dan dial dinyatakan.
- Placeholder menyamar sebagai data final: PASS.
- Kontrol tanpa nama aksesibel atau state: PASS setelah semua `aria-label`, `aria-pressed`, `aria-expanded`, `aria-checked` ditambahkan.

Block 2 Purpose-Gate
- Gradien dan glow sebagai default: PASS. Gradien hanya di panel gambar login sebagai pelindung keterbacaan, glow hanya denyut emas pada alert kritis.
- Ikon generik: PASS. Semua ikon adalah garis fungsional untuk navigasi dan aksi, tidak ada sparkle, orb, atau robot.
- Tipografi tanpa alasan: PASS. Satoshi dipilih dengan alasan tertulis di `DESIGN.md`.
- Latar grid atau blueprint: PASS. Tidak ada.
- Panah dekoratif di semua tombol: PASS. Tidak ada.
- Badge tanpa fungsi: PASS. Badge hanya untuk LIVE, jumlah alert, status agent, dan status kamera, semuanya status nyata. Badge "SEGERA" yang hanya penanda sudah dihapus.
- Glassmorphism berlebihan: PASS. Tidak ada `backdrop-filter`.
- Bayangan di semua komponen: PASS. Bayangan hanya satu tingkat elevasi kartu.
- Glow di semua elemen: PASS.
- Kartu fitur identik: PASS. Kartu status area mewarisi warna sesuai tingkat kepadatan.
- Animasi template: PASS. Hanya hover, fokus, animasi masuk kartu area, dan denyut alert.
- Ilustrasi generik: PASS. Tidak ada.

Block 3 Liveliness
- Dial dinyatakan: PASS. ENERGY 1 / RHYTHM 1 / MOTION 1, dengan alasan alat kerja operator.
- Konsisten dengan dial: PASS. Ritme seragam dan gerak minimal sesuai klaim.
- Titik fokus per layar: PASS. Angka okupansi utama pada dashboard, grid kamera pada live, grafik pada analitik.
- Whitespace struktural: PASS. Jarak antar seksi lebih besar daripada jarak di dalam kartu.
- Satu aksen sengaja: PASS. Emas hanya untuk status live, menu aktif, dan alert.
- Motif identitas: PASS. Biru dan emas UGM konsisten di sidebar, badge, dan grafik.
- Design Read dinyatakan: PASS. Tertulis di `DESIGN.md`.

Block 4 Craftsmanship dan Quality Locks
- C-1 sampai C-5: PASS. Setiap keputusan punya alasan tertulis, semua kontrol berfungsi, tidak ada seksi pengisi template, UI bertahan di semua state dan tema, tidak ada klaim tanpa bukti.
- R-05 templat AI: PASS. Struktur mengikuti kebutuhan isi dashboard operasional.
- R-11 semua pill: PASS. Radius konsisten 10px, tidak pill.
- R-15 CTA generik: PASS. "Masuk", "Terapkan Default", "Start All", "Stop All", semuanya spesifik.
- R-16 kata buzzword: PASS. Tidak ada.
- R-20 identitas lemah: PASS. Warna dan tipografi institusi, bukan default mesin.
- R-21 mode gelap: PASS. Ada alasan tertulis dan toggle bekerja di kedua arah.
- R-29 palet berlebih: PASS. Dua warna inti plus netral.
- R-30 klon produk lain: PASS. Mengikuti pola dashboard admin yang dikenal, bukan meniru Linear atau Vercel.
- R-31 alasan setiap keputusan: PASS. Tertulis di `DESIGN.md`.

### Cara menjalankan

```bash
dashboard-perpus-v2
```

Lalu buka `http://127.0.0.1:4173/desain-awal-dashboard/login.html` dan masuk
dengan `admin` / `admin123`.

### Catatan sisa

Dua hal yang bukan bagian dari PRD dan tidak dikerjakan: autentikasi masih
sisi klien dan statis (bukan JWT), dan data masih data demo dari
`scripts/seed_demo_events.py`. Keduanya sudah tercatat di README sebagai
kondisi yang belum production-ready.