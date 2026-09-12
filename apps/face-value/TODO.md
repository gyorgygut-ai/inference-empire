# TODO: Actionable Tasks

## 🔄 Agent Workflow & Testing Rules

- **Workflow**: Plan → Dev implements → Test proposes cases → User approves → Test implements (red) → Dev fixes (green) → Verify.
- **Framework**: Vitest + React Testing Library
- **Scope**: One test file per component or Server Action
- **Philosophy**: Test behaviour, not implementation
- **Coverage**: Empty, single, many, loading, success, error states as defined in SPECS

## ✅ Done

- Strip default Next.js boilerplate
- Static Server Component shell with outcome loading
- `useActionState`, `useFormStatus`, `useOptimistic`
- Image upload, validation, resize, base64
- Inference payload + call, error propagation
- `<a download>` for generated image
- CF JWT verification in `middleware.ts` via `jose`, redirect on invalid token
- Origin URL kept private via env vars, CF as only entry point
- Env vars optional-gated — middleware no-op without CF vars set

## 🎁 Nice to Haves

- [ ] `fetch` cache: cache key = image hash + outcome id, `revalidate: false`
- [ ] Layout: fields side-by-side via inline wrapping, button centered

## 🔐 Access

- [ ] Configure Cloudflare Access email OTP for domain gating
- ~~`proxy.ts`: CF JWT verification with `jose` against CF public certs, redirect on invalid token~~ ✅
- ~~Ensure origin URL remains private — CF as only entry point~~ ✅

## 🚀 Production Setup

- ~~`proxy.ts` routing logic (pre-auth, origin proxying only)~~ ✅
- [ ] Enable React Compiler in `next.config.ts`
- [ ] Complete `.agents/` definitions (`developer`, `doc-writer`, `test-engineer`)
- [ ] Deploy

## 🧪 Tests

- [ ] Outcome loading (empty, 1, many), `<select>` population, static shell render
- [ ] Form states, error display, optimistic UI, loading state, download link
- [ ] File validation, server action error paths, payload preparation
- [ ] Outcome resolution, payload structure, inference error propagation
- [ ] Cache behavior (cache key = hash + outcome id)
- [ ] JWT validation paths, redirect on invalid token, auth header injection
