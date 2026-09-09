# Nx Migration Plan

## Current State
This is a polyglot monorepo containing:
- Python inference workers (Modal, Beam, Flash)
- Next.js chat UI
- Cloudflare Worker proxy
- Shared CLI tooling

## Target Structure

```
inference-tooling/
├── apps/
│   ├── chat-ui/              # Next.js frontend (from gui/)
│   ├── infra-router/         # Cloudflare Worker (from proxy/)
│   └── gpu-workers/          
│       ├── flux2/            # Colocated contracts + workers
│       ├── krea2/
│       └── tiny_sd/
├── packages/
│   ├── contracts/            # Shared JSON schemas (source of truth)
│   ├── workers-core/         # Shared Python modules
│   └── types/                # Shared TypeScript definitions
├── tools/
│   ├── cli/                  # Developer CLI tools
│   ├── executors/            # Custom Nx executors
│   └── generators/           # Code scaffolding generators
├── workers/                  # KEEP - legacy structure
├── nx.json
├── package.json
└── workspace.json
```

## Project Mapping

| Current Path | New Path | Type |
|-------------|----------|------|
| gui/ | apps/chat-ui/ | Application |
| proxy/ | apps/infra-router/ | Application |
| workers/*/contracts/*.json | packages/contracts/ | Library |
| workers/services/* | packages/workers-core/ | Library |
| workers/*/[worker_*.py] | apps/gpu-workers/*// | Application Modules |
| workers/*/tests/ | apps/gpu-workers/*//tests/ | Tests |
| cli/ | tools/cli/ | Tool |
| Makefile targets | Nx targets | Task Abstraction |

## Nx Targets to Implement

- `build`: For TypeScript applications and packages
- `test`: Python and JavaScript unit/e2e tests
- `lint`: Code quality across languages
- `deploy-modal`: Custom executor for Modal deployments
- `deploy-beam`: Custom executor for Beam deployments
- `deploy-flash`: Custom executor for Flash deployments
- `verify-deploy-gate`: Dependency resolution validation
- `build-manifest`: Generated task from contract schemas to UI inputs

## Custom Executors Needed

1. `@inference/modal-deploy` - Wraps `modal deploy` commands
2. `@inference/beam-deploy` - Wraps Beam task queue submissions
3. `@inference/flash-deploy` - Wraps Flash CLI deployment
4. `@inference/python-test` - Executes pytest with proper environment setup

## Custom Generators Needed

1. `@inference/create-model` - Scaffolds new model directories with contracts
2. `@inference/create-worker` - Generates worker implementations per platform
3. `@inference/create-contract` - Creates validated JSON schema contracts

## Migration Steps

1. Initialize Nx workspace in existing repo
2. Migrate TypeScript projects first (lowest risk)
3. Restructure Python worker directories preserving contracts
4. Implement custom executors for deployment workflows
5. Migrate CLI tooling to Nx generator/plugins
6. Update CI/CD pipelines to use Nx commands
7. Validate full test suite passes
8. Archive legacy paths after verification

## Risks

- Potential breaking changes to existing import paths
- Need to maintain dual structure temporarily
- Custom executor maintenance burden
- Coordination between JavaScript/Nx tooling and Python deployment systems
