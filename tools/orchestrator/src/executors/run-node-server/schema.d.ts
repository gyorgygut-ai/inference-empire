export interface RunNodeServerExecutorSchema {
  command: string;
  args?: string[];
  envFile?: string;
  key?: string;
  env?: Record<string, string>;
}
