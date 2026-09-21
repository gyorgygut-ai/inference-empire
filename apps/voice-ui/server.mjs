import { createServer } from "http";
import { parse } from "url";
import next from "next";
import { WebSocket, WebSocketServer } from "ws";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// A plain `node server.mjs` doesn't auto-load .env.local (only Next does),
// so load it here so the proxy can see REALTIME_WORKER_URL / WORKER_TOKEN.
const envPath = join(__dirname, ".env.local");
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const m = line.match(/^\s*([\w.-]+)\s*=\s*(.*)\s*$/);
    if (m && m[1] && !(m[1] in process.env)) {
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
}

const dev = process.env.NODE_ENV !== "production";
const port = parseInt(process.env.PORT || "3000", 10);
const workerUrl = process.env.REALTIME_WORKER_URL;
const token = process.env.WORKER_TOKEN;

if (!workerUrl) {
  console.error("[proxy] REALTIME_WORKER_URL is not set");
}

const app = next({ dev });
const handle = app.getRequestHandler();

// Forward WS frames preserving frame type. `ws` delivers text frames as
// Buffers and re-sends a Buffer as a BINARY frame, so text must be forwarded
// as a string — otherwise the browser receives a Blob and JSON.parse fails.
function pipeWs(clientWs, upstream) {
  const forward = (target, source) => {
    source.on("message", (data, isBinary) => {
      if (target.readyState === target.OPEN) {
        target.send(isBinary ? data : data.toString());
      }
    });
  };
  forward(clientWs, upstream);
  forward(upstream, clientWs);
  // Always pass a close code — Modal SDK crashes on None (no frame sent)
  upstream.on("close", () => clientWs.close(1000));
  upstream.on("error", () => clientWs.close(1006));
  clientWs.on("close", () => upstream.close(1000));
  clientWs.on("error", () => upstream.close(1006));
}

const wss = new WebSocketServer({ noServer: true });

app.prepare().then(() => {
  const upgradeHandler = app.getUpgradeHandler();
  const server = createServer((req, res) => {
    handle(req, res, parse(req.url, true));
  });

  server.on("upgrade", (req, socket, head) => {
    const { pathname } = parse(req.url || "");
    if (pathname === "/api/realtime") {
      if (!workerUrl) {
        socket.destroy();
        return;
      }
      wss.handleUpgrade(req, socket, head, (clientWs) => {
        const upstream = new WebSocket(workerUrl, {
          headers: { Authorization: `Bearer ${token}` },
        });
        pipeWs(clientWs, upstream);
      });
    } else {
      // Everything else (HMR, etc.) is handled by Next's own dev server.
      upgradeHandler(req, socket, head);
    }
  });

  server.listen(port, () => {
    console.log(
      `> Ready on http://localhost:${port} (Next dev; /api/realtime -> ${workerUrl})`,
    );
  });
});
