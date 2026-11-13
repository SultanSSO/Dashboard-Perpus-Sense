# DESIGN.md: PerpusSense Dashboard

Arah desain untuk dashboard okupansi Perpustakaan UGM. Dokumen ini adalah
sumber arah (identitas, palet, tipografi, ritme). Filter anti-slop diterapkan
di atasnya, bukan menggantikannya.

## Perubahan spesifik pada kode

- card yang kamu modifikasi sebelumnya kembalikan ke tema awal.

- buat tulisan di bawah bagian menu dashboard <p class="text-[11px] font-medium leading-snug text-bodydark" id="conn-label" title="Dashboard aktif, tetapi observation lama tidak dihitung sebagai kondisi saat ini">API terhubung, worker berhenti</p> dan live monitoring <div class="flex items-center gap-2">
        <span id="conn-dot" class="h-2 w-2 shrink-0 rounded-full bg-gold"></span>
        <p class="text-[11px] font-medium leading-snug text-bodydark" id="conn-label" title="Dashboard aktif, tetapi belum ada observation fresh">API terhubung, worker berhenti</p>
      </div> seperti code ini <div class="rounded-sm border border-white/10 bg-white/5 p-4">
        <div class="flex items-center gap-2">
          <p class="text-xs font-bold uppercase tracking-wide text-gold">Backend CCTV</p>
        </div>
        <p class="mt-1.5 text-[11px] leading-snug text-bodydark">Riwayat event aktual dari Vision Worker</p>
      </div>



