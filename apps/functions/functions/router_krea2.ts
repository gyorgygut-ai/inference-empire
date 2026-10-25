import { createRouter } from "../../src/_shared/router";

const krea2Schema = {
  input: null as any,
  output: null as any,
};

export async function handler(event: any, context: any) {
  const url = event.rawUrl || `http://${event.headers.host}${event.path}`;
  const req = new Request(url, {
    method: event.httpMethod,
    headers: event.headers,
  });
  
  const router = createRouter(krea2Schema);
  const res = await router.handle(req);
  
  return {
    statusCode: res.status,
    headers: Object.fromEntries(res.headers.entries()),
    body: await res.text(),
  };
}

