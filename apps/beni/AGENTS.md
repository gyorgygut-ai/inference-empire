# Beni App

Vanilla-TS Vite frontend for `router-krea2`.

**Runtime**:

- No artifact consumed, no `VITE_*` required.
- Defaults to `http://127.0.0.1:4202` with manual override input.
- Calls `POST /q` and `GET /sup` with manual `Bearer` token input.

---

## NX target: `beni:dev`

**:dev**:

- **depends**: `router:router-krea2` (ordering only)
- **command**: `vite --port 4300 --strictPort`
