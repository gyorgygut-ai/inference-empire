# dotenvx executor

`dotenvx:run-commands` delegates to Nx's `run-commands` executor after expanding
`options.env` with dotenvx. It uses a copy of the task environment, so concurrent
targets do not mutate each other's variables.

Use `options.env` for `${VARIABLE}` references and `$(command)` substitutions.
Use `options.args` for CLI arguments; the command's shell expands `$VARIABLE`.
All other options and the executor context pass through to Nx unchanged.

```json
{
  "executor": "dotenvx:run-commands",
  "options": {
    "env": { "AUTH_TOKEN": "${GENERATED_AUTH_TOKEN}" },
    "command": "npx wrangler dev",
    "args": "--port=\"$ROUTER_PORT\""
  }
}
```
