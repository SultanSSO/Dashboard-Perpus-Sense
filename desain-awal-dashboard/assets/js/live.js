/* Live Monitoring: katalog area plus observation snapshot dari API. */
'use strict';

const LIVE_COLOR = { primary: '#125174', gold: '#F4C542' };
const FALLBACK_CAMERAS = [
  { id: '1.145-CH01', name: 'Communal study area', location: 'DVR-02', status: 'offline', analysis: false },
];

let CCTV_DEVICES = (window.CCTV_CATALOG || FALLBACK_CAMERAS).map(d => ({
  ...d,
  name: d.location === 'Tidak Terdeteksi' ? 'Lokasi belum terpetakan' : d.location,
  location: `${d.device} · ${d.location}`,
}));

const liveState = {
  activeId: CCTV_DEVICES.find(d => d.id === '1.145-CH13')?.id || CCTV_DEVICES[0]?.id,
  filter: 'all',
  query: '',
  muted: {},
  observations: {},
  statuses: {},
  connected: false,
  apiConnected: false,
};
CCTV_DEVICES.forEach(d => { liveState.muted[d.id] = true; });

const $id = id => document.getElementById(id);

const LIVE_REFRESH_MS = 5000;

function formatAge(iso) {
  if (!iso) return '--';
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds} detik lalu`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} menit lalu`;
  return `${Math.floor(minutes / 60)} jam lalu`;
}

function updateActiveAge() {
  const d = CCTV_DEVICES.find(x => x.id === liveState.activeId);
  const observation = d ? cameraObservation(d) : {};
  const updated = $id('active-updated');
  const age = $id('active-age');
  if (updated) updated.textContent = observation.observedAt ? new Date(observation.observedAt).toLocaleString('id-ID') : '--';
  if (age) age.textContent = formatAge(observation.observedAt);
}

function statusStyle(s) {
  return {
    online: { dot: 'bg-emerald-500', badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300', label: 'Online' },
    standby: { dot: 'bg-gold', badge: 'bg-gold/20 text-golddark dark:bg-gold/20 dark:text-gold', label: 'Standby' },
    offline: { dot: 'bg-body', badge: 'bg-slate-200 text-body dark:bg-slate-600/40 dark:text-bodydark', label: 'Offline' },
  }[s] || { dot: 'bg-body', badge: 'bg-slate-200 text-body', label: 'Unknown' };
}

function cameraObservation(d) {
  const obs = liveState.observations[d.id];
  const measurement = obs?.measurement || {};
  const quality = obs?.quality || {};
  const observedAt = obs?.observed_at || null;
  const computedAge = observedAt
    ? Math.max(0, (Date.now() - new Date(observedAt).getTime()) / 1000)
    : null;
  const ageSeconds = Number.isFinite(obs?.age_seconds) ? obs.age_seconds : computedAge;
  const fresh = obs?.fresh === true || (obs?.fresh === undefined && Number.isFinite(ageSeconds) && ageSeconds <= 30);
  return {
    available: Boolean(obs?.available),
    fresh,
    ageSeconds,
    people: Number.isFinite(measurement.person_count) ? measurement.person_count : null,
    chairs: Number.isFinite(measurement.chair_count) ? measurement.chair_count : null,
    observedAt,
    inference: Number.isFinite(quality.inference_seconds) ? Math.round(quality.inference_seconds * 1000) : null,
    quality: quality.stream_ok === false ? 'degraded' : fresh ? 'normal' : obs?.available ? 'stale' : 'unavailable',
  };
}

function setConnectionState() {
  const label = $id('conn-label');
  if (!label) return;
  const detail = liveState.apiConnected
    ? liveState.connected
      ? 'Observation semi-realtime dari Vision Worker'
      : 'Dashboard aktif, tetapi belum ada observation fresh'
    : 'API CCTV belum dapat dihubungi';
  label.textContent = liveState.apiConnected
    ? liveState.connected ? 'Vision Worker live' : 'API terhubung, worker berhenti'
    : 'Backend CCTV offline';
  label.title = detail;
  const dot = $id('conn-dot');
  if (dot) {
    dot.className = 'h-1.5 w-1.5 shrink-0 rounded-full '
      + (!liveState.apiConnected ? 'bg-rose-500' : liveState.connected ? 'bg-emerald-400' : 'bg-gold');
  }
}

function renderGrid() {
  const grid = $id('cctv-grid');
  const q = liveState.query.toLowerCase();
  const visible = CCTV_DEVICES.filter(d =>
    (liveState.filter === 'all' || d.status === liveState.filter) &&
    (d.name.toLowerCase().includes(q) || d.location.toLowerCase().includes(q) || d.id.toLowerCase().includes(q))
  );

  $id('cctv-count').textContent = `${visible.length} dari ${CCTV_DEVICES.length} kamera`;
  $id('analysis-count').textContent = `${CCTV_DEVICES.filter(d => d.analysis).length} kamera dianalisis Vision Agent`;
  $id('cctv-empty').classList.toggle('hidden', visible.length !== 0);
  grid.classList.toggle('hidden', visible.length === 0);

  grid.innerHTML = visible.map(d => {
    const st = statusStyle(d.status);
    const active = d.id === liveState.activeId;
    const observation = cameraObservation(d);
    const aiBadge = d.analysis
      ? '<span class="rounded-sm bg-primary px-2 py-1 text-[9px] font-bold text-white dark:bg-gold dark:text-primarydk">AI ACTIVE</span>'
      : '<span class="rounded-sm bg-white/10 px-2 py-1 text-[9px] font-bold text-white/70">Katalog</span>';
    const title = d.status === 'offline'
      ? 'Kamera offline'
      : d.analysis && observation.fresh
        ? `${observation.people} orang terdeteksi`
        : d.analysis && observation.available
          ? `Hasil terakhir: ${observation.people ?? '--'} orang`
          : d.analysis ? 'Menunggu snapshot' : 'Belum masuk scope analisis';
    const detail = d.status === 'offline'
      ? 'Health event menunggu reconnect'
      : d.analysis && observation.fresh
        ? `fresh · ${observation.inference ?? '--'} ms`
        : d.analysis && observation.available
          ? `stale · ${formatAge(observation.observedAt)}`
          : d.analysis ? 'Belum ada observation terbaru' : 'Katalog kamera';
    return `
    <div class="cctv-tile group cursor-pointer overflow-hidden rounded-sm border bg-white shadow-default transition dark:bg-boxdark
        ${active ? 'border-primary ring-2 ring-primary/30 dark:border-gold dark:ring-gold/30' : 'border-stroke dark:border-strokedark hover:border-primary/50 dark:hover:border-gold/50'}"
        data-id="${d.id}" onclick="selectTile('${d.id}')">
      <div class="relative aspect-video bg-gradient-to-br from-primarydk to-[#0a2c40]">
        <div class="absolute inset-0 flex flex-col items-center justify-center px-4 text-center">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="rgba(174,183,192,.7)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
          <p class="mt-2 text-xs font-bold text-bodydark">${title}</p>
          <p class="mt-0.5 text-[10px] font-medium text-bodydark/70">${detail}</p>
        </div>
        <div class="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/70 to-transparent px-3 pb-2.5 pt-8 opacity-0 transition group-hover:opacity-100">
          <span class="flex items-center gap-1.5 text-[10px] font-bold text-white"><span class="relative flex h-2 w-2"><span class="absolute inline-flex h-full w-full animate-ping rounded-full ${st.dot} opacity-75"></span><span class="relative inline-flex h-2 w-2 rounded-full ${st.dot}"></span></span>${st.label}</span>
          <div class="flex items-center gap-1.5">${aiBadge}<button onclick="event.stopPropagation(); openFocus('${d.id}')" title="Perbesar kamera" aria-label="Perbesar kamera ${d.id}" class="flex h-11 min-w-[44px] items-center justify-center gap-1 rounded-sm bg-white/15 px-2 text-[10px] font-bold text-white hover:bg-white/30">Fokus</button></div>
        </div>
      </div>
      <div class="flex items-center justify-between gap-3 px-4 py-3">
        <div class="min-w-0"><p class="truncate text-sm font-bold text-black dark:text-white">${d.id}</p><p class="truncate text-[11px] font-medium text-body">${d.name} · ${d.device}</p></div>
        <span class="shrink-0 rounded-sm px-2 py-1 text-[10px] font-bold ${st.badge}">${st.label}</span>
      </div>
    </div>`;
  }).join('');
  renderActivePanel();
}

function renderActivePanel() {
  const d = CCTV_DEVICES.find(x => x.id === liveState.activeId) || CCTV_DEVICES[0];
  if (!d) return;
  const st = statusStyle(d.status);
  const observation = cameraObservation(d);
  $id('active-name').textContent = d.id;
  $id('active-location').textContent = d.name;
  $id('active-id').textContent = d.location;
  $id('active-status').innerHTML = `<span class="h-2 w-2 rounded-full ${st.dot}"></span> ${st.label}`;
  const message = d.status === 'offline'
    ? 'Kamera offline'
    : observation.fresh
      ? `${observation.people} orang · semi-realtime`
      : observation.available
        ? `Hasil terakhir: ${observation.people ?? '--'} orang`
        : d.analysis ? 'Menunggu snapshot hasil analisis' : 'Kamera belum masuk scope analisis';
  const detail = observation.fresh
    ? `Vision Worker · fresh · ${observation.inference ?? '--'} ms`
    : observation.available
      ? `Data stale · ${formatAge(observation.observedAt)} · jalankan worker untuk data terkini`
      : d.analysis ? 'Belum ada event terbaru untuk kamera ini' : 'Kamera berada di katalog, belum dianalisis oleh worker';
  const snapshotUrl = observation.fresh
    ? `/api/v1/cameras/${encodeURIComponent(d.id)}/snapshot?ts=${encodeURIComponent(observation.observedAt || Date.now())}`
    : '';
  $id('active-viewport').innerHTML = `
    ${snapshotUrl ? `<img src="${snapshotUrl}" alt="Snapshot ${d.id}" class="h-full w-full object-contain" onerror="this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden')">` : ''}
    <div class="${snapshotUrl ? 'hidden ' : ''}absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-primarydk to-[#0a2c40] px-4 text-center">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="rgba(174,183,192,.7)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
      <p class="mt-3 text-2xl font-bold text-white">${message}</p>
      <p class="mt-2 text-base font-medium text-bodydark">${detail}</p>
    </div>
    <div class="absolute bottom-0 left-0 right-0 flex items-center justify-between bg-black/70 px-5 py-3 text-base text-white">
      <span class="font-bold">${message}</span>
      <span class="text-sm">${observation.observedAt ? new Date(observation.observedAt).toLocaleString('id-ID') : 'Belum ada update'}</span>
    </div>`;
  updateActiveAge();
}

function selectTile(id) { liveState.activeId = id; renderGrid(); }
function openFocus(id) { liveState.activeId = id; renderGrid(); $id('active-panel').scrollIntoView({ behavior: 'smooth', block: 'center' }); }
function setFilter(f, btn) {
  liveState.filter = f;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.className = 'filter-btn flex min-h-[44px] items-center rounded-sm px-4 text-xs font-bold text-body transition hover:text-primary dark:hover:text-gold';
    b.setAttribute('aria-pressed', 'false');
  });
  btn.className = 'filter-btn flex min-h-[44px] items-center rounded-sm bg-primary px-4 text-xs font-bold text-white dark:bg-gold dark:text-primarydk';
  btn.setAttribute('aria-pressed', 'true');
  renderGrid();
}

function renderStats() {
  $id('count-online').textContent = CCTV_DEVICES.filter(d => d.status === 'online').length;
  $id('count-standby').textContent = CCTV_DEVICES.filter(d => d.status === 'standby').length;
  $id('count-offline').textContent = CCTV_DEVICES.filter(d => d.status === 'offline').length;
  $id('count-total').textContent = CCTV_DEVICES.length;
  $id('analysis-count').textContent = `${CCTV_DEVICES.filter(d => d.analysis).length} kamera dianalisis Vision Agent`;
}

async function refreshLiveData() {
  try {
    const overview = await VisionApi.get('/overview');
    liveState.apiConnected = true;
    liveState.connected = overview.health?.live_worker?.connected === true;
    liveState.observations = overview.observations || {};
    liveState.statuses = overview.statuses || {};
    const catalogById = new Map((overview.catalog?.items || []).map(item => [item.camera_id, item]));
    CCTV_DEVICES = CCTV_DEVICES.map(d => {
      const item = catalogById.get(d.id);
      const status = liveState.statuses[d.id];
      const operational = item?.operational_status;
      const nextStatus = operational === 'inactive'
        ? 'offline'
        : status?.stream_status === 'online'
          ? 'online'
          : item?.analysis_enabled ? 'standby' : d.status;
      return { ...d, analysis: Boolean(item?.analysis_enabled ?? d.analysis), status: nextStatus };
    });
  } catch (error) {
    liveState.apiConnected = false;
    liveState.connected = false;
  }
  setConnectionState();
  renderStats();
  renderGrid();
}

$id('cctv-search').addEventListener('input', e => { liveState.query = e.target.value; renderGrid(); });
document.addEventListener('DOMContentLoaded', () => {
  renderStats();
  renderGrid();
  refreshLiveData();
  setInterval(refreshLiveData, LIVE_REFRESH_MS);
  setInterval(updateActiveAge, 1000);
});
