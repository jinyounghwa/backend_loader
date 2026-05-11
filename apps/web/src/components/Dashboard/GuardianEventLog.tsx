'use client';

import { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Info, AlertTriangle, Filter, Wifi, WifiOff } from 'lucide-react';
import { useGuardianStream } from '@/lib/hooks/useGuardianStream';

export interface GuardianEvent {
  id: string;
  timestamp: string;
  severity: 'HIGH' | 'MEDIUM' | 'INFO';
  check_type: string;
  title: string;
  message: string;
  details: Record<string, any>;
}

interface GuardianEventLogProps {
  limit?: number;
  onFilter?: (severity?: string) => void;
  enableRealtimeStream?: boolean;
}

export default function GuardianEventLog({ limit = 10, onFilter, enableRealtimeStream = true }: GuardianEventLogProps) {
  const [events, setEvents] = useState<GuardianEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeverity, setSelectedSeverity] = useState<string | undefined>();

  const handleStreamEvent = useCallback((event: GuardianEvent) => {
    if (selectedSeverity && event.severity !== selectedSeverity) {
      return;
    }
    setEvents((prev) => {
      const updated = [event, ...prev];
      return updated.slice(0, limit);
    });
  }, [selectedSeverity, limit]);

  const { isConnected } = useGuardianStream({
    enabled: enableRealtimeStream,
    onEvent: handleStreamEvent,
  });

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        params.set('limit', limit.toString());
        if (selectedSeverity) {
          params.set('severity', selectedSeverity);
        }

        const response = await fetch(`/api/guardian/events?${params}`);
        if (!response.ok) throw new Error('Failed to fetch events');

        const data = await response.json();
        setEvents(data.events || []);
      } catch (error) {
        console.error('Error fetching events:', error);
        setEvents([]);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [limit, selectedSeverity]);

  const handleFilterChange = (severity?: string) => {
    setSelectedSeverity(severity);
    onFilter?.(severity);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'MEDIUM':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'INFO':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return <AlertCircle className="w-4 h-4" />;
      case 'MEDIUM':
        return <AlertTriangle className="w-4 h-4" />;
      case 'INFO':
        return <Info className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    const diffInHours = Math.floor(diffInMinutes / 60);
    const diffInDays = Math.floor(diffInHours / 24);

    if (diffInMinutes < 1) return '방금';
    if (diffInMinutes < 60) return `${diffInMinutes}분 전`;
    if (diffInHours < 24) return `${diffInHours}시간 전`;
    return `${diffInDays}일 전`;
  };

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-100">Recent Events</h2>
          {enableRealtimeStream && (
            <div className="flex items-center gap-1.5">
              {isConnected ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-green-500" />
                  <span className="text-xs text-green-500">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-xs text-slate-500">Offline</span>
                </>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={selectedSeverity || ''}
            onChange={(e) => handleFilterChange(e.target.value || undefined)}
            className="rounded border border-slate-600 bg-slate-800 px-3 py-1 text-sm text-slate-300 hover:border-slate-500 focus:border-slate-400 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="INFO">Info</option>
          </select>
        </div>
      </div>

      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-slate-400">Loading events...</div>
          </div>
        ) : events.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-slate-400">No events found</div>
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-4 rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3 transition-all hover:bg-slate-800/50"
            >
              <div className="mt-0.5">
                {getSeverityIcon(event.severity)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium border ${getSeverityColor(
                      event.severity
                    )}`}
                  >
                    {event.severity}
                  </span>
                  <span className="text-sm font-medium text-slate-300">{event.check_type.toUpperCase()}</span>
                  <span className="text-xs text-slate-500">{getRelativeTime(event.timestamp)}</span>
                </div>
                <p className="text-sm font-semibold text-slate-100 mb-1">{event.title}</p>
                <p className="text-xs text-slate-400">{event.message}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
