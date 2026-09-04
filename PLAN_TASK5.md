# Plan: Write PLAN_TESTING.md (conftest refactoring plan)

## Goal
Create `PLAN_TESTING.md` documenting the full conftest refactoring plan as the canonical reference for Task 2.

## Content
- **Problem statement**: Why current conftest.py is unmaintainable (504 lines, if/elif factories, global state, useless proxies)
- **Current structure breakdown**: What each section of conftest.py does (mock installers, proxies, factories, routing, fixtures)
- **Target architecture**: WorkerRegistry dict → WorkerFactory.make() → WorkerProxy → platform/runner fixtures
- **Migration steps**: File-by-file changes needed
- **Code snippets**: The new WorkerRegistry, WorkerProxy, fixture definitions
- **Verification criteria**: `--target fake` and `--target live` test suites pass

## Relation to PLAN_TASK2.md
PLAN_TASK2.md contains the technical plan for execution. PLAN_TESTING.md serves as the human-readable reference that can be read without knowing the codebase. It's the authoritative document for the testing harness redesign.

## Execution
Write PLAN_TESTING.md with:
1. Current state analysis (with line references)
2. Problems identified
3. Target design
4. Step-by-step migration plan
5. Verification steps

## Done when
PLAN_TESTING.md exists and contains all above sections. PLAN_TASK2.md is the execution checklist; PLAN_TESTING.md is the reference doc.