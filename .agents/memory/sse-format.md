---
name: SSE format
description: The specific SSE wire format this backend uses and why the frontend must use onmessage not addEventListener.
---

## Rule
The backend sends ALL SSE frames as the **default event type** (no `event:` line):

```
retry: 3000
data: {"_sse_type": "connected"}\n\n

data: {"_sse_type": "heartbeat"}\n\n

data: {"_sse_type": "new_event", "id": 42, ...}\n\n
```

The message type is encoded **inside the JSON payload** as `_sse_type`.

**Why:** Named events (`event: new_event\ndata: ...`) are stripped or mis-forwarded by some proxies and CDN edge nodes. Using only `data:` frames ensures they survive Replit's reverse proxy intact.

**How to apply:**  
- Frontend: use `es.onmessage = (e) => { const d = JSON.parse(e.data); if (d._sse_type === 'new_event') ... }`.  
- Do NOT use `es.addEventListener('new_event', ...)` — that listens for named events, which will never fire.
- Backend: never add `event:` lines to SSE output in this project.
