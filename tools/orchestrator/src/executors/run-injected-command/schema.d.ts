export interface RunInjectedCommandExecutorSchema {
  command: string;
  inject: Array<{ env: string; command: string; artifact?: string; args?: string[] }>;
  artifact?: string;
  cwd?: string;
  timeout?: number;
}