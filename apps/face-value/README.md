# face-value

[https://face-value.gyorgygutai.dev](https://face-value.gyorgygutai.dev/)

## What This Is

- Upload a photo of yourself
- Pick an outcome
- Get a generated image back
- A [Next.js 16](https://nextjs.org) feature showcase — all architectural decisions built around this
- [Flux.2 Klein 9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) as the image model
- `worker-router-flux2` Cloudflare Worker as the inference backend (Modal/Flash/Beam providers behind it)
- [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/applications/) as auth
- Tailwind v4 + assistant-ui chat interface

## Getting Started

First, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Next.js Features Demonstrated

See [SPECS.md](./SPECS.md) for full decisions and reasoning.

## How To Run It

### Environment Variables

See [env.schema.ts](./env.schema.ts) for required variables.

### Dev

```bash
npm i
npm run schema:generate
npm run dev
```

### Deploy

```bash
npm run build
```

Deploy to any Node.js host. Ensure your domain is proxied through Cloudflare with Access enabled.

## Agents

See [AGENTS.md](./AGENTS.md).
