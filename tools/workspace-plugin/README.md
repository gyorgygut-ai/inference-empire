# workspace-plugin

Local Nx plugin, loaded from source: `nx.json` registers `src/inference/python.ts`, and
`executors.json` / `generators.json` resolve straight to the TypeScript implementations.
There is no build step.

## Inference

`src/inference/python.ts` matches `apps/**/worker_*.py` and infers, per family root
(`apps/<family>` or `apps/workers/<family>`):

`audit-uv` · `ruff` · `ty` · `vulture` · `audit` · `lint` · `test-unit` · `test-e2e` · `test` · `verify`

`build` is merged with whatever the project declares.

## Executors

| Executor | Runs |
| --- | --- |
| `audit-uv` | `uv pip check` |
| `ruff` | `uvx ruff check <projectRoot>` |
| `ty` | `uv run --locked --group test ty check <projectRoot>` |
| `vulture` | `uv run --locked --group test vulture <projectRoot>` |
| `pytest` | `uv run --locked --group test pytest <projectRoot>/tests/ -k "<unit\|e2e>"` |

All take `projectRoot` (workspace-relative), not a bare family name.

## Generators

- `gpu-family` — scaffolds `apps/workers/<family>/` (shared logic, tests, project.json) and `packages/schemas/<family>/schema.json`
- `ts-app` — scaffolds an app under `apps/`
- `ts-lib` — scaffolds a lib under `packages/`

```bash
npx nx g @inference/workspace-plugin:gpu-family tiny_sd
```
