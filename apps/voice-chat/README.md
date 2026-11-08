# voice-chat

A Next.js chat shell using TanStack AI UI wiring. It starts with an empty thread and no custom tools.

## Run

Use `npx nx run voice-chat:dev` from the workspace root. Local Nx commands decrypt the root `.env` using the `DOTENV_PRIVATE_KEY` resolved from the ignored `.env.keys` file. Keep `.env.keys` outside Git. The app port is configured with `DEV_VOICE_CHAT_PORT`, and dev also deploys and resolves the voice worker URL.

## Deploy

Use `npx nx run voice-chat:deploy`. Configure `SECRET_VOICE_CHAT_VERCEL_TOKEN`, `SECRET_VOICE_CHAT_VERCEL_ORG_ID`, and `SECRET_VOICE_CHAT_VERCEL_PROJECT_ID` in the root `.env`. Add or rotate encrypted values with `dotenvx set KEY value`; keep the decryption key outside Git.
