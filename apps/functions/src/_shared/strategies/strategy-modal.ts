export const strategyModal = {
  resolveConfig: () => {
    const url = process.env.WORKER_RESOLVED_MODAL_URL;
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

  encodeTaskId(originalTaskId: string) {
    return Buffer.from(`modal:${originalTaskId}`, 'utf8').toString('base64url');
  },

  decodeTaskId(encodedId: string) {
    const decoded = Buffer.from(encodedId, 'base64url').toString('utf8');
    const [provider, originalTaskId] = decoded.split(':');
    return { provider, originalTaskId };
  },
};
