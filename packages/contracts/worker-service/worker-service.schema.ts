export interface WorkerServiceSchema {
  WORKER_RESOLVED_BEAM_URL: string;
  WORKER_RESOLVED_MODAL_URL: string;
  WORKER_RESOLVED_FLASH_URL: string;
  envFilePath: (taskName: string) => string;
}

export type WorkerServiceKey = keyof WorkerServiceSchema;
