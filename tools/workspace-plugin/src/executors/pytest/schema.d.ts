export interface PytestExecutorSchema {
  projectRoot: string;
  mode?: 'unit' | 'e2e';
}
