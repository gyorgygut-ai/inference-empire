# Shared Chat UI

**Structure**:

- `chat/components/`: chat ui `components`
- `chat/components/Layout.tsx`
- `chat/components/Message.tsx`
- `chat/parts/{.ts}`: a `part factory` per file
- `chat/parts/components/`: `partsComponents`, one per file

**Non-negotiables**:

- USE `@tanstack/ai/*`; utilize the library fully, no hand-rolling
- NO hand-rolled ui; NO state management; `@tanstack/ai` does it
- NO `useEffect`, `useState`; state travels through tools
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO auth tokens or other secrets exposed to the browser
