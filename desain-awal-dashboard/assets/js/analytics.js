/* Riwayat & analitik dari event vision.event.v1 yang dibaca melalui API. */
'use strict';

const ANAL_COLOR = { gold: '#F4C542', primary: '#125174', body: '#64748B', bodyDark: '#AEB7C0', grid: '#E2E8F0', gridDark: '#2E3A47' };
const analyticsState = {
  period: 'harian',
  events: [],
  totalEvents: 0,
  dark: (new URLSearchParams(location.search).get('force') === 'dark') ||
    (localStorage.getItem('perpus-theme') ? localStorage.getItem('perpus-theme') === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches),
};
let chart = null;

function periodMeta(period) {
  return {
    harian: { judul: 'Deteksi Orang Hari Ini', sub: 'Rata-rata per jam dari event aktual' },
    mingguan: { judul: 'Deteksi Orang 7 Hari', sub: 'Rata-rata per hari dari event aktual' },
    bulanan: { judul: 'Deteksi Orang 30 Hari', sub: 'Rata-rata per tanggal dari event aktual' },
    tahunan: { judul: 'Deteksi Orang 12 Bulan', sub: 'Rata-rata per bulan dari event aktual' },
  }[period];
}

function eventValue(event) {
  const value = event?.measurement?.person_count;
  return Number.isFinite(value) ? value : null;
}

function bucketKey(date, period) {
  if (period === 'harian') return `${String(date.getHours()).padStart(2, '0')}.00`;
  if (period === 'mingguan') return date.toLocaleDateString('id-ID', { weekday: 'short' });
  if (period === 'bulanan') return String(date.getDate());
  return date.toLocaleDateString('id-ID', { month: 'short' });
}

function buildSeries(period) {
  const labels = period === 'harian'
    ? Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, '0')}.00`)
    : [];
  const groups = new Map(labels.map(label => [label, []]));
  analyticsState.events.forEach(event => {
    const value = eventValue(event);
    const observed = event?.observed_at ? new Date(event.observed_at) : null;
    if (value === null || !observed || Number.isNaN(observed.valueOf())) return;
    const key = bucketKey(observed, period);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(value);
  });
  const ordered = [...groups.entries()];
  return {
    labels: ordered.map(([label]) => label),
    persons: ordered.map(([, values]) => values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null),
  };
}

function renderChart() {
  const series = buildSeries(analyticsState.period);
  const dark = analyticsState.dark;
  const axis = dark ? ANAL_COLOR.bodyDark : ANAL_COLOR.body;
  const grid = dark ? ANAL_COLOR.gridDark : ANAL_COLOR.grid;
  const meta = periodMeta(analyticsState.period);
  document.getElementById('an-title').textContent = meta.judul;
  document.getElementById('an-sub').textContent = meta.sub;
  const opts = {
    chart: { type: 'area', height: 380, toolbar: { show: true }, background: 'transparent', fontFamily: 'Satoshi, Inter, sans-serif' },
    theme: { mode: dark ? 'dark' : 'light' },
    stroke: { curve: 'smooth', width: 3 },
    fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05 } },
    colors: [ANAL_COLOR.gold],
    series: [{ name: 'Orang terdeteksi', data: series.persons }],
    xaxis: { categories: series.labels, labels: { style: { colors: axis } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { colors: axis } } },
    grid: { borderColor: grid, strokeDashArray: 4 },
    legend: { position: 'top', horizontalAlign: 'right', labels: { colors: axis } },
    dataLabels: { enabled: false },
    tooltip: { theme: dark ? 'dark' : 'light' },
  };
  if (!chart) { chart = new ApexCharts(document.getElementById('analytics-chart'), opts); chart.render(); }
  else {
    chart.updateOptions({ theme: opts.theme, xaxis: opts.xaxis, yaxis: opts.yaxis, grid: opts.grid, legend: opts.legend }, false, false);
    chart.updateSeries(opts.series);
  }

  const values = series.persons.filter(Number.isFinite);
  const average = values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
  const peak = values.length ? Math.round(Math.max(...values)) : null;
  const low = values.length ? Math.round(Math.min(...values)) : null;
  const peakIndex = series.persons.indexOf(peak);
  document.getElementById('sum-avg').textContent = average === null ? '--' : `${average} orang`;
  document.getElementById('sum-peak').textContent = peak === null ? '--' : `${peak} orang`;
  document.getElementById('sum-peak-label').textContent = peak === null ? '' : `pada ${series.labels[peakIndex]}`;
  document.getElementById('sum-low').textContent = low === null ? '--' : `${low} orang`;
  document.getElementById('metric-event-count').textContent = String(analyticsState.totalEvents);
  document.getElementById('metric-downtime').textContent = '--';
  document.getElementById('metric-task-status').textContent = 'API';
  const recent = analyticsState.events.slice(0, 3);
  document.getElementById('analytics-events').innerHTML = recent.length
    ? recent.map(event => `<li class="rounded-sm bg-whiter px-3.5 py-3 dark:bg-boxdark-2"><p class="text-xs font-bold text-emerald-600 dark:text-emerald-400">${event.source?.camera_id || 'CCTV'} · ${eventValue(event) ?? '--'} orang</p><p class="mt-1 text-[10px] font-medium text-body">${event.event_type || 'VISION_EVENT'} · ${new Date(event.observed_at).toLocaleString('id-ID')}</p></li>`).join('')
    : '<li class="rounded-sm bg-whiter p-4 text-center text-xs text-body">Belum ada event aktual.</li>';
}

async function loadAnalytics() {
  try {
    const result = await VisionApi.get('/events?limit=200');
    analyticsState.events = result.items || [];
    analyticsState.totalEvents = Number.isFinite(result.total) ? result.total : analyticsState.events.length;
    renderChart();
  } catch (error) {
    analyticsState.events = [];
    analyticsState.totalEvents = 0;
    renderChart();
  }
}

function setPeriod(period, btn) {
  analyticsState.period = period;
  document.querySelectorAll('.period-btn').forEach(b => b.className = 'period-btn rounded-sm px-3.5 py-2 text-xs font-bold text-body transition hover:text-primary dark:hover:text-gold');
  btn.className = 'period-btn rounded-sm bg-primary px-3.5 py-2 text-xs font-bold text-white dark:bg-gold dark:text-primarydk';
  renderChart();
}

document.addEventListener('DOMContentLoaded', () => {
  renderChart();
  loadAnalytics();
  setInterval(loadAnalytics, 5000);
});
