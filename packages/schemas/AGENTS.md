# Schemas

**JSON -> Zod**:

- **Tool**: `{projectRoot}/tools/generate-zod-from-json`
- **Problem**: Need to generate zod schemas from json
- **Approach**: One `build` target, `configurations` for models
- **Outcome**: `.json` as source of truth; `schema.ts` generated
