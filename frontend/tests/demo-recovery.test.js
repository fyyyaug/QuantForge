import test from 'node:test';
import assert from 'node:assert/strict';

test('exhausted session can be ended after reload and replaced without clearing cookies', async () => {
  const saved = Object.fromEntries(['document', 'window', 'fetch'].map((k) => [k, globalThis[k]]));
  const listeners = {};
  const root = { innerHTML: '', addEventListener: (name, fn) => (listeners[name] = fn) };
  let active = true;
  let exhausted = true;
  let logouts = 0;
  const limits = { session_minutes: 120, max_runs: 12 };
  const session = () => ({ enabled: true, session_active: active, expires_at: 2000000000, limits });
  globalThis.document = {
    querySelector: (selector) => (selector === '#app' ? root : null),
    addEventListener() {},
  };
  globalThis.window = { addEventListener() {}, scrollTo() {} };
  globalThis.fetch = async (path) => {
    let body;
    let status = 200;
    if (path === '/api/workspace') body = { demo: session() };
    else if (path === '/api/demo/session/logout') {
      active = false;
      logouts++;
      body = { ended: true };
    } else if (path === '/api/demo/session') {
      if (!active) exhausted = false;
      active = true;
      body = session();
    } else if (exhausted) {
      status = 429;
      body = { error: { code: 'DEMO_QUOTA_REACHED', message: 'Request allowance exhausted.' } };
    } else body = [];
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  };
  const settle = async () => {
    for (let i = 0; i < 20; i++) await new Promise((resolve) => setImmediate(resolve));
  };
  const click = (action) =>
    listeners.click({
      target: { closest: (selector) => (selector === '[data-action]' ? { dataset: { action } } : null) },
    });
  try {
    await import('../assets/app.js?demo-recovery');
    await settle();
    assert.match(root.innerHTML, /Request allowance exhausted/);
    assert.match(root.innerHTML, /data-action="end-demo"/);
    click('start-demo');
    await settle();
    assert.match(root.innerHTML, /data-action="end-demo"/);
    assert.equal(logouts, 0, 'failed reconnect must not silently revoke history access');
    click('end-demo');
    await settle();
    assert.equal(logouts, 1);
    assert.doesNotMatch(root.innerHTML, /data-action="end-demo"/);
    click('start-demo');
    await settle();
    assert.match(root.innerHTML, /Start with a hypothesis/);
    assert.match(root.innerHTML, /End demo/);
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
});
