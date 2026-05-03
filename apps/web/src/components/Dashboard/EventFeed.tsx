'use client';

import { useAccounts } from '@/components/Providers';
import { useEffect, useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, Zap, RefreshCw } from 'lucide-react';

interface GuardianEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'warning';
  details?: { message?: string };
  auto_response?: { action: string; status: string };
}

export default function EventFeed() {
  const { selectedAccountId } = useAccounts();
  const [events, setEvents] = useState<GuardianEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadEvents = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/events?hours=24`);
      if (res.ok) {
        const data = await res.json();
        setEvents((data.events || []).slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to load events:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
    const interval = setInterval(loadEvents, 30000);
    return () => clearInterval(interval);
  }, [selectedAccountId]);

  const getSeverityIcon = (severity: GuardianEvent['severity']) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'high':
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-amber-400" />;
      case 'medium':
        return <Zap className="w-4 h-4 text-blue-400" />;
      default:
        return <CheckCircle className="w-4 h-4 text-green-400" />;
    }
  };

  const getSeverityColor = (severity: GuardianEvent['severity']) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-400 bg-red-500/5';
      case 'high':
      case 'warning':
        return 'border-l-amber-400 bg-amber-500/5';
      case 'medium':
        return 'border-l-blue-400 bg-blue-500/5';
      default:
        return 'border-l-green-400 bg-green-500/5';
    }
  };

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-100">Recent Events</h2>
        <button
          onClick={loadEvents}
          disabled={isLoading}
          className="p-1.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {events.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recent events</p>
          </div>
        ) : (
          events.map(event => (
            <div key={event.event_id} className={`border-l-4 rounded p-3 ${getSeverityColor(event.severity)}`}>
              <div className="flex items-start space-x-3">
                <div className="mt-1">{getSeverityIcon(event.severity)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-100 truncate">
                    {event.event_type.replace(/_/g, ' ').toUpperCase()}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {typeof event.details === 'string'
                      ? event.details
                      : event.details?.message || 'No additional details'}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-500">{event.severity.toUpperCase()}</span>
                    <span className="text-xs text-slate-500">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
