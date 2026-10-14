const DEFAULT_ROUTER_URL = 'http://127.0.0.1:4202';

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('#app not found');
}

app.innerHTML = [
  '<h1>beni</h1>',
  '<label>router <input id="router-url" type="text" autocomplete="off" /></label>',
  '<label>auth token <input id="token" type="password" autocomplete="off" /></label>',
  '<div><button id="sup">GET /sup</button> <button id="q">POST /q</button></div>',
  '<pre id="out"></pre>'
].join('');

const out = document.querySelector<HTMLPreElement>('#out');
const tokenInput = document.querySelector<HTMLInputElement>('#token');
const routerInput = document.querySelector<HTMLInputElement>('#router-url');

if (routerInput) {
  routerInput.value = DEFAULT_ROUTER_URL;
}

function routerUrl(): string {
  const v = routerInput?.value.trim();
  return v ? v : DEFAULT_ROUTER_URL;
}

function show(value: unknown): void {
  if (out) {
    out.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  }
}

document.querySelector<HTMLButtonElement>('#sup')?.addEventListener('click', async () => {
  const ROUTER_URL = routerUrl();
  const res = await fetch(`${ROUTER_URL}/sup`, {
    headers: tokenInput?.value ? { authorization: `Bearer ${tokenInput.value}` } : {}
  });
  show({ status: res.status, body: await res.text() });
});

document.querySelector<HTMLButtonElement>('#q')?.addEventListener('click', async () => {
  const ROUTER_URL = routerUrl();
  const res = await fetch(`${ROUTER_URL}/q`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...(tokenInput?.value ? { authorization: `Bearer ${tokenInput.value}` } : {})
    },
    body: JSON.stringify({})
  });
  show({ status: res.status, body: await res.text() });
});
