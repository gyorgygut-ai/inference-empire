export interface ContractModule {
  keys: readonly string[];
  envFilePath: string;
  resolvers?: Record<string, string>;
}

export interface RunCommandExecutorSchema {
  command: string;
  args?: string;
  env?: Record<string, string>;
  cwd?: string;
}
