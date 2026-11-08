# Face Value

**Value Proposition**: NextJS chat app that turns you into a hotdog 
**Production URL**: [face-value.gyorgygutai.dev](https://face-value.gyorgygutai.dev)

---

## Getting Started

First, run the development server:

```bash
npm i
npx nx run face-value:dev
```

The workspace root `.env` is the shared configuration source. Local Nx commands decrypt it using the `DOTENV_PRIVATE_KEY` resolved from the ignored `.env.keys` file. Keep `.env.keys` outside Git. Use `dotenvx set KEY value` to add or rotate encrypted values.

Open [http://localhost:3050](http://localhost:3050) with your browser to see the result.

## Agents

See [AGENTS.md](./AGENTS.md).
