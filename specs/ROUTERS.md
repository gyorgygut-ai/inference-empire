# Routers

## apps/router

- Read: [Router](./apps/router/AGENTS.md)

**target: router-flux2**:

- dependencies: `flux2` worker project
- output (url): `GENERATE_IMAGE_SERVICE_URL`
- output (auth): `GENERATE_IMAGE_SERVICE_SECRET_AUTH_TOKEN`
- input (contract): [Flux2 Contract](./packages/contracts/flux2/contract.json)

**target: router-krea2**:

- dependencies: `krea2` worker project
- output (url): `GENERATE_IMAGE_1_SERVICE_URL`
- output (auth): `GENERATE_IMAGE_SERVICE_1_SECRET_AUTH_TOKEN`
- input (contract): [Krea2 Contract](./packages/contracts/krea2/contract.json)

**Activate**:

- `~/.agents/skills/wrangler`
