import { useState, useEffect, useRef, useCallback } from 'react';
import type { EventResponse } from '@workspace/api-client-react';

export type LiveEventsStatus = 'connecting' | 'connected' | 'error';

export function useLiveEvents(maxEvents = 50) {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [status, setStatus] = useState<LiveEventsStatus>('connecting');
  const [criticalEvent, setCriticalEvent] = useState<EventResponse | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      setStatus('connecting');
      const es = new EventSource('/api/events/stream');
      esRef.current = es;

      es.addEventListener('connected', () => setStatus('connected'));

      es.addEventListener('new_event', (e: MessageEvent) => {
        try {
          const ev: EventResponse = JSON.parse(e.data);
          setEvents(prev => [ev, ...prev].slice(0, maxEvents));
          if (ev.escalation_level === 'critical') {
            setCriticalEvent(ev);
          }
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

  const dismissCritical = useCallback(() => setCriticalEvent(null), []);

  return { events, status, criticalEvent, dismissCritical };
}
