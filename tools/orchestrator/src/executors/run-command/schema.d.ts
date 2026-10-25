export interface ContractModule {
  keys: readonly string[];
  envFilePath: string;
}

export interface ContractNeed {
  contract: string;
  contractKey?: string;
}

export interface ContractFulfillment {
  contract: string;
  contractKey: string;
}

export interface RunCommandExecutorSchema {
  command: string;
  args?: string;
  env?: Record<string, string>;
  envFile?: string;
  envKey?: string;
  cwd?: string;
  needs?: ContractNeed[];
  fulfills?: ContractFulfillment[];
}
