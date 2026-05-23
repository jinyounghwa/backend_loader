'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

interface StreamEvent {
  type: 'audit_log_created' | 'audit_log_modified' | 'audit_log_removed';
  data: Record<string, any>;
  timestamp: string;
}

interface UseAuditLogStreamOptions {
  accountId?: string;
  connectionId?: string;
  onNewLog?: (event: StreamEvent) => void;
  onError?: (error: Error) => void;
}

export function useAuditLogStream({
  accountId,
  connectionId,
  onNewLog,
  onError,
}: UseAuditLogStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttemptsRef = useRef(5);
  const reconnectDelayRef = useRef(1000);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      return;
    }

    if (!accountId && !connectionId) {
      return;
    }

    const params = new URLSearchParams();
    if (accountId) params.append('account_id', accountId);
    if (connectionId) params.append('connection_id', connectionId);

    const url = `/api/guardian/audit-logs/stream?${params.toString()}`;

    try {
      const eventSource = new EventSource(url);

      eventSource.addEventListener('open', () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      });

      eventSource.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data) as StreamEvent;

          if (data.type === 'audit_log_created') {
            onNewLog?.(data);
          }
        } catch (error) {
          console.error('Failed to parse stream event:', error);
        }
      });

      eventSource.addEventListener('error', () => {
        eventSource.close();
        eventSourceRef.current = null;
        setIsConnected(false);

        if (reconnectAttemptsRef.current < maxReconnectAttemptsRef.current) {
          reconnectAttemptsRef.current += 1;
          const delay = reconnectDelayRef.current * Math.pow(2, reconnectAttemptsRef.current - 1);

          setTimeout(() => {
            connect();
          }, Math.min(delay, 30000));
        } else {
          const error = new Error('Max reconnect attempts reached');
          onError?.(error);
        }
      });

      eventSourceRef.current = eventSource;
    } catch (error) {
      console.error('Failed to create EventSource:', error);
      setIsConnected(false);
    }
  }, [accountId, connectionId, onNewLog, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    reconnectAttempts: reconnectAttemptsRef.current,
  };
}
