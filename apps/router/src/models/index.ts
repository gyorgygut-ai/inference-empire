export async function loadModel() {
  const model = process.env.ROUTER_MODEL;
  if (model === 'flux2') {
    return import('./flux2.js');
  }
  if (model === 'krea2') {
    return import('./krea2.js');
  }
  throw new Error(`ROUTER_MODEL must be "flux2" or "krea2", got ${model ?? 'undefined'}`);
}
