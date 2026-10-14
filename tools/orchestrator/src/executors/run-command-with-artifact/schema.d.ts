export interface RunCommandWithArtifactExecutorSchema {
  command: string;
  args?: string[];
  artifact: string;
  cwd?: string;
  timeout?: number;
}