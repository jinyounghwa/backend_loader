import { useEffect, useState, useCallback, useRef } from 'react';

interface UseEventStreamOptions {
  accountId?: string;
  onEvent?: (event: any) => void;
  autoConnect?: boolean;
}

export function useEventStream(options: UseEventStreamOptions = {}) {
  const { accountId, onEvent, autoConnect = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) return;
    if (!accountId) return;

    const url = new URL('/api/events/stream', window.location.origin);
    url.searchParams.set('account_id', accountId);

    const es = new EventSource(url.toString());

    es.addEventListener('event', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        onEvent?.(data);
      } catch (err) {
        console.error('Failed to parse event:', err);
      }
    });

    es.addEventListener('error', () => {
      setIsConnected(false);
      setError('Event stream connection lost');
      es.close();
      eventSourceRef.current = null;
    });

    es.addEventListener('open', () => {
      setIsConnected(true);
      setError(null);
    });

    eventSourceRef.current = es;
  }, [accountId, onEvent]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    if (autoConnect && accountId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [accountId, autoConnect, connect, disconnect]);

  return { isConnected, error, connect, disconnect };
}
