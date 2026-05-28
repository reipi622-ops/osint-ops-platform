import { useState, useEffect, useRef } from 'react';
import type { EventResponse } from '@workspace/api-client-react';

export type LiveEventsStatus = 'connecting' | 'connected' | 'error';

export function useLiveEvents(maxEvents = 50) {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [status, setStatus] = useState<LiveEventsStatus>('connecting');
  const esRef = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      setStatus('connecting');
      const es = new EventSource('/api/events/stream');
      esRef.current = es;

      // The server sends named SSE events — `event: connected`, `event: new_event`, `event: heartbeat`.
      // es.onmessage only fires for *unnamed* events; we must use addEventListener for named ones.
      es.addEventListener('connected', () => setStatus('connected'));

      es.addEventListener('new_event', (e: MessageEvent) => {
        try {
          const ev: EventResponse = JSON.parse(e.data);
          setEvents(prev => [ev, ...prev].slice(0, maxEvents));
        } catch {
          /* ignore malformed frames */
        }
      });

      es.addEventListener('heartbeat', () => {});

      es.onerror = () => {
        setStatus('error');
        es.close();
        timerRef.current = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [maxEvents]);

  return { events, status };
}
