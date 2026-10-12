# Acceptance Testing Patterns

This directory contains the acceptance testing patterns for generative-ui:

## Overview

This pattern defines the acceptance criteria for the generative-ui:face-value target.

## Required Setup

1. Clean `dist` folder before running tests
2. Start all dependent workers (router-flux2:dev-modal, router-flux2:dev)
3. Verify all artifacts are generated

## Test File Structure

Each test file in this directory tests acceptance criteria for a specific target:

- `acceptance-dev.coverage.spec.ts` - Tests for generative-ui:face-value:dev
- `acceptance-deploy.coverage.spec.ts` - Tests for generative-ui:face-value:deploy

## Test Patterns

### 1. Artifact Verification Tests
Check that required artifacts exist and have the correct format:
- Environment files (`.env` format) contain required variables
- TypeScript files contain proper imports/usage
- Generated files are correctly formatted

### 2. Authentication Flow Tests
Verify that all routes respect authentication:
- Unauthenticated requests get 401
- Bad tokens get 401
- Valid tokens succeed

### 3. Integration Tests
End-to-end testing with real services:
- Submit tasks to router
- Poll task status
- Wait for completion

## Critical Success Criteria

All tests must pass when the system is in a clean, verified state:
1. No hardcoded URLs or tokens in generated code
2. All environment variables properly distributed
3. Router authentication works correctly
4. All routes (POST /q, GET /sup) respond correctly
5. Face-value app runs on correct port (3000)
6. Router runs on correct port (4201)
