import { formatFiles, joinPathFragments, logger, readJson, type Tree } from '@nx/devkit';
import { compile } from 'json-schema-to-typescript';

export interface JsonToTsGeneratorSchema {
  readonly inference: string;
  readonly api: string;
  readonly output: string;
}

export async function jsonToTsGenerator(tree: Tree, options: JsonToTsGeneratorSchema): Promise<void> {
  if (options.output.length === 0) {
    throw new Error('output must be a non-empty workspace-relative path');
  }
  if (!/(^|\/)generated\/[^/]+_[^/]+\.ts$/.test(options.output)) {
    throw new Error(`output must match generated/{target}_{filename}.ts, got ${options.output}`);
  }
  if (!options.inference || options.inference.length === 0) {
    throw new Error('inference must be a non-empty workspace-relative path');
  }
  if (!options.api || options.api.length === 0) {
    throw new Error('api must be a non-empty workspace-relative path');
  }

  const inferenceSchema = readJson(tree, options.inference);
  const apiSchema = readJson(tree, options.api);
  
  // Combine both schemas into one for type generation
  const combinedSchema = {
    ...inferenceSchema,
    ...apiSchema,
    properties: {
      ...(inferenceSchema.properties || {}),
      ...(apiSchema.properties || {}),
    },
    required: [
      ...(inferenceSchema.required || []),
      ...(apiSchema.required || []),
    ],
  };

  const result = await compile(combinedSchema, 'GeneratedSchema', { bannerComment: '' });
  
  tree.write(joinPathFragments(options.output), result);
  await formatFiles(tree);
  logger.info(`Generated ${options.output} from ${options.inference} and ${options.api}`);
}

export default jsonToTsGenerator;
