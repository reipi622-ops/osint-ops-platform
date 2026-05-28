import { useState, useEffect, useRef, useCallback } from 'react';
import type { EventResponse } from '@workspace/api-client-react';

export type LiveEventsStatus = 'connecting' | 'connected' | 'error';

export interface UseLiveEventsResult {
  events: EventResponse[];
  status: LiveEventsStatus;
  criticalEvent: EventResponse | null;
  dismissCritical: () => void;
  messageCount: number;
  lastEventAt: Date | null;
}

export function useLiveEvents(maxEvents = 50): UseLiveEventsResult {
  const [events, setEvents]               = useState<EventResponse[]>([]);
  const [status, setStatus]               = useState<LiveEventsStatus>('connecting');
  const [criticalEvent, setCriticalEvent]  = useState<EventResponse | null>(null);
  const [messageCount, setMessageCount]   = useState(0);
  const [lastEventAt, setLastEventAt]     = useState<Date | null>(null);

  // Refs stable across renders
  const esRef      = useRef<EventSource | null>(null);
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const seenIdsRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      console.log('[SSE] connecting to /api/events/stream …');
      setStatus('connecting');

      const es = new EventSource('/api/events/stream');
      // Register as current BEFORE any callbacks fire
      esRef.current = es;

      es.onmessage = (e: MessageEvent) => {
        // Guard: ignore messages from a connection that has been superseded
        if (esRef.current !== es) {
          console.debug('[SSE] ignoring stale connection message');
          return;
        }
        try {
          const msg = JSON.parse(e.data) as Record<string, unknown>;
          const sseType = msg._sse_type as string | undefined;

          if (sseType === 'connected') {
            console.log('[SSE] handshake OK — stream live');
            if (mountedRef.current) setStatus('connected');
            return;
          }

          if (sseType === 'heartbeat') {
            console.debug('[SSE] heartbeat');
            return;
          }

          if (sseType === 'new_event') {
            const { _sse_type: _t, ...evData } = msg;
            const ev = evData as unknown as EventResponse;
            const evId = Number(ev.id);

            // Deduplicate by id
            if (evId > 0 && seenIdsRef.current.has(evId)) {
              console.log('[SSE] duplicate id=%s — skipped', evId);
              return;
            }
            if (evId > 0) seenIdsRef.current.add(evId);
            // Trim seen-ID set so it doesn't grow unbounded
            if (seenIdsRef.current.size > maxEvents * 3) {
              const arr = Array.from(seenIdsRef.current);
              seenIdsRef.current = new Set(arr.slice(arr.length - maxEvents));
            }

            console.log(
              '[SSE] ✓ new_event id=%s cat=%s side=%s conf=%s src=%s',
              ev.id, ev.category, ev.side, ev.confidence_level, ev.source_name,
            );

            if (mountedRef.current) {
              setEvents(prev => [ev, ...prev].slice(0, maxEvents));
              setMessageCount(n => n + 1);
              setLastEventAt(new Date());
              if (ev.escalation_level === 'critical') setCriticalEvent(ev);
            }
            return;
          }

          console.warn('[SSE] unknown _sse_type=%s frame=%s', sseType, e.data.slice(0, 120));
        } catch (err) {
          console.error('[SSE] parse error:', e.data.slice(0, 120), err);
        }
      };

      es.onerror = () => {
        // Guard: only react to errors on the current connection
        if (esRef.current !== es) return;
        console.warn('[SSE] connection error — reconnecting in 3 s');
        if (mountedRef.current) setStatus('error');
        es.close();
        esRef.current = null;
        timerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, 3_000);
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      // Mark current ES as superseded BEFORE closing so the onerror guard fires
      const current = esRef.current;
      esRef.current = null;
      current?.close();
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [maxEvents]);

  const dismissCritical = useCallback(() => setCriticalEvent(null), []);

  return { events, status, criticalEvent, dismissCritical, messageCount, lastEventAt };
}
