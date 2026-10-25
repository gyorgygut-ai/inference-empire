export const strategyBeam = {
  resolveConfig: () => {
    const url = process.env.WORKER_RESOLVED_BEAM_URL;
    return url ? { url } : null;
  },

  async pushToTaskQueue(input: any, config: { url: string }) {
    const response = await fetch(`${config.url}/queues/default`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });
    const result = await response.json();
    return { task_id: result.task_id };
  },

  async fetchTaskStatus(taskId: string, config: { url: string }) {
    const response = await fetch(`${config.url}/queues/default/${taskId}`);
    const result = await response.json();
    return {
      status: result.status || "PENDING",
      output: result.output,
    };
  },
};
