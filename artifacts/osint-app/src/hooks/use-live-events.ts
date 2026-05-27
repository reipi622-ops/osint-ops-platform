import { useState, useEffect, useRef } from 'react';
import type { EventResponse } from '@workspace/api-client-react';

export type LiveEventsStatus = 'connecting' | 'connected' | 'error';

export function useLiveEvents(maxEvents = 20) {
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [status, setStatus] = useState<LiveEventsStatus>('connecting');
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function connect() {
      setStatus('connecting');
      
      const es = new EventSource('/api/events/stream');
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus('connected');
      };

      es.onmessage = (event) => {
        try {
          const newEvent: EventResponse = JSON.parse(event.data);
          setEvents((prev) => {
            const updated = [newEvent, ...prev];
            return updated.slice(0, maxEvents);
          });
        } catch (err) {
          console.error('Failed to parse SSE data', err);
        }
      };

      es.onerror = (error) => {
        console.error('SSE error', error);
        setStatus('error');
        es.close();
        
        // Auto-reconnect after 3s
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [maxEvents]);

  return { events, status };
}
