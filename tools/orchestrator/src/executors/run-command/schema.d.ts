export interface RunCommandExecutorSchema {
  command: string;
  args?: string[];
  envFile?: string;
  key?: string;
  env?: Record<string, string>;
}
