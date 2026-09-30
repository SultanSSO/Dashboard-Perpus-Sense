/* Logika halaman login (Fase 1.1). Validasi via PerpusAuth. */

'use strict';

(function () {
  // Sudah login? langsung ke dashboard.
  if (PerpusAuth.isLoggedIn()) { location.replace('index.html'); return; }

  const form = document.getElementById('login-form');
  const errBox = document.getElementById('login-error');
  const errText = document.getElementById('login-error-text');
  const btn = document.getElementById('btn-login');

  function showError(msg) {
    errText.textContent = msg;
    errBox.classList.remove('hidden');
    errBox.classList.add('flex');
  }
  function hideError() {
    errBox.classList.add('hidden');
    errBox.classList.remove('flex');
  }

  // Toggle lihat password
  document.getElementById('toggle-password').addEventListener('click', () => {
    const pw = document.getElementById('password');
    const show = pw.type === 'password';
    pw.type = show ? 'text' : 'password';
    document.getElementById('eye-open').classList.toggle('hidden', show);
    document.getElementById('eye-closed').classList.toggle('hidden', !show);
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    hideError();
    const u = document.getElementById('username').value.trim();
    const p = document.getElementById('password').value;
    const remember = document.getElementById('remember').checked;

    if (!u || !p) { showError('Username dan password wajib diisi.'); return; }

    btn.disabled = true;
    btn.textContent = 'Memeriksa…';

    // Simulasi jeda jaringan kecil agar terasa natural
    setTimeout(() => {
      const res = PerpusAuth.login(u, p, remember);
      if (res.ok) {
        btn.textContent = 'Berhasil, mengalihkan…';
        location.href = 'index.html';
      } else {
        btn.disabled = false;
        btn.textContent = 'Masuk';
        showError(res.message);
      }
    }, 400);
  });
})();
