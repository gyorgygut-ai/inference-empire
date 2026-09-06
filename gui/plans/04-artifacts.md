# Artifacts — R2 media only

## Scope
- Only `Artifact{presigned_url}` from `flux2/krea2/h3` (`../workers/AGENTS.md:42-44`, `../workers/flux2/_shared_flux2_klein9b.py:174-180`)
- `small_vision` JSON `classification/subjects/description` stays inline in chat, not artifacts

## Source
- Derived from current thread `useAuiState(s=>s.thread.messages)` filtered for `ImagePart | FilePart` with `presigned_url` (`architecture.md:167-175`)
- Not a global R2 feed

## UI
- `src/components/panels/Artifacts.tsx:11-25` keep `CollapsiblePanel side="right"` `forceMountContent` + `hidden data-[state=open]:block lg:block` filling remaining (`src/app/globals.css:3-14` + `AGENTS.md:30`)
- Replace `Artifacts todo` with thumbnail/video player + download/open
- Clear on refresh (`AGENTS.md:41`), expiry `3600s` (`../workers/services/storage/storage.py:3`) re-fetch on click

## Files
- edit `src/components/panels/Artifacts.tsx`
- new `src/lib/artifacts/types.ts`
- optional `src/hooks/useArtifacts.ts`
