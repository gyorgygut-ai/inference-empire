import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, test, expect } from "vitest";

const fixturesDir = join(import.meta.dirname, "deploy-flash", "fixtures");

function input(name: string) {
  return JSON.parse(
    readFileSync(join(fixturesDir, name, "input.json"), "utf-8"),
  );
}
function expected(name: string) {
  return JSON.parse(
    readFileSync(join(fixturesDir, name, "expected.json"), "utf-8"),
  );
}

describe("deploy-flash.ts", () => {
  test("spawns uv run --locked flash deploy with correct cwd", async () => {
    const { workerFile } = input("spawns-correct-args");
    const { command, args, options } = expected("spawns-correct-args");

    let captured: { command?: string; args?: string[]; options?: any } = {};
    const stubSpawn = (
      cmd: string,
      argv: string[],
      opts: any,
    ) => {
      captured.command = cmd;
      captured.args = argv;
      captured.options = opts;
      return {
        stdout: { on: () => {} },
        stderr: { on: () => {} },
        on: (_: string, cb: any) => {
          if (_ === "data") cb(Buffer.from("https://abc123xyz.api.runpod.ai/process"));
          else if (_ === "close") cb(0);
        },
      } as any;
    };

    const module = await import("./deploy-flash.ts");
    await module.run(workerFile, {
      spawnImpl: stubSpawn,
      consoleLog: (...args: any[]) => {},
      processExit: (code?: number) => {},
    });

    expect(captured.command).toBe(command);
    expect(captured.args).toEqual(args);
    expect(captured.options.cwd).toBe(options.cwd);
  });

  test("emits the flash URL to stdout when found in child output", async () => {
    const { workerFile } = input("emits-url");
    const { url } = expected("emits-url");

    const outputs: string[] = [];
    const stubSpawn = () => ({
      stdout: { on: (_: string, cb: any) => cb(Buffer.from(url)) },
      stderr: { on: () => {} },
      on: (_: string, cb: any) => {
        if (_ === "close") cb(0);
      },
    });

    const module = await import("./deploy-flash.ts");
    await module.run(workerFile, {
      spawnImpl: stubSpawn,
      consoleLog: (...args: any[]) => outputs.push(args.join(" ")),
      processExit: (code?: number) => {},
    });

    expect(outputs).toContain(url);
  });

  test("exits with code 1 when no URL is found in output", async () => {
    const { workerFile } = input("no-url-found");
    const { exitCode } = expected("no-url-found");

    const exits: number[] = [];
    const stubSpawn = () => ({
      stdout: { on: () => {} },
      stderr: { on: () => {} },
      on: (_: string, cb: any) => {
        if (_ === "close") cb(1);
      },
    });

    const module = await import("./deploy-flash.ts");
    await module.run(workerFile, {
      spawnImpl: stubSpawn,
      consoleLog: (...args: any[]) => {},
      processExit: (code?: number) => exits.push(code ?? 1),
    });

    expect(exits).toContain(exitCode);
  });

  test("exits with code 1 when child process fails to start", async () => {
    const { workerFile } = input("child-fails-to-start");
    const { exitCode } = expected("child-fails-to-start");

    const exits: number[] = [];
    const stubSpawn = () => ({
      stdout: { on: () => {} },
      stderr: { on: () => {} },
      on: (_: string, cb: any) => {
        if (_ === "error") cb(new Error("spawn failed"));
      },
    });

    const module = await import("./deploy-flash.ts");
    try {
      await module.run(workerFile, {
        spawnImpl: stubSpawn,
        consoleLog: (...args: any[]) => {},
        processExit: (code?: number) => {
          exits.push(code ?? 1);
          throw new Error("exit called");
        },
      });
    } catch {
      // processExit throws
    }

    expect(exits).toContain(exitCode);
  });
});