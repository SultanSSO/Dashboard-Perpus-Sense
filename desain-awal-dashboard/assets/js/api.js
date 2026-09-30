/* Same-origin client for the Vision Agent dashboard API. */
'use strict';

window.VisionApi = (() => {
  async function get(path) {
    const response = await fetch(`/api/v1${path}`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = payload.error || {};
      throw new Error(error.message || `API ${response.status}`);
    }
    return payload;
  }

  async function post(path, body) {
    const response = await fetch(`/api/v1${path}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = payload.error || {};
      throw new Error(error.message || `API ${response.status}`);
    }
    return payload;
  }

  return { get, post };
})();
