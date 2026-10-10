import {
  createNodesFromFiles,
  readJsonFile,
  type CreateNodesV2,
  type TargetConfiguration,
  type TargetDependencyConfig,
} from "@nx/devkit";
import { dirname, join } from "node:path";

function fail(message: string): never {
  throw new Error(`[nx-orchestrate-configurations] ${message}`);
}

type TargetDef = {
  executor?: string;
  options?: Record<string, unknown>;
  dependsOn?: Array<string | TargetDependencyConfig>;
  inputs?: unknown[];
  outputs?: string[];
  cache?: boolean;
};

function readBaseTargets(projectRoot: string): Record<string, TargetDef> {
  try {
    const projectJson = readJsonFile(join(projectRoot, "project.json")) as Record<
      string,
      unknown
    >;
    const targets = projectJson["targets"];
    if (targets !== null && typeof targets === "object" && !Array.isArray(targets)) {
      return targets as Record<string, TargetDef>;
    }
  } catch {
    // no readable project.json; base lookup fails per entry below
  }
  return {};
}

function isSelfRef(dep: string | TargetDependencyConfig, name: string): boolean {
  if (dep === name) {
    return true;
  }
  if (dep !== null && typeof dep === "object" && !Array.isArray(dep)) {
    return (dep as TargetDependencyConfig).target === name;
  }
  return false;
}

function createNodesInternal(configFilePath: string): {
  projects: Record<string, { targets: Record<string, TargetConfiguration> }>;
} {
  const projectRoot = dirname(configFilePath);
  const baseTargets = readBaseTargets(projectRoot);
  let raw: Record<string, unknown>;
  try {
    raw = readJsonFile(configFilePath) as Record<string, unknown>;
  } catch {
    fail(`cannot read ${configFilePath}`);
  }
  if (!Array.isArray(raw["targets"])) {
    fail(`${configFilePath} must contain a "targets" array`);
  }
  const targets: Record<string, TargetConfiguration> = {};
  for (const entry of raw["targets"] as Array<Record<string, unknown>>) {
    if (
      typeof entry["name"] !== "string" ||
      (entry["name"] as string).length === 0
    ) {
      fail(`${configFilePath}: every entry needs a non-empty "name"`);
    }
    const name = entry["name"] as string;
    if (typeof entry["base"] !== "string" || (entry["base"] as string).length === 0) {
      fail(`${configFilePath}: entry "${name}" needs a non-empty "base" target`);
    }
    const baseName = entry["base"] as string;
    const base = baseTargets[baseName];
    if (base === undefined) {
      fail(
        `${configFilePath}: entry "${name}" base "${baseName}" not found in ${projectRoot}/project.json`
      );
    }
    const executor =
      (entry["executor"] as string | undefined) ?? base.executor;
    if (typeof executor !== "string" || executor.length === 0) {
      fail(`${configFilePath}: entry "${name}" resolves to no executor`);
    }
    const entryOptions =
      (entry["options"] as Record<string, unknown> | undefined) ?? {};
    const baseOptions = base.options ?? {};
    const options: Record<string, unknown> =
      entry["executor"] !== undefined && entry["executor"] !== base.executor
        ? { ...entryOptions }
        : { ...baseOptions, ...entryOptions };
    const target: TargetConfiguration = { executor };
    if (Object.keys(options).length > 0) {
      target["options"] = options;
    }
    const entryDependsOn =
      (entry["dependsOn"] as Array<string | TargetDependencyConfig> | undefined) ?? [];
    const dependsOn = [...(base.dependsOn ?? []), ...entryDependsOn].filter(
      (dep) => !isSelfRef(dep, name)
    );
    if (dependsOn.length > 0) {
      target["dependsOn"] = dependsOn;
    }
    const inputs: unknown[] = [];
    const seenInputs = new Set<string>();
    const pushInput = (input: unknown): void => {
      const key =
        input !== null && typeof input === "object" ? JSON.stringify(input) : String(input);
      if (!seenInputs.has(key)) {
        seenInputs.add(key);
        inputs.push(input);
      }
    };
    for (const input of base.inputs ?? []) {
      pushInput(input);
    }
    if (entry["contract"] !== undefined) {
      pushInput(`{workspaceRoot}/${entry["contract"] as string}`);
    }
    for (const envName of (entry["env"] as string[] | undefined) ?? []) {
      pushInput({ env: envName });
    }
    for (const input of (entry["inputs"] as unknown[] | undefined) ?? []) {
      pushInput(input);
    }
    if (inputs.length > 0) {
      target["inputs"] = inputs as TargetConfiguration["inputs"];
    }
    const outputs =
      (entry["outputs"] as string[] | undefined) ?? base.outputs;
    if (outputs !== undefined) {
      target["outputs"] = outputs;
    }
    const cache = (entry["cache"] as boolean | undefined) ?? base.cache;
    if (cache !== undefined) {
      target["cache"] = cache;
    }
    targets[name] = target;
  }
  return { projects: { [projectRoot]: { targets } } };
}

export const createNodesV2: CreateNodesV2 = [
  "apps/*/project-targets.json",
  async (configFiles, options, context) => {
    return await createNodesFromFiles(
      (configFile) => createNodesInternal(configFile),
      configFiles,
      options,
      context,
    );
  },
];

export const createNodes = createNodesV2;
