# Apple Shortcuts

macOS/iOS automation via Apple's Shortcuts app.

## Kickoff

1. Create your shortcuts in the Shortcuts app
2. Run: `nx run apple-shortcuts:<target>`

## Targets

- `run` — run a shortcut
- `run-input` — run with text input
- `reminders` — create/query/complete
- `notes` — create/append/search
- `calendar` — create/query events

## Artifact Production

Shortcuts are generated and stored in `packages/apple-shortcuts/artifacts/`.

Each shortcut has two versions:

- `<name>_unsigned.shortcut` — raw binary plist, produced by the generator
- `<name>.shortcut` — signed version, produced by running `shortcuts sign -i <name>_unsigned.shortcut -o <name>.shortcut`

The unsigned version is used for version control. The signed version is drag-and-drop ready.