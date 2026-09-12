# Rules for Agents

## Critical Specs

- [Specifications](./specs/SPECS.md)
- [NextJS Docs](./node_modules/next/dist/docs/)

## Golden Rules

- Specs are authoritative — code must match them
- STRICTLY no touching, editing, removal of any file, no git commands
- User MUST approve agent suggestion before any file operation
- No meta-commentary or context-aware talk in code, docs or commits
- No assumptions, inference or helpfulness creep; do the task as requested
- Exact touched files and lines to finish task; no less, no more
- Any suggestion, conflict, flaw can and should be raised upon finishing task
- A question is not a command; questions need answers, commands need action
- No cutting corners, slacking, fabricating or lying; if task is not clear, say it
- Adherence to requirements, key decisions and golden rules is non-negotiable

---

## Workflow

**Read before writing code**:

- [Specifications](./specs/SPECS.md)

**Coding Rules**:

- No kindergarten level code comments; adults write clean code
- Any code change only while keeping requirements, old or new, intact
- If user request directly contradicts any of the former, raise it boldly
- No direct editing of generated files, npm packages or OpenAPI specs
- ESLint rules are non-negotiable; all code must pass linting

**Versioning and Commits**:

- Bump version when requested adhering to semver
- Conventional commits, sentence case, no period
