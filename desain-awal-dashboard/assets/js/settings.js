/* Dashboard preferences plus operational Vision Agent task settings. */
'use strict';

const PerpusSettings = (() => {
  const KEY = 'perpus-settings';
  const defaults = {
    interval: 5,
    padat: 66,
    sedang: 33,
    dark: null,
    profile: 'balanced',
    model: 'yolo11n.pt',
    appliedModel: 'yolo11n.pt',
    boxes: true,
    healthEvents: true,
  };
  const AGENT_FIELDS = [
    'agent-task-select',
    'agent-severity',
    'agent-threshold',
    'agent-persistence',
    'agent-resolution',
    'agent-cooldown',
    'agent-enabled',
    'btn-save-agent',
  ];

  let agentTasks = [];
  let agentDefaults = { run_all_tasks: false, mode: 'individual' };
  const $ = id => document.getElementById(id);

  function load() {
    try { return { ...defaults, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; }
    catch { return { ...defaults }; }
  }

  function save(settings) { localStorage.setItem(KEY, JSON.stringify(settings)); }

  function setAgentDisabled(disabled) {
    AGENT_FIELDS.forEach(id => { if ($(id)) $(id).disabled = disabled; });
  }

  function setAgentStatus(message, kind = 'normal') {
    const status = $('agent-save-status');
    if (!status) return;
    status.textContent = message;
    status.className = `text-xs font-medium ${
      kind === 'error' ? 'text-rose-500' :
      kind === 'success' ? 'text-emerald-600 dark:text-emerald-400' : 'text-body'
    }`;
  }

  function setAgentDefaultStatus(message, kind = 'normal') {
    const status = $('agent-default-status');
    if (!status) return;
    status.textContent = message;
    status.className = `text-xs font-medium ${
      kind === 'error' ? 'text-rose-500' :
      kind === 'success' ? 'text-emerald-600 dark:text-emerald-400' : 'text-body'
    }`;
  }

  function renderAgentDefaults(settings) {
    agentDefaults = settings || { run_all_tasks: false, mode: 'individual' };
    $('agent-default-all').checked = agentDefaults.run_all_tasks;
    setAgentDefaultStatus(
      agentDefaults.run_all_tasks
        ? 'ON · semua task monitoring didorong ke RUNNING.'
        : 'OFF · status aktif diatur per task.'
    );
    if ($('agent-enabled')) $('agent-enabled').disabled = agentDefaults.run_all_tasks;
  }

  function renderAgentTask(taskId) {
    const task = agentTasks.find(item => item.task_id === taskId) || agentTasks[0];
    if (!task) {
      setAgentDisabled(true);
      setAgentStatus('Belum ada task Vision Agent yang dapat dikonfigurasi.', 'error');
      return;
    }
    const rule = task.rule || {};
    const thresholdField = $('agent-threshold');
    $('agent-task-select').value = task.task_id;
    const cameraIds = task.camera_ids || [];
    $('agent-camera').value = cameraIds.length > 4
      ? `${cameraIds.length} kamera · ${cameraIds.slice(0, 3).join(', ')}…`
      : cameraIds.join(', ');
    $('agent-camera').title = cameraIds.join(', ');
    $('agent-severity').value = rule.severity || 'warning';
    thresholdField.value = rule.threshold ?? rule.high_threshold ?? rule.person_threshold ?? 0;
    thresholdField.disabled = !['PEOPLE_THRESHOLD_EXCEEDED'].includes(rule.type);
    thresholdField.title = thresholdField.disabled
      ? 'Threshold task ini dikelola melalui konfigurasi rule lengkap dan override per kamera.'
      : '';
    $('agent-persistence').value = rule.persistence_seconds ?? 0;
    $('agent-resolution').value = rule.resolution_seconds ?? 0;
    $('agent-cooldown').value = rule.cooldown_seconds ?? 0;
    setAgentDisabled(false);
    thresholdField.disabled = !['PEOPLE_THRESHOLD_EXCEEDED'].includes(rule.type);
    $('agent-enabled').checked = agentDefaults.run_all_tasks || task.status === 'RUNNING';
    $('agent-enabled').disabled = agentDefaults.run_all_tasks;
    setAgentStatus(`${task.task_id} · ${rule.type} · ${task.status} · ${cameraIds.length} kamera.`);
  }

  async function loadAgentTasks() {
    const badge = $('agent-engine-status');
    setAgentDisabled(true);
    try {
      const [taskResult, health, defaultSettings] = await Promise.all([
        VisionApi.get('/tasks?limit=100'),
        VisionApi.get('/health'),
        VisionApi.get('/agent/settings'),
      ]);
      agentTasks = (taskResult.items || []).filter(
        task => task.rule?.type && task.status !== 'CANCELLED'
      );
      renderAgentDefaults(defaultSettings);
      const select = $('agent-task-select');
      select.replaceChildren();
      if (agentTasks.length) {
        agentTasks.forEach(task => select.add(new Option(`${task.name} · ${task.status}`, task.task_id)));
      } else {
        select.add(new Option('Belum ada task threshold', ''));
      }
      if (badge) {
        badge.textContent = health.live_worker?.connected ? 'ONLINE' : 'WORKER OFFLINE';
        badge.className = `rounded-sm px-2.5 py-1 text-[10px] font-bold ${
          health.live_worker?.connected
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300'
            : 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300'
        }`;
      }
      renderAgentTask(select.value || agentTasks[0]?.task_id);
    } catch (error) {
      if (badge) {
        badge.textContent = 'OFFLINE';
        badge.className = 'rounded-sm bg-rose-100 px-2.5 py-1 text-[10px] font-bold text-rose-600 dark:bg-rose-500/20 dark:text-rose-300';
      }
      setAgentDisabled(true);
      setAgentStatus(`Gagal memuat konfigurasi agent: ${error.message}`, 'error');
    }
  }

  function readNonNegative(id, label) {
    const value = Number($(id).value);
    if (!Number.isFinite(value) || value < 0) throw new Error(`${label} harus angka non-negatif.`);
    return value;
  }

  async function saveAgentTask() {
    const taskId = $('agent-task-select').value;
    const task = agentTasks.find(item => item.task_id === taskId);
    if (!task) {
      setAgentStatus('Pilih task yang akan dikonfigurasi.', 'error');
      return;
    }
    const button = $('btn-save-agent');
    button.disabled = true;
    button.textContent = 'Menyimpan...';
    try {
      const result = await VisionApi.post(`/tasks/${encodeURIComponent(taskId)}/settings`, {
        enabled: agentDefaults.run_all_tasks || $('agent-enabled').checked,
        rule: {
          ...task.rule,
          ...(task.rule.type === 'PEOPLE_THRESHOLD_EXCEEDED'
            ? { threshold: readNonNegative('agent-threshold', 'Batas jumlah orang') }
            : {}),
          persistence_seconds: readNonNegative('agent-persistence', 'Durasi pemicu'),
          resolution_seconds: readNonNegative('agent-resolution', 'Durasi normal'),
          cooldown_seconds: readNonNegative('agent-cooldown', 'Cooldown'),
          severity: $('agent-severity').value,
        },
      });
      const index = agentTasks.findIndex(item => item.task_id === taskId);
      agentTasks[index] = result.task;
      const selectedOption = $('agent-task-select').selectedOptions[0];
      if (selectedOption) selectedOption.textContent = `${result.task.name} · ${result.task.status}`;
      renderAgentTask(taskId);
      setAgentStatus(`Tersimpan · audit ${result.audit_id}`, 'success');
    } catch (error) {
      setAgentStatus(`Gagal menyimpan: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
      button.textContent = 'Simpan Pengaturan Agent';
    }
  }

  async function saveAgentDefaults() {
    const button = $('btn-save-agent-default');
    button.disabled = true;
    button.textContent = 'Menerapkan...';
    try {
      const result = await VisionApi.post('/agent/settings', {
        run_all_tasks: $('agent-default-all').checked,
      });
      renderAgentDefaults(result.settings);
      await loadAgentTasks();
      setAgentDefaultStatus(`Tersimpan · audit ${result.audit_id}`, 'success');
    } catch (error) {
      setAgentDefaultStatus(`Gagal menerapkan default: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
      button.textContent = 'Terapkan Default';
    }
  }

  function renderRuntime(runtime) {
    if (!$('runtime-system-status')) return;
    const status = runtime.system_status || 'UNKNOWN';
    $('runtime-system-status').textContent = status;
    $('runtime-worker-count').textContent = `${runtime.workers_running || 0} / ${runtime.configured_cameras || 0}`;
    $('runtime-task-engine').textContent = runtime.task_engine?.running ? 'RUNNING' : 'STOPPED';
    $('runtime-failed-count').textContent = String(runtime.workers_failed || 0);
    const colors = {
      RUNNING: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
      DEGRADED: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
      STOPPED: 'bg-slate-100 text-body dark:bg-boxdark-2',
    };
    $('runtime-system-status').className = `rounded-sm px-3 py-1 text-[10px] font-bold ${colors[status] || colors.STOPPED}`;
  }

  async function loadRuntime() {
    try {
      const runtime = await VisionApi.get('/runtime/status');
      renderRuntime(runtime);
      const select = $('runtime-camera-select');
      const selected = select.value;
      select.replaceChildren();
      (runtime.cameras || []).forEach(camera => {
        const label = `${camera.camera_id} · ${camera.location || 'Lokasi belum diisi'} · ${camera.running ? 'RUNNING' : 'STOPPED'}`;
        select.add(new Option(label, camera.camera_id));
      });
      if (selected && [...select.options].some(option => option.value === selected)) select.value = selected;
    } catch (error) {
      $('runtime-action-status').textContent = `Gagal memuat runtime: ${error.message}`;
    }
  }

  function setRuntimeBusy(busy) {
    ['btn-runtime-start', 'btn-runtime-stop', 'btn-runtime-restart', 'btn-camera-start', 'btn-camera-stop', 'btn-camera-restart']
      .forEach(id => { if ($(id)) $(id).disabled = busy; });
  }

  async function runtimeAction(action, cameraId = null) {
    const globalAction = !cameraId;
    if (globalAction && ['stop', 'restart'].includes(action)) {
      const message = action === 'stop'
        ? 'Hentikan seluruh monitoring Vision Agent?'
        : 'Restart seluruh worker dan Task Engine?';
      if (!window.confirm(message)) return;
    }
    setRuntimeBusy(true);
    $('runtime-action-status').textContent = `Menjalankan ${action}${cameraId ? ` untuk ${cameraId}` : ' seluruh runtime'}...`;
    try {
      const path = cameraId
        ? `/runtime/${encodeURIComponent(cameraId)}/${action}`
        : `/runtime/${action}`;
      const payload = globalAction ? { batch_size: 4, batch_delay: 1 } : {};
      const result = await VisionApi.post(path, payload);
      if (result.runtime) renderRuntime(result.runtime);
      $('runtime-action-status').textContent = `Berhasil · audit ${result.audit_id}`;
      await loadRuntime();
    } catch (error) {
      $('runtime-action-status').textContent = `Gagal: ${error.message}`;
    } finally {
      setRuntimeBusy(false);
    }
  }

  function init() {
    const settings = load();
    if ($('set-interval')) $('set-interval').value = String(settings.interval);

    const padat = $('set-padat');
    const sedang = $('set-sedang');
    if (padat) {
      padat.value = settings.padat;
      $('val-padat').textContent = settings.padat;
      padat.addEventListener('input', event => { $('val-padat').textContent = event.target.value; });
    }
    if (sedang) {
      sedang.value = settings.sedang;
      $('val-sedang').textContent = settings.sedang;
      sedang.addEventListener('input', event => { $('val-sedang').textContent = event.target.value; });
    }

    if ($('set-profile')) $('set-profile').value = settings.profile;
    if ($('set-boxes')) $('set-boxes').checked = settings.boxes;
    if ($('set-health-events')) $('set-health-events').checked = settings.healthEvents;

    syncDark(document.documentElement.classList.contains('dark'));
    const appliedModel = settings.appliedModel || settings.model || defaults.appliedModel;
    if ($('set-model')) $('set-model').value = appliedModel;
    if ($('model-apply-status')) $('model-apply-status').textContent = `Model aktif: ${appliedModel}`;

    const darkButton = $('set-dark');
    if (darkButton) darkButton.addEventListener('click', () => {
      const nowDark = !document.documentElement.classList.contains('dark');
      localStorage.setItem('perpus-theme', nowDark ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', nowDark);
      $('icon-moon').classList.toggle('hidden', nowDark);
      $('icon-sun').classList.toggle('hidden', !nowDark);
      syncDark(nowDark);
    });

    const user = PerpusAuth.currentUser();
    if (user && $('acc-user')) $('acc-user').textContent = user.username;

    const applyModel = $('set-apply-model');
    if (applyModel) applyModel.addEventListener('click', () => {
      const model = ($('set-model') || {}).value || defaults.appliedModel;
      const current = load();
      save({ ...current, model, appliedModel: model });
      if ($('model-apply-status')) $('model-apply-status').textContent = `Model aktif: ${model}`;
      applyModel.textContent = 'Sudah diterapkan';
      setTimeout(() => { applyModel.textContent = 'Terapkan'; }, 1500);
    });

    const changePassword = $('btn-change-pass');
    if (changePassword) changePassword.addEventListener('click', () => alert('Fitur ubah password akan tersedia setelah backend autentikasi aktif.'));

    const saveButton = $('btn-save');
    if (saveButton) saveButton.addEventListener('click', () => {
      const current = load();
      current.interval = Number(($('set-interval') || {}).value || current.interval);
      current.padat = Number(($('set-padat') || {}).value || current.padat);
      current.sedang = Number(($('set-sedang') || {}).value || current.sedang);
      current.profile = ($('set-profile') || {}).value || current.profile;
      current.boxes = $('set-boxes') ? $('set-boxes').checked : current.boxes;
      current.healthEvents = $('set-health-events') ? $('set-health-events').checked : current.healthEvents;
      save(current);
      saveButton.textContent = 'Tersimpan';
      setTimeout(() => { saveButton.textContent = 'Simpan Pengaturan'; }, 1500);
    });

    const reset = $('btn-reset');
    if (reset) reset.addEventListener('click', () => { save({ ...defaults }); location.reload(); });
    if ($('agent-task-select')) $('agent-task-select').addEventListener('change', event => renderAgentTask(event.target.value));
    if ($('btn-save-agent')) $('btn-save-agent').addEventListener('click', saveAgentTask);
    if ($('btn-save-agent-default')) $('btn-save-agent-default').addEventListener('click', saveAgentDefaults);
    if ($('btn-runtime-start')) $('btn-runtime-start').addEventListener('click', () => runtimeAction('start'));
    if ($('btn-runtime-stop')) $('btn-runtime-stop').addEventListener('click', () => runtimeAction('stop'));
    if ($('btn-runtime-restart')) $('btn-runtime-restart').addEventListener('click', () => runtimeAction('restart'));
    if ($('btn-camera-start')) $('btn-camera-start').addEventListener('click', () => runtimeAction('start', $('runtime-camera-select').value));
    if ($('btn-camera-stop')) $('btn-camera-stop').addEventListener('click', () => runtimeAction('stop', $('runtime-camera-select').value));
    if ($('btn-camera-restart')) $('btn-camera-restart').addEventListener('click', () => runtimeAction('restart', $('runtime-camera-select').value));
    loadAgentTasks();
    loadRuntime();
    window.setInterval(loadRuntime, 5000);
  }

  function syncDark(isDark) {
    const darkButton = $('set-dark');
    if (!darkButton) return;
    darkButton.setAttribute('aria-checked', String(isDark));
    const knob = darkButton.querySelector('span');
    darkButton.classList.toggle('bg-primary', isDark);
    darkButton.classList.toggle('bg-slate-300', !isDark);
    if (knob) knob.classList.toggle('translate-x-5', isDark);
  }

  document.addEventListener('DOMContentLoaded', init);
  return { load, save, syncDark };
})();
