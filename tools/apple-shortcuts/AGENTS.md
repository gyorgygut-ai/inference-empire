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

Shortcuts are generated and stored in `tools/apple-shortcuts/artifacts/`.

Each shortcut has two versions:

- `<name>_unsigned.shortcut` — raw binary plist, produced by the generator
- `<name>.shortcut` — signed version, produced by running `shortcuts sign -i <name>_unsigned.shortcut -o <name>.shortcut`

The unsigned version is used for development and version control. The signed version is drag-and-drop ready for the Shortcuts app and does not trigger the "importing unsigned shortcuts not supported" warning.

## Dirigera Shortcuts

Created for testing the IKEA Dirigera hub API:

- `dirigera-list-devices_unsigned.shortcut` — lists all connected devices via GET `/v1/devices`
- `dirigera-toggle-plug_unsigned.shortcut` — toggles Plug 1 (`dee49759-bb38-4a48-a048-b193d5128dbf_1`) on/off via GET/PATCH `/v1/devices/{deviceId}`

Both shortcuts hardcode the auth token and use the "Get Contents of URL" action.

## Signing

To sign a shortcut:

```bash
shortcuts sign -i tools/apple-shortcuts/artifacts/<name>_unsigned.shortcut -o tools/apple-shortcuts/artifacts/<name>.shortcut
```

The signed `.shortcut` file is the one you drag into the Shortcuts app.