/* =====================================================================
 * PerpusAuth, autentikasi sisi klien (Fase 1.1, statis)
 * Kredensial demo: admin / admin123
 *
 * Fase 2: ganti validasi lokal dengan POST /api/v1/auth/login (JWT).
 * API di bawah sengaja dibuat mirip sehingga halaman tidak perlu diubah:
 *   PerpusAuth.login(u, p)   -> { ok, message } , set session bila ok
 *   PerpusAuth.logout()      -> hapus session + redirect ke login.html
 *   PerpusAuth.guard()       -> panggil di halaman terproteksi
 *   PerpusAuth.isLoggedIn()  -> boolean
 * ===================================================================== */

'use strict';

const PerpusAuth = (() => {
  const KEY = 'perpus-auth';
  // Kredensial demo (Fase 1.1). Nanti divalidasi di backend.
  const CREDENTIALS = { username: 'admin', password: 'admin123' };

  function _setSession(username, remember) {
    const payload = { username, loginAt: new Date().toISOString() };
    if (remember) localStorage.setItem(KEY, JSON.stringify(payload));
    else sessionStorage.setItem(KEY, JSON.stringify(payload));
  }
  function _getSession() {
    try {
      return JSON.parse(sessionStorage.getItem(KEY) || localStorage.getItem(KEY) || 'null');
    } catch { return null; }
  }

  function login(username, password, remember = false) {
    if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
      _setSession(username, remember);
      return { ok: true };
    }
    return { ok: false, message: 'Username atau password salah.' };
  }

  function logout() {
    sessionStorage.removeItem(KEY);
    localStorage.removeItem(KEY);
    location.href = 'login.html';
  }

  function isLoggedIn() { return !!_getSession(); }
  function currentUser() { return _getSession(); }

  // Panggil di halaman terproteksi; redirect ke login bila belum masuk.
  function guard() { if (!isLoggedIn()) location.replace('login.html'); }

  return { login, logout, isLoggedIn, currentUser, guard };
})();
