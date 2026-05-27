---
name: React Query hook options
description: Generated hooks require explicit queryKey in options object, not just refetchInterval or enabled
---

# React Query hook options — required queryKey

## The rule
When passing options to a generated query hook (e.g. `useGetTelegramAuthStatus`, `useGetScraperStatus`, `useGetEvent`), always include `queryKey` in the `query` sub-object:

```typescript
// WRONG — causes TS2741 "Property 'queryKey' is missing"
useGetScraperStatus({ query: { refetchInterval: 3000 } })
useGetEvent(id, { query: { enabled: !!id } })

// CORRECT
useGetScraperStatus({ query: { queryKey: getGetScraperStatusQueryKey(), refetchInterval: 3000 } })
useGetEvent(id, { query: { queryKey: getGetEventQueryKey(id), enabled: !!id } })
```

**Why:** Orval generates `UseQueryOptions` which has `queryKey` as required. The internal default logic works fine at runtime, but TypeScript enforces the type at compile time.

**How to apply:** Any time you add `refetchInterval`, `enabled`, `staleTime`, or other query options to a generated hook, also import and include the matching `getXxxQueryKey()` function from the same module.
