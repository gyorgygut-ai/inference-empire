#!/usr/bin/env -S npx tsx
import { readFileSync } from "node:fs";
import { spawn } from "node:child_process";

const [workerFile] = process.argv.slice(2);
if (!workerFile) {
  console.error("usage: deploy-beam.ts <worker_beam.py>");
  process.exit(1);
}
const match = /@task_queue\([\s\S]*?\)\s*\n\s*def\s+(\w+)/.exec(
  readFileSync(workerFile, "utf8"),
);
if (!match) {
  console.error(
    `[deploy-beam] could not find @task_queue handler in ${workerFile}`,
  );
  process.exit(1);
}

const child = spawn(
  "uv",
  ["run", "--locked", "beam", "deploy", `${workerFile}:${match[1]}`],
  {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PYTHONPATH: [process.cwd(), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(":"),
    },
    stdio: ["inherit", "pipe", "pipe"],
  },
);

const urlPattern = /https:\/\/[^\s'"]+/;
let seenUrl: string | null = null;

function scan(chunk: Buffer): void {
  if (seenUrl) {
    return;
  }
  const clean = chunk.toString("utf8").replace(/\x1b\[[0-9;]*m/g, "");
  const match = urlPattern.exec(clean);
  if (match) {
    seenUrl = match[0].replace(/[.,;)]+$/, "");
  }
}

child.stdout?.on("data", (chunk: Buffer) => {
  process.stderr.write(chunk);
  scan(chunk);
});
child.stderr?.on("data", (chunk: Buffer) => {
  process.stderr.write(chunk);
  scan(chunk);
});
child.on("error", (err) => {
  console.error(`[deploy-beam] failed to start beam: ${err.message}`);
  process.exit(1);
});
child.on("close", (code) => {
  if (!seenUrl) {
    console.error("[deploy-beam] no beam URL found in output");
    process.exit(1);
  }
  console.log(seenUrl);
  process.exit(code ?? 0);
});
