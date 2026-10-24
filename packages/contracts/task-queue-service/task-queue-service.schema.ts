export interface TaskQueueServiceSchema {
  ROUTER_RESOLVED_URL: string;
  ROUTER_GENERATED_AUTH_TOKEN: string;
  envFilePath: string;
}

export type TaskQueueServiceKey = keyof TaskQueueServiceSchema;
