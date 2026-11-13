/* =====================================================================
 * PerpusSense Dashboard, data plane dari Dashboard API.
 * Model data: status observasi PER AREA CCTV.
 * Hermes menerima event terstruktur; dashboard tidak menerima frame mentah.
 * ===================================================================== */

'use strict';

/* ---------------- Palet ---------------- */
const COLOR = {
  primary:  '#125174',
  primaryLt:'#3E7CA1',
  gold:     '#F4C542',
  goldDk:   '#C99E1F',
  green:    '#10B981',
  greenDk:  '#059669',
  body:     '#5B6B80',
  bodyDark: '#AEB7C0',
  grid:     '#E2E8F0',
  gridDark: '#2E3A47',
  text:     '#1C2434',
  textDark: '#EEF2F7',
};

/* ---------------- Katalog area CCTV (per alamat) ---------------- */
/* Fase 2: daftar ini diisi dari GET /api/v1/devices. */
const ANALYSIS_CATALOG = window.VISION_ANALYSIS_CAMERAS || [
  { id: '1.145-CH01', name: 'Communal study area', purpose: 'Okupansi' },
  { id: '1.145-CH02', name: 'Communal study area', purpose: 'Okupansi, kepadatan' },
  { id: '1.145-CH03', name: 'Individual Study Station', purpose: 'Okupansi' },
  { id: '1.145-CH05', name: 'Communal study area', purpose: 'Okupansi, kandidat RoI kursi' },
  { id: '1.145-CH07', name: 'Communal study area', purpose: 'Okupansi' },
  { id: '1.145-CH13', name: 'Pintu masuk utama', purpose: 'Trafik' },
  { id: '1.145-CH15', name: 'Pelataran Utama', purpose: 'Trafik' },
];
const AREAS = ANALYSIS_CATALOG.map((camera, index) => ({
  id: camera.id,
  name: camera.name,
  purpose: camera.purpose,
  status: index === 5 ? 'standby' : 'online',
}));

const CONFIG = {
  intervalSeconds: 5,
  chartMaxPoints: 30,
  modelName: 'yolo11n.pt',
  deviceName: 'CPU / target GPU host',
};


/* ---------------- State ---------------- */
// Tema: prioritas = ?force=light|dark > localStorage > prefers-color-scheme
const _qTheme = new URLSearchParams(location.search).get('force');
const _savedTheme = localStorage.getItem('perpus-theme');
const state = {
  areas: {},          // id -> current observation per monitored camera
  areaOrder: AREAS.map(a => a.id),
  activeId: null,     // area yang tampil di panel snapshot
  history: [],        // agregat total [{t, rate, persons, occupied, empty, total}]
  alerts: [],
  alertLevels: {},
  healthStates: {},
  events: [],
  tasks: [
    { id: 'TASK-001', name: 'Occupancy monitoring · 7 kamera', status: 'RUNNING', detail: 'Observation tiap 5 detik' },
    { id: 'TASK-002', name: 'Camera health watch', status: 'RUNNING', detail: 'Reconnect dan degraded state' },
    { id: 'TASK-003', name: 'Daily occupancy report', status: 'SCHEDULED', detail: 'Ringkasan pukul 21.00' },
  ],
  agent: { hermes: 'Terhubung', rules: 'Aktif', worker: '7 kamera', model: 'YOLO11n · CPU' },
  lastEvent: null,
  query: '',          // filter pencarian area (nama atau id kamera)
  dark: _qTheme ? _qTheme === 'dark'
       : _savedTheme ? _savedTheme === 'dark'
       : window.matchMedia('(prefers-color-scheme: dark)').matches,
};


/* Klasifikasi status hanya jika backend menyediakan occupancy_rate. */
function crowdStatus(rate) {
  if (!Number.isFinite(rate)) return { key: 'unknown', label: 'Belum tersedia', color: 'slate' };
  if (rate >= 0.66) return { key: 'padat', label: 'Padat', color: 'rose' };
  if (rate >= 0.33) return { key: 'sedang', label: 'Sedang', color: 'amber' };
  return { key: 'kosong', label: 'Kosong', color: 'emerald' };
}

/* =====================================================================
 *  DATA PLANE, observation aktual dari dashboard API
 * ===================================================================== */
async function handleOccupancyEvent() {
  try {
    const overview = await VisionApi.get('/overview');
    const workerLive = overview.health?.live_worker?.connected === true;
    const connLabel = $('conn-label');
    const connDetail = workerLive
      ? 'Observation semi-realtime dari Vision Worker'
      : 'Dashboard aktif, tetapi observation lama tidak dihitung sebagai kondisi saat ini';
    if (connLabel) {
      connLabel.textContent = workerLive ? 'Vision Worker live' : 'API terhubung, worker berhenti';
      connLabel.title = connDetail;
    }
    const dot = $('conn-dot');
    if (dot) dot.className = `h-1.5 w-1.5 shrink-0 rounded-full ${workerLive ? 'bg-emerald-400' : 'bg-gold'}`;
    const cameras = overview.analysis_cameras || [];
    const observations = overview.observations || {};
    const statuses = overview.statuses || {};
    state.areaOrder = cameras.map(camera => camera.camera_id);
    state.areas = {};
    cameras.forEach(camera => {
      const cameraId = camera.camera_id;
      const observation = observations[cameraId] || {};
      const measurement = observation.measurement || {};
      const status = statuses[cameraId] || {};
      const fresh = observation.fresh === true && status.stream_status === 'online';
      state.areas[cameraId] = {
        id: cameraId,
        name: camera.location || camera.description || cameraId,
        purpose: camera.analysis_purpose || 'Okupansi',
        status: fresh ? 'online' : observation.available ? 'stale' : 'standby',
        fresh,
        age_seconds: observation.age_seconds,
        occupancy: fresh && Number.isFinite(measurement.occupancy_rate) ? measurement.occupancy_rate : null,
        persons: fresh && Number.isFinite(measurement.person_count) ? measurement.person_count : null,
        last_persons: Number.isFinite(measurement.person_count) ? measurement.person_count : null,
        updated: observation.observed_at || null,
        inference_ms: fresh && Number.isFinite(observation.quality?.inference_seconds)
          ? Math.round(observation.quality.inference_seconds * 1000) : null,
        model: camera.vision_profile || 'Vision profile',
        ground_truth: Boolean(observation.ground_truth),
      };
    });
    if (!state.activeId || !state.areas[state.activeId]) {
      const onlineId = state.areaOrder.find(id => state.areas[id].status === 'online');
      state.activeId = onlineId || state.areaOrder[0];
    }

    const list = state.areaOrder.map(id => state.areas[id]);
    const rates = list.map(a => a.occupancy).filter(Number.isFinite);
    const avgRate = rates.length ? rates.reduce((sum, value) => sum + value, 0) / rates.length : null;
    const totalPersons = list.reduce((sum, area) => sum + (Number.isFinite(area.persons) ? area.persons : 0), 0);
    const timestamp = overview.generated_at;
    state.lastEvent = { timestamp };
    state.history.push({
      t: new Date(timestamp),
      rate: Number.isFinite(avgRate) ? +(avgRate * 100).toFixed(1) : null,
      persons: totalPersons,
      padat: list.filter(a => crowdStatus(a.occupancy).key === 'padat').length,
      kosong: list.filter(a => crowdStatus(a.occupancy).key === 'kosong').length,
      total: list.length,
    });
    if (state.history.length > CONFIG.chartMaxPoints) state.history.shift();

    const sourceEvents = overview.events || [];
    state.alerts = (overview.alerts || []).map(alert => ({
      level: alert.severity || 'warning',
      message: `${alert.source?.camera_id || 'CCTV'} · ${alert.measurement?.person_count ?? '--'} orang, batas ${alert.measurement?.threshold ?? '--'}`,
      ts: alert.opened_at || alert.observed_at || timestamp,
      timeMs: new Date(alert.opened_at || alert.observed_at || timestamp).getTime(),
    }));
    state.events = sourceEvents.slice(0, 30).map(event => ({
      type: event.event_type || 'VISION_EVENT',
      message: `${event.source?.camera_id || 'CCTV'} · ${event.measurement?.person_count ?? '--'} orang`,
      ts: event.observed_at || timestamp,
      level: event.severity || 'info',
    }));
    const tasks = overview.tasks || [];
    state.tasks = tasks.map(task => ({
      id: task.task_id,
      name: task.name,
      status: task.status,
      detail: task.goal || task.type || 'Task backend',
    }));
    state.agent = {
      hermes: overview.health?.live_worker?.connected ? 'Observation aktual' : 'Menunggu worker',
      rules: `${tasks.filter(task => task.status === 'RUNNING').length} task aktif`,
      worker: `${cameras.length} kamera`,
      model: `${overview.health?.vision_config?.model || 'YOLO'} · ${overview.health?.vision_config?.device || 'CPU'}`,
    };
    renderAll();
  } catch (error) {
    const connLabel = $('conn-label');
    if (connLabel) {
      connLabel.textContent = 'Backend CCTV offline';
      connLabel.title = 'API CCTV belum dapat dihubungi';
    }
    const dot = $('conn-dot');
    if (dot) dot.className = 'h-1.5 w-1.5 shrink-0 rounded-full bg-rose-500';
    state.agent.hermes = 'Backend offline';
    state.agent.rules = 'Tidak tersedia';
    renderAgentPanels();
  }
}
/* =====================================================================
 *  RENDER
 * ===================================================================== */
const $ = id => document.getElementById(id);
const fmtTime = d => d ? new Date(d).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--';
let charts = { line: null, donut: null };

function renderAll() {
  renderStats();
  renderCharts();
  renderAreaCards();
  renderAreaTable();
  renderSnapshot();
  renderAgentPanels();
  renderAlerts();
  renderNotifs();
}

/* --- Stat cards (agregat seluruh area) --- */
function renderStats() {
  const list = state.areaOrder.map(id => state.areas[id]);
  const rates = list.map(a => a.occupancy).filter(Number.isFinite);
  const avg = rates.length ? rates.reduce((sum, value) => sum + value, 0) / rates.length : null;
  const persons = list.reduce((sum, area) => sum + (Number.isFinite(area.persons) ? area.persons : 0), 0);
  const online = list.filter(a => a.status === 'online').length;

  $('stat-total').textContent = list.length;
  $('stat-occupied').textContent = persons;
  $('stat-empty').textContent = online;
  $('stat-rate').textContent = Number.isFinite(avg) ? (avg * 100).toFixed(1) : '--';

  const h = state.history;
  if (h.length >= 2) {
    const prev = h[h.length - 2], curr = h[h.length - 1];
    setTrend('trend-occupied', curr.persons - prev.persons, true);
    setTrend('trend-empty', curr.padat - prev.padat, false);
    if (Number.isFinite(curr.rate) && Number.isFinite(prev.rate)) {
      setTrend('trend-rate', +(curr.rate - prev.rate).toFixed(1), true, '%');
    }
  }
}
function setTrend(id, diff, upIsGood, unit = '') {
  const el = $(id);
  const up = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`;
  const dn = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>`;
  const good = upIsGood ? diff >= 0 : diff <= 0;
  const cls = good ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400';
  if (diff === 0) { el.className = 'flex items-center gap-1 text-sm font-medium text-body'; el.innerHTML = 'stabil'; return; }
  el.className = `flex items-center gap-1 text-sm font-medium ${cls}`;
  el.innerHTML = `${diff > 0 ? up : dn} ${Math.abs(diff)}${unit}`;
}

/* --- Charts (agregat) --- */
function renderCharts() {
  // Format jam pendek, contoh: 15.01 (HH.MM)
  const labels = state.history.map(p => p.t.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace(':', '.'));
  const rates = state.history.map(p => p.rate);
  const persons = state.history.map(p => p.persons);
  const dark = state.dark;
  const axisColor = dark ? COLOR.bodyDark : COLOR.body;
  const gridColor = dark ? COLOR.gridDark : COLOR.grid;

  const lineOpts = {
    chart: { type: 'area', height: 310, toolbar: { show: false }, background: 'transparent',
             fontFamily: 'Satoshi, Inter, sans-serif', animations: { dynamicAnimation: { speed: 400 } } },
    theme: { mode: dark ? 'dark' : 'light' },
    stroke: { curve: 'smooth', width: [2.5, 2] },
    fill: { type: ['gradient', 'solid'], gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.02 } },
    colors: [COLOR.green, COLOR.gold],
    series: [ { name: 'Okupansi %', data: rates }, { name: 'Orang', data: persons } ],
    xaxis: { categories: labels, labels: { style: { colors: axisColor } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: [ { max: 100, labels: { style: { colors: axisColor }, formatter: v => v + '%' } },
             { opposite: true, labels: { style: { colors: axisColor } } } ],
    grid: { borderColor: gridColor, strokeDashArray: 4 },
    legend: { show: false }, dataLabels: { enabled: false }, tooltip: { theme: dark ? 'dark' : 'light' },
  };
  if (!charts.line) { charts.line = new ApexCharts($('chart-occupancy'), lineOpts); charts.line.render(); }
  else {
    charts.line.updateOptions({ theme: { mode: dark ? 'dark' : 'light' }, xaxis: lineOpts.xaxis, yaxis: lineOpts.yaxis, grid: lineOpts.grid }, false, false);
    charts.line.updateSeries(lineOpts.series);
  }

  // Donut: distribusi status area (Padat/Sedang/Kosong)
  const list = state.areaOrder.map(id => state.areas[id]);
  const nPadat = list.filter(a => crowdStatus(a.occupancy).key === 'padat').length;
  const nSedang = list.filter(a => crowdStatus(a.occupancy).key === 'sedang').length;
  const nKosong = list.filter(a => crowdStatus(a.occupancy).key === 'kosong').length;
  const donutOpts = {
    chart: { type: 'donut', height: 250, background: 'transparent', fontFamily: 'Satoshi, Inter, sans-serif' },
    theme: { mode: dark ? 'dark' : 'light' },
    series: [nPadat, nSedang, nKosong],
    labels: ['Padat', 'Sedang', 'Kosong'],
    colors: ['#F43F5E', COLOR.gold, '#10B981'],
    legend: { position: 'bottom', labels: { colors: axisColor }, markers: { radius: 4 } },
    dataLabels: { enabled: false },
    plotOptions: { pie: { donut: { size: '72%', labels: {
      show: true,
      name: { fontSize: '12px', color: axisColor },
      value: { fontSize: '26px', fontWeight: 700, color: dark ? COLOR.textDark : COLOR.text },
      total: { show: true, label: 'Area', fontSize: '12px', color: axisColor, formatter: () => list.length + ' area' },
    } } } },
    stroke: { width: 0 },
  };
  if (!charts.donut) { charts.donut = new ApexCharts($('chart-donut'), donutOpts); charts.donut.render(); }
  else {
    charts.donut.updateOptions({ theme: { mode: dark ? 'dark' : 'light' }, plotOptions: donutOpts.plotOptions, legend: donutOpts.legend }, false, false);
    charts.donut.updateSeries(donutOpts.series);
  }
  $('donut-occupied').textContent = nPadat;
  $('donut-empty').textContent = nKosong;
}

/* --- Kartu per area CCTV --- */
/* --- Filter pencarian: nama area atau id kamera --- */
function visibleAreaIds() {
  const q = state.query.trim().toLowerCase();
  if (!q) return state.areaOrder;
  return state.areaOrder.filter(id => {
    const a = state.areas[id] || {};
    const name = (a.name || '').toLowerCase();
    return name.includes(q) || id.toLowerCase().includes(q);
  });
}

function renderAreaCards() {
  const toneMap = {
    rose:    { ring: 'border-rose-200 bg-rose-50 dark:border-rose-500/30 dark:bg-rose-500/10', bar: 'bg-rose-500', txt: 'text-rose-700 dark:text-rose-400', badge: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300' },
    amber:   { ring: 'border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10', bar: 'bg-gold', txt: 'text-golddark dark:text-gold', badge: 'bg-gold/20 text-golddark dark:bg-gold/20 dark:text-gold' },
    emerald: { ring: 'border-emerald-200 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/10', bar: 'bg-emerald-500', txt: 'text-emerald-700 dark:text-emerald-400', badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' },
    slate:   { ring: 'border-slate-200 bg-slate-50 dark:border-slate-500/30 dark:bg-slate-500/10', bar: 'bg-slate-400', txt: 'text-slate-600 dark:text-slate-300', badge: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300' },
  };
  const ids = visibleAreaIds();
  if (!ids.length) {
    $('seat-grid').innerHTML = `<p class="col-span-full rounded-sm border border-dashed border-stroke px-4 py-8 text-center text-sm font-medium text-body dark:border-strokedark">Tidak ada area yang cocok dengan pencarian.</p>`;
    $('seatmap-updated').textContent = fmtTime(state.lastEvent?.timestamp);
    return;
  }
  $('seat-grid').innerHTML = ids.map(id => {
    const a = state.areas[id];
    const cs = crowdStatus(a.occupancy);
    const tone = toneMap[cs.color];
    const active = id === state.activeId;
    const pct = Number.isFinite(a.occupancy) ? (a.occupancy * 100).toFixed(0) : '--';
    return `
      <button type="button" onclick="selectArea('${id}')"
        class="seat-card relative overflow-hidden rounded-sm border p-4 text-left transition hover:-translate-y-0.5
          ${tone.ring} ${active ? 'ring-2 ring-primary/40 dark:ring-gold/40' : ''}">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="truncate text-sm font-bold text-black dark:text-white">${a.name}</p>
            <p class="mt-0.5 text-[10px] font-medium uppercase tracking-wide text-body">${a.id}</p>
          </div>
          ${active ? '<span class="shrink-0 rounded-sm bg-primary px-1.5 py-0.5 text-[9px] font-bold text-white dark:bg-gold dark:text-primarydk">DIPILIH</span>' : ''}
        </div>
        <div class="mt-3 flex items-end justify-between">
          <p class="text-2xl font-bold ${tone.txt}">${pct}<span class="text-sm">%</span></p>
          <span class="rounded-sm px-2 py-0.5 text-[11px] font-bold ${tone.badge}">${cs.label}</span>
        </div>
        <div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
          <div class="h-full rounded-full ${tone.bar}" style="width:${Number.isFinite(a.occupancy) ? pct : 0}%"></div>
        </div>
        <p class="mt-2 text-[10px] font-medium text-body">${a.fresh ? `${a.persons} orang · live` : a.updated ? `Hasil terakhir ${a.last_persons ?? '--'} orang · stale` : 'Belum ada data'} </p>
      </button>`;
  }).join('');
  $('seatmap-updated').textContent = fmtTime(state.lastEvent?.timestamp);
}

/* --- Tabel per area --- */
function renderAreaTable() {
  const ids = visibleAreaIds();
  if (!ids.length) {
    $('chair-table').innerHTML = `<tr><td colspan="5" class="py-6 text-center text-sm font-medium text-body">Tidak ada area yang cocok dengan pencarian.</td></tr>`;
    return;
  }
  $('chair-table').innerHTML = ids.map(id => {
    const a = state.areas[id];
    const cs = crowdStatus(a.occupancy);
    const badgeCls = { rose: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300',
                       amber: 'bg-gold/20 text-golddark dark:bg-gold/20 dark:text-gold',
                       emerald: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
                       slate: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300' }[cs.color];
    const occupancy = Number.isFinite(a.occupancy) ? `${(a.occupancy * 100).toFixed(0)}%` : '--';
    return `
      <tr class="cursor-pointer hover:bg-whiter dark:hover:bg-boxdark-2" tabindex="0" role="button"
          aria-label="Pilih area ${a.name}"
          onclick="selectArea('${id}')"
          onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectArea('${id}');}">
        <td class="py-3 pr-4 font-bold text-black dark:text-white">${a.name}</td>
        <td class="py-3 pr-4"><span class="badge ${badgeCls}">${cs.label}</span></td>
        <td class="py-3 pr-4 font-medium">${occupancy}</td>
        <td class="py-3 pr-4 font-medium">${Number.isFinite(a.persons) ? a.persons : '--'}</td>
        <td class="py-3 text-xs font-medium text-body">${fmtTime(a.updated)}</td>
      </tr>`;
  }).join('');
}

/* --- Panel Live Snapshot (area yang dipilih / acak) --- */
function renderSnapshot() {
  const a = state.areas[state.activeId];
  if (!a) return;
  const cs = crowdStatus(a.occupancy);
  $('snap-name').textContent = a.name;
  $('snap-id').textContent = a.id;
  $('snap-status').textContent = cs.label;
  $('snap-occupancy').textContent = Number.isFinite(a.occupancy) ? (a.occupancy * 100).toFixed(0) + '%' : '--';
  $('snap-updated').textContent = fmtTime(a.updated);
}

/* --- Pilih area (klik kartu / baris tabel) --- */
function selectArea(id) {
  state.activeId = id;
  renderAreaCards();
  renderAreaTable();
  renderSnapshot();
  const panel = document.getElementById('snapshot-panel');
  if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* --- Alerts --- */
function pushAlert(level, message, ts) {
  const last = state.alerts[0];
  if (last && last.message === message && (Date.now() - last.timeMs) < 30000) return;
  state.alerts.unshift({ level, message, ts, timeMs: Date.now() });
  if (state.alerts.length > 20) state.alerts.pop();
  renderAlerts(); renderNotifs();
}
function renderAlerts() {
  const list = $('alerts-list');
  $('alerts-count').textContent = `${state.alerts.length} alert`;
  if (!state.alerts.length) {
    list.innerHTML = `<li class="rounded-sm bg-whiter p-4 text-center text-xs font-medium text-body dark:bg-boxdark-2">Belum ada alert. Sistem berjalan normal.</li>`;
    return;
  }
  const styles = {
    warning:  'border-l-4 border-gold bg-gold/10 text-golddark dark:text-gold',
    critical: 'alert-critical border-l-4 border-primary bg-primary/10 text-primary dark:text-primaryLt',
    info:     'border-l-4 border-body bg-whiter text-body dark:bg-boxdark-2',
  };
  list.innerHTML = state.alerts.map(a => `
    <li class="rounded-sm p-3.5 text-xs ${styles[a.level] || styles.info}">
      <p class="font-bold leading-snug">${a.message}</p>
      <p class="mt-1 font-medium opacity-70">${fmtTime(a.ts)}</p>
    </li>`).join('');
}
function renderNotifs() {
  const badge = $('notif-badge'), sideBadge = $('sidebar-alert-badge');
  const n = state.alerts.length;
  [badge, sideBadge].forEach(el => { el.textContent = n; el.classList.toggle('hidden', n === 0); });
  badge.classList.toggle('flex', n > 0);
  $('notif-list').innerHTML = n === 0
    ? `<li class="px-5 py-6 text-center text-xs text-body">Belum ada notifikasi</li>`
    : state.alerts.slice(0, 8).map(a => `
      <li class="notif-item px-5 py-3.5">
        <p class="text-xs font-bold leading-snug text-black dark:text-white">${a.message}</p>
        <p class="mt-0.5 text-[10px] font-medium text-body">${fmtTime(a.ts)}</p>
      </li>`).join('');
}

/* --- Vision Agent panels --- */
function renderAgentPanels() {
  if (!$('agent-status-badge')) return;
  $('agent-status-badge').textContent = state.agent.hermes === 'Backend offline' ? 'Offline' : 'Terhubung API';
  $('agent-hermes').textContent = state.agent.hermes;
  $('agent-rules').textContent = state.agent.rules;
  $('agent-worker').textContent = state.agent.worker;
  $('agent-model').textContent = state.agent.model;

  $('task-count').textContent = `${state.tasks.length} task`;
  $('task-list').innerHTML = state.tasks.map(task => `
    <li class="rounded-sm border-l-4 ${task.status === 'RUNNING' ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10' : 'border-gold bg-gold/10'} px-3.5 py-3">
      <div class="flex items-start justify-between gap-2">
        <p class="text-xs font-bold text-black dark:text-white">${task.name}</p>
        <span class="shrink-0 text-[9px] font-bold tracking-wide ${task.status === 'RUNNING' ? 'text-emerald-700 dark:text-emerald-300' : 'text-golddark dark:text-gold'}">${task.status}</span>
      </div>
      <p class="mt-1 text-[10px] font-medium text-body">${task.id} · ${task.detail}</p>
    </li>`).join('');

  const recent = state.events.slice(0, 5);
  $('event-count').textContent = `${state.events.length} event`;
  $('event-list').innerHTML = recent.length
    ? recent.map(event => `
      <li class="rounded-sm bg-whiter px-3.5 py-3 dark:bg-boxdark-2">
        <div class="flex items-start justify-between gap-2">
          <p class="text-xs font-bold text-black dark:text-white">${event.message}</p>
          <span class="shrink-0 text-[9px] font-bold text-body">${event.level.toUpperCase()}</span>
        </div>
        <p class="mt-1 text-[10px] font-medium text-body">${event.type} · ${fmtTime(event.ts)}</p>
      </li>`).join('')
    : `<li class="rounded-sm bg-whiter p-4 text-center text-xs font-medium text-body dark:bg-boxdark-2">Belum ada event.</li>`;
}

/* =====================================================================
 *  UI INTERACTIONS
 * ===================================================================== */
function applyDark() {
  document.documentElement.classList.toggle('dark', state.dark);
  $('icon-moon').classList.toggle('hidden', state.dark);
  $('icon-sun').classList.toggle('hidden', !state.dark);
  const darkBtn = $('btn-dark');
  if (darkBtn) darkBtn.setAttribute('aria-pressed', String(state.dark));
  if (charts.line) renderCharts();
}
$('btn-dark').addEventListener('click', () => {
  state.dark = !state.dark;
  localStorage.setItem('perpus-theme', state.dark ? 'dark' : 'light');
  applyDark();
});

$('btn-sidebar').addEventListener('click', () => {
  $('sidebar').classList.toggle('-translate-x-full');
  $('sidebar-overlay').classList.toggle('hidden');
});
$('sidebar-overlay').addEventListener('click', () => {
  $('sidebar').classList.add('-translate-x-full');
  $('sidebar-overlay').classList.add('hidden');
});

$('btn-notif').addEventListener('click', e => {
  e.stopPropagation();
  const dd = $('notif-dropdown');
  dd.classList.toggle('hidden');
  $('btn-notif').setAttribute('aria-expanded', String(!dd.classList.contains('hidden')));
});
document.addEventListener('click', e => {
  const dd = $('notif-dropdown');
  if (!dd.contains(e.target)) {
    dd.classList.add('hidden');
    $('btn-notif').setAttribute('aria-expanded', 'false');
  }
});
/* Escape menutup dropdown notifikasi, sama seperti klik di luar. */
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const dd = $('notif-dropdown');
  if (!dd || dd.classList.contains('hidden')) return;
  dd.classList.add('hidden');
  $('btn-notif').setAttribute('aria-expanded', 'false');
  $('btn-notif').focus();
});
$('btn-clear-notif').addEventListener('click', () => { state.alerts = []; renderAlerts(); renderNotifs(); });

/* Pencarian area: menyaring kartu status dan tabel per area. */
const areaSearch = $('area-search');
if (areaSearch) {
  areaSearch.addEventListener('input', e => {
    state.query = e.target.value;
    renderAreaCards();
    renderAreaTable();
  });
}

setInterval(() => {
  $('clock').textContent = new Date().toLocaleTimeString('id-ID');
}, 1000);

/* =====================================================================
 *  BOOT
 * ===================================================================== */
function boot() {
  applyDark();
  $('chart-interval-label').textContent = CONFIG.intervalSeconds;
  state.activeId = null;
  state.alerts = [];
  renderAlerts();
  renderNotifs();
  handleOccupancyEvent();
  setInterval(handleOccupancyEvent, CONFIG.intervalSeconds * 1000);
}

document.addEventListener('DOMContentLoaded', boot);
