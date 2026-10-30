# Schemas

**Source of Truth**:

- `env/*.schema.json` and `workers/*.schema.json` are the language-agnostic source of truth.
- Keep provider and worker contract files flat inside their respective directories.
- Generated TypeScript and Python files are outputs; never edit them by hand.

**Generators**:

- `build-ts`: converts a JSON Schema to a Zod schema and TypeScript types.
  - **Options**: `source`, `out`
- `build-pydantic`: converts a JSON Schema to Pydantic v2 models with `datamodel-code-generator`.
  - **Options**: `source`, `out`
- Both targets receive `source` and `out` from their consuming target with Nx `options: "forward"`.

**Consumers**:

- `functions:router:prebuild` generates the TypeScript contract into `apps/functions/dist/`.
- `workers-{family}:predeploy` generates the Pydantic contract inside that worker project.
- Worker generation must not use `dist/` or overwrite hand-maintained `shared/contract_*.py` files.

```json
{
  "dependsOn": [
    {
      "projects": ["schemas"],
      "target": "build-ts",
      "options": "forward"
    }
  ],
  "options": {
    "source": "packages/schemas/workers/flux2.schema.json",
    "out": "apps/functions/dist/flux2.schema.ts"
  }
}
```

```json
{
  "dependsOn": [
    {
      "projects": ["schemas"],
      "target": "build-pydantic",
      "options": "forward"
    }
  ],
  "options": {
    "source": "packages/schemas/workers/flux2.schema.json",
    "out": "apps/workers/flux2/shared/generated/flux2.schema.py"
  }
}
```

**Pydantic Command**:

```bash
datamodel-codegen \
  --input {options.source} \
  --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel \
  --output {options.out}
```
