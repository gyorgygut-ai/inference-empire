import { formatFiles, joinPathFragments, logger, readJson, type Tree } from '@nx/devkit';
import { compile } from 'json-schema-to-typescript';

export interface JsonToTsGeneratorSchema {
  readonly contract?: string;
  readonly inference?: string;
  readonly api?: string;
  readonly output: string;
}

export async function jsonToTsGenerator(tree: Tree, options: JsonToTsGeneratorSchema): Promise<void> {
  if (options.output.length === 0) {
    throw new Error('output must be a non-empty workspace-relative path');
  }
  if (options.inference !== undefined || options.api !== undefined) {
    if (options.inference === undefined || options.inference.length === 0 || options.api === undefined || options.api.length === 0) {
      throw new Error('inference and api must both be non-empty workspace-relative paths');
    }
    const inference = readJson(tree, options.inference) as { input: unknown; output: unknown };
    if (inference.input === undefined || inference.output === undefined) {
      throw new Error(`inference ${options.inference} must contain ONLY input and output`);
    }
    const api = readJson(tree, options.api) as { inferRequest: unknown; inferResponse: unknown; inquireResponse: unknown };
    if (api.inferRequest === undefined || api.inferResponse === undefined || api.inquireResponse === undefined) {
      throw new Error(`api ${options.api} must contain inferRequest, inferResponse and inquireResponse`);
    }
    const input = await compile(inference.input as never, 'ContractInput', { bannerComment: '' });
    const output = await compile(inference.output as never, 'ContractOutput', { bannerComment: '' });
    const inferRequest = await compile(api.inferRequest as never, 'InferRequest', { bannerComment: '' });
    const inferResponse = await compile(api.inferResponse as never, 'InferResponse', { bannerComment: '' });
    const inquireResponse = await compile(api.inquireResponse as never, 'InquireResponse', { bannerComment: '' });
    tree.write(joinPathFragments(options.output), `${input}${output}${inferRequest}${inferResponse}${inquireResponse}`);
    await formatFiles(tree);
    logger.info(`Generated ${options.output} from ${options.inference} + ${options.api}`);
    return;
  }
  if (options.contract === undefined || options.contract.length === 0) {
    throw new Error('contract must be a non-empty workspace-relative path');
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
