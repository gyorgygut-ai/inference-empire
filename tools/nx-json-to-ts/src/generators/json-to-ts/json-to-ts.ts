import { formatFiles, joinPathFragments, logger, readJson, type Tree } from '@nx/devkit';
import { compile } from 'json-schema-to-typescript';

export interface JsonToTsGeneratorSchema {
  readonly contract: string;
  readonly output: string;
}

export async function jsonToTsGenerator(tree: Tree, options: JsonToTsGeneratorSchema): Promise<void> {
  if (options.contract.length === 0 || options.output.length === 0) {
    throw new Error('contract and output must be non-empty workspace-relative paths');
  }
  const contract = readJson(tree, options.contract) as { input: unknown; output: unknown };
  if (contract.input === undefined || contract.output === undefined) {
    throw new Error(`contract ${options.contract} must contain ONLY input and output`);
  }
  const input = await compile(contract.input as never, 'ContractInput', { bannerComment: '' });
  const output = await compile(contract.output as never, 'ContractOutput', { bannerComment: '' });
  tree.write(joinPathFragments(options.output), `${input}${output}`);
  await formatFiles(tree);
  logger.info(`Generated ${options.output} from ${options.contract}`);
}

export default jsonToTsGenerator;
