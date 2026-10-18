import { Handler } from "@netlify/functions";

export const handler: Handler = async (event) => {
  const url = new URL(event.path, "http://localhost");
  const pathname = url.pathname;

  if (pathname.startsWith("/flux2")) {
    console.log("flux2");
    return { statusCode: 200, body: "flux2" };
  }

  if (pathname.startsWith("/krea2")) {
    console.log("krea2");
    return { statusCode: 200, body: "krea2" };
  }

  return { statusCode: 404, body: "Not Found" };
};