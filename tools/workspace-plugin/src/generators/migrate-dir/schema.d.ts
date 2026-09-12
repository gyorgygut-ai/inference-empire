export interface MigrateDirGeneratorSchema {
  from: string;
  to: string;
  kind: 'app' | 'lib' | 'tool';
  skipMove?: boolean;
}
