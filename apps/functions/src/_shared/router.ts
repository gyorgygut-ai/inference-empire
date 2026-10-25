import { Router } from "itty-router";
import { z } from "zod";
import { pickStrategy } from "./services/pick-strategy";
import { createStrategy } from "./services/create-strategy";

type Status = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function auth(request: Request) {
  const authHeader = request.headers.get("Authorization");
  const token = process.env.ROUTER_GENERATED_AUTH_TOKEN;
  if (!authHeader || !authHeader.startsWith("Bearer ")) return json({ error: "Unauthorized" }, 401);
  if (!token || authHeader.substring(7) !== token) return json({ error: "Invalid token" }, 401);
  return null;
}

export function createRouter<Api extends z.ZodObject<{ input: z.ZodTypeAny; output: z.ZodTypeAny }>>(api: Api, base: string) {
  const router = Router({ base });

  router.post("/q", async (request: Request) => {
    const authErr = auth(request);
    if (authErr) return authErr;
    try {
      const body = await request.json();
      const parsed = api.shape.input.safeParse(body.input);
      if (!parsed.success) {
        return json({ error: "Invalid input", details: parsed.error.issues }, 400);
      }
      const strategyName = pickStrategy();
      const strategy = createStrategy(strategyName);
      if (!strategy) return json({ error: "Strategy unavailable" }, 503);
      const config = strategy.resolveConfig();
      if (!config) return json({ error: "Worker URL not configured" }, 503);
      const { task_id } = await strategy.pushToTaskQueue(parsed.data, config);
      const encodedTaskId = strategy.encodeTaskId(task_id);
      return json({ task_id: encodedTaskId });
    } catch (error) {
      console.error("[router] /q failed:", error);
      return json({ error: "Internal error" }, 500);
    }
  });

  router.get("/sup", async (request: Request) => {
    const authErr = auth(request);
    if (authErr) return authErr;
    const url = new URL(request.url);
    const id = url.searchParams.get("id");
    if (!id) return json({ error: "Missing task id" }, 400);
    try {
      const strategyName = "beam";
      const strategy = createStrategy(strategyName)!;
      const decoded = strategy.decodeTaskId(id);
      const provider = decoded.provider;
      const originalTaskId = decoded.originalTaskId;
      if (!provider || !originalTaskId) return json({ error: "Invalid task id format" }, 400);
      const strat = createStrategy(provider);
      if (!strat) return json({ error: "Unknown provider" }, 400);
      const config = strat.resolveConfig();
      if (!config) return json({ error: "Worker URL not configured" }, 503);
      const result = await strat.fetchTaskStatus(originalTaskId, config);
      const response: any = { status: result.status as Status };
      if (result.status === "COMPLETED" && result.output) {
        const parsedOutput = api.shape.output.safeParse(result.output);
        if (parsedOutput.success) response.output = parsedOutput.data;
        else response.output = result.output;
      }
      return json(response);
    } catch {
      return json({ error: "Invalid task id encoding" }, 400);
    }
  });

  router.all("*", () => json({ error: "Not Found" }, 404));

  return router;
}
