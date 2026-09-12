---
description: Worker drift - unit + e2e gaps
agent: build
---
Test-workers: $ARGUMENTS
Check worker/contract drift, run unit (`-k "not e2e"`), list missing e2e pairs. 100% or fail. No live calls.
