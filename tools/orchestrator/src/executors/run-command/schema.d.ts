export interface RunCommandExecutorSchema {
  command: string;
  args?: string;
  env?: Record<string, string>;
  envFile?: string;
  envKey?: string;
  cwd?: string;
  needs?: {
    contract: string;
    contractKey: string;
  };
  fulfills?: {
    contract: string;
    contractKey: string;
  };
}
