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
  const [events, setEvents]             = useState<EventResponse[]>([]);
  const [status, setStatus]             = useState<LiveEventsStatus>('connecting');
  const [criticalEvent, setCriticalEvent] = useState<EventResponse | null>(null);
  const [messageCount, setMessageCount] = useState(0);
  const [lastEventAt, setLastEventAt]   = useState<Date | null>(null);

  const esRef      = useRef<EventSource | null>(null);
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    function connect() {
      if (!mountedRef.current) return;
      console.log('[SSE] connecting to /api/events/stream …');
      setStatus('connecting');

      const es = new EventSource('/api/events/stream');
      esRef.current = es;

      // Single handler for ALL frames — the backend embeds _sse_type in the JSON
      // so we never rely on the SSE 'event:' field (which proxies can strip).
      es.onmessage = (e: MessageEvent) => {
        try {
          const msg = JSON.parse(e.data) as Record<string, unknown>;
          const sseType = msg._sse_type as string | undefined;

          if (sseType === 'connected') {
            console.log('[SSE] handshake OK — stream is live');
            if (mountedRef.current) setStatus('connected');
            return;
          }

          if (sseType === 'heartbeat') {
            console.debug('[SSE] heartbeat');
            return;
          }

          if (sseType === 'new_event') {
            // Strip the internal meta field before storing
            const { _sse_type: _, ...evData } = msg;
            const ev = evData as unknown as EventResponse;
            console.log(
              '[SSE] new_event id=%s category=%s side=%s source=%s',
              ev.id, ev.category, ev.side, ev.source_name,
            );
            if (mountedRef.current) {
              setEvents(prev => [ev, ...prev].slice(0, maxEvents));
              setMessageCount(n => n + 1);
              setLastEventAt(new Date());
              if (ev.escalation_level === 'critical') {
                setCriticalEvent(ev);
              }
            }
            return;
          }

          // Unknown message type — log it so we can catch proxy mangling
          console.warn('[SSE] unknown message type=%s raw=%s', sseType, e.data.slice(0, 200));
        } catch (err) {
          console.error('[SSE] failed to parse message:', e.data.slice(0, 200), err);
        }
      };

      es.onerror = (err) => {
        console.warn('[SSE] connection error — will reconnect in 3 s', err);
        if (mountedRef.current) setStatus('error');
        es.close();
        timerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, 3000);
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      esRef.current?.close();
      esRef.current = null;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [maxEvents]);

  const dismissCritical = useCallback(() => setCriticalEvent(null), []);

  return { events, status, criticalEvent, dismissCritical, messageCount, lastEventAt };
}
