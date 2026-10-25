export const strategyBeam = {
  resolveConfig: () => {
    const url = process.env.WORKER_RESOLVED_BEAM_URL;
    const token = process.env.BEAM_TOKEN;
    return url && token ? { url, token } : null;
  },

  async pushToTaskQueue(input: any, config: { url: string; token: string }) {
    const response = await fetch(config.url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.token}`,
      },
      body: JSON.stringify(input),
    });
    console.error("[beam] POST", config.url, "->", response.status, response.headers.get("content-type"));
    if (!response.ok) throw new Error(`beam queue ${response.status}: ${await response.text()}`);
    const result = await response.json();
    return { task_id: result.task_id };
  },

  async fetchTaskStatus(taskId: string, config: { url: string; token: string }) {
    const response = await fetch(`https://api.beam.cloud/v2/task/${taskId}/`, {
      headers: { Authorization: `Bearer ${config.token}` },
    });
    if (!response.ok) throw new Error(`beam task ${response.status}: ${await response.text()}`);
    const result = await response.json();
    return {
      status: result.status === "COMPLETE" ? "COMPLETED" : result.status || "PENDING",
      output: result.outputs?.[0],
    };
  },

  encodeTaskId(originalTaskId: string) {
    return Buffer.from(`beam:${originalTaskId}`, 'utf8').toString('base64url');
  },

  decodeTaskId(encodedId: string) {
    const decoded = Buffer.from(encodedId, 'base64url').toString('utf8');
    const [provider, originalTaskId] = decoded.split(':');
    return { provider, originalTaskId };
  },
};
