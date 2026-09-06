## What changed and why

<!-- One or two sentences. Link an issue if there is one. -->

## Verification

- [ ] `npm run typecheck` passes (all workspaces)
- [ ] `npm run lint` passes with zero errors
- [ ] `npm run test` passes (mcp-server's integration suite spawns a real server — see `mcp-server/src/index.test.ts`)
- [ ] If this touches `mcp-server/src/index.ts`: the six tools still list with the correct `readOnlyHint`/`destructiveHint` annotations (covered by the test above, but re-check by eye if you touched annotations directly)
- [ ] If this touches `ui/src/App.tsx`'s event handling: `ui/src/App.e2e.test.tsx` still passes (its mock TrueForge server is inline in the test file, separate from `mock-server/`)

## Qodo review

- [ ] Qodo's automated review has run on this PR
- [ ] Every finding was either fixed or has a one-line reply explaining why it was left as-is
