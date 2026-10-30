# voice-chat

A Next.js chat shell using TanStack AI UI wiring. It starts with an empty thread and no custom tools.

## Run

Use `npx dotenvx run -f config.dev -- npx nx run voice-chat:dev` from the workspace root. The app port is configured with `VOICE_CHAT_PORT`; dev also deploys and resolves the voice worker URL.

## Deploy

Use `npx dotenvx run -f config.deploy -- npx nx run voice-chat:deploy`. Configure `SECRET_VOICE_CHAT_VERCEL_TOKEN`, `SECRET_VOICE_CHAT_VERCEL_ORG_ID`, and `SECRET_VOICE_CHAT_VERCEL_PROJECT_ID`.
