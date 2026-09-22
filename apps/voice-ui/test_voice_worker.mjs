import WebSocket from "ws";

const WORKER_URL = process.env.WORKER_URL || "wss://gyorgy-gutai--ws.modal.run/v1/realtime";
const WORKER_TOKEN = process.env.WORKER_TOKEN || "";

console.log(`[TEST] Connecting to ${WORKER_URL}`);
console.log(`[TEST] Token: ${WORKER_TOKEN ? "provided" : "not provided"}`);

const ws = new WebSocket(WORKER_URL, {
  headers: WORKER_TOKEN ? { Authorization: `Bearer ${WORKER_TOKEN}` } : {},
});

ws.on("open", () => {
  console.log("[TEST] ✓ WebSocket connected");
});

ws.on("message", (data) => {
  const msg = JSON.parse(data.toString());
  console.log(`[TEST] <- ${msg.type}`, JSON.stringify(msg, null, 2).slice(0, 200));
  
  if (msg.type === "session.created") {
    console.log("[TEST] ✓ session.created received - worker is responding!");
    
    // Try sending a session.update
    const sessionUpdate = {
      type: "session.update",
      session: {
        voice: "GutAI",
        language: "en"
      }
    };
    console.log(`[TEST] Sending session.update: ${JSON.stringify(sessionUpdate)}`);
    ws.send(JSON.stringify(sessionUpdate));
    
    // Wait a bit then disconnect
    setTimeout(() => {
      console.log("[TEST] Disconnecting");
      ws.close(1000);
    }, 2000);
  }
});

ws.on("close", (code, reason) => {
  console.log(`[TEST] ✓ WebSocket closed (code: ${code}, reason: ${reason.toString()})`);
  process.exit(0);
});

ws.on("error", (err) => {
  console.error("[TEST] ✗ WebSocket error:", err.message);
  process.exit(1);
});

// Timeout
setTimeout(() => {
  console.error("[TEST] ✗ Timeout - no response within 10 seconds");
  ws.close();
  process.exit(1);
}, 10000);
