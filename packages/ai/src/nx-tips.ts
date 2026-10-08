/**
 * A small curated set of Nx tips, surfaced by the `getNxTip` tool.
 * Kept in the shared lib so both the server tool and any future UI can use it.
 */
export interface NxTip {
  id: number;
  category: 'caching' | 'tasks' | 'graph' | 'generators' | 'ci' | 'cloud';
  tip: string;
  command?: string;
}

export const NX_TIPS: ReadonlyArray<NxTip> = [
  {
    id: 1,
    category: 'caching',
    tip: 'Nx caches task outputs locally. Re-running an unchanged task is instant - it replays the cached result instead of doing the work again.',
    command: 'nx run-many -t build',
  },
  {
    id: 2,
    category: 'tasks',
    tip: 'Use affected commands to run only the projects touched by your changes. Great for fast CI.',
    command: 'nx affected -t build,test,lint',
  },
  {
    id: 3,
    category: 'graph',
    tip: 'Visualize how your projects depend on each other with the interactive project graph.',
    command: 'nx graph',
  },
  {
    id: 4,
    category: 'generators',
    tip: 'Generators scaffold consistent code. Add --dry-run to preview the changes before writing them.',
    command: 'nx g @nx/js:library my-lib --dry-run',
  },
  {
    id: 5,
    category: 'cloud',
    tip: 'Nx Cloud adds remote caching so your whole team and CI share one cache. Connect in one command.',
    command: 'nx connect',
  },
  {
    id: 6,
    category: 'ci',
    tip: 'Nx Cloud distributes tasks across multiple agents in parallel, cutting wall-clock CI time dramatically.',
  },
  {
    id: 7,
    category: 'tasks',
    tip: 'Run a single target across every project that defines it with run-many.',
    command: 'nx run-many -t test',
  },
  {
    id: 8,
    category: 'graph',
    tip: 'Tag projects with scope: and type: tags, then enforce module boundaries so apps cannot import each other.',
  },
  {
    id: 9,
    category: 'caching',
    tip: 'Define inputs and outputs precisely in project.json so the cache stays correct and never serves a stale result.',
  },
  {
    id: 10,
    category: 'cloud',
    tip: 'Self-healing CI uses Nx Cloud to detect flaky tasks and re-run them automatically, so flakes do not block your team.',
  },
];

export function getRandomNxTip(): NxTip {
  const index = Math.floor(Math.random() * NX_TIPS.length);
  return NX_TIPS[index];
}

export function getNxTipsByCategory(category: NxTip['category']): NxTip[] {
  return NX_TIPS.filter((t) => t.category === category);
}
