---
name: Codegen before typecheck
description: The required order of operations when changing the OpenAPI spec in this repo
---

## Rule
Always run codegen before running the frontend typecheck. The codegen command also runs `typecheck:libs` internally.

```
pnpm --filter @workspace/api-spec run codegen
```

Then:
```
pnpm --filter @workspace/osint-app run typecheck
```

## Why
The frontend imports generated types from `@workspace/api-client-react`. If the OpenAPI spec adds new fields (e.g. `confidence_level`, `propaganda_score`) but codegen hasn't run, `tsc` will error on those fields even though the spec and backend already have them.

**How to apply:** Any time `lib/api-spec/openapi.yaml` changes, codegen must be the very next step before any frontend type check or restart.
