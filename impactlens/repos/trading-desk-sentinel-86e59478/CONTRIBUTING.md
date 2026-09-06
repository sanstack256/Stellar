# Contributing

This is a small, four-package repo (`mcp-server`, `agent`, `skills`, `client`,
`ui`) wired together with npm workspaces at the root.

## Setup

```bash
npm install   # installs and links all workspaces from the repo root
```

## Before opening a PR

```bash
npm run lint                          # eslint across every workspace, zero errors required
npm run typecheck                     # tsc --noEmit across every workspace
npm run build --workspace mcp-server  # required first on a fresh clone — the test
                                       # suite below spawns dist/index.js directly
npm run test                          # vitest — mcp-server's suite spawns the real server
npm run build                         # production build for mcp-server, client, and ui
```

This is also the exact order `.github/workflows/ci.yml` runs on every PR.

## Verification standard for this repo

Every non-trivial change should be checked by actually running it, not just
read back — that's the standard the rest of this codebase was held to:

- A protocol or schema claim (an MCP tool annotation, a TrueForge event
  shape, an SDK method signature) gets checked against the real, installed
  package — `.d.ts` files under `node_modules`, or a live request/response —
  not assumed from memory or docs prose. Several real bugs in this repo were
  only found this way (see the README's "What's verified vs. what needs a
  live TrueForge instance" section for specifics).
- A UI change that touches the investigation transcript or the approval gate
  should be checked against `ui/src/App.e2e.test.tsx`, which drives the real
  component through a full investigation using an inline mock TrueForge
  server built directly in the test file (not `mock-server/`, which is a
  separate standalone server for manual `npm run dev` testing — update both
  if you're changing an event shape).
- Prefer adding a test that would have caught a bug over just fixing the bug.

## Qodo

This repo requires every substantive PR to go through Qodo's automated
review before merging (see the PR template). If Qodo flags something you
disagree with, leave a one-line reply explaining why — don't just dismiss
it silently.
