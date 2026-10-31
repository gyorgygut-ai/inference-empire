# Schemas

**Source of Truth**:

- `env/*.schema.json` and `workers/*.schema.json` are the language-agnostic source of truth, including the workspace runtime config contract.
- Keep provider and worker contract files flat inside their respective directories.
- Generated TypeScript and Python files are outputs; never edit them by hand.

**Generators**:

- `build-ts`: converts a JSON Schema to a Zod schema and TypeScript types.
  - **Options**: `source`, `out`
- `build-pydantic`: converts a JSON Schema to Pydantic v2 models with `datamodel-code-generator`.
  - **Options**: `source`, `out`
- Both targets receive `source` and `out` from their consuming target with Nx `options: "forward"`.
- Workspace-config cross-field constraints that JSON Schema cannot express live in the handwritten `config.schema.ts` wrapper around the generated `env/config.schema.ts`; never edit the generated file by hand.

**Consumers**:

- `router:prebuild` generates the TypeScript contracts into `apps/router/dist/`.
- `workers-{family}:predeploy` generates the Pydantic contract inside that worker project.
- Worker `predeploy` generates Pydantic modules into worker-local `dist/`; these generated files are ignored and included in deployment bundles. Import them from `dist.*`; do not hand-edit generated files.

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
    "out": "apps/router/dist/flux2.schema.ts"
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
    "out": "apps/workers/flux2/dist/contract_flux2.py"
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
