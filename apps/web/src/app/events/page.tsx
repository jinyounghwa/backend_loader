'use client';

import { useState, useCallback } from 'react';
import { useEvents } from '@/hooks/useGuardianData';
import { Activity, Filter, Download, RefreshCw, ChevronDown, ChevronUp, Calendar } from 'lucide-react';

export default function EventsPage() {
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);

  const { events, total, isLoading, isError, refresh } = useEvents(
    typeFilter,
    severityFilter,
    startDate,
    endDate
  );

  // CSV Export 함수
  const exportToCSV = useCallback(() => {
    if (events.length === 0) {
      alert('No events to export');
      return;
    }

    const headers = ['Event ID', 'Timestamp', 'Type', 'Severity', 'Message', 'Auto Response Action', 'Auto Response Status', 'Resource ID'];
    const rows = events.map((event) => [
      event.event_id || '',
      event.timestamp || '',
      event.event_type || '',
      event.severity || '',
      event.details?.message || '',
      event.auto_response?.action || '',
      event.auto_response?.status || '',
      event.auto_response?.resource_id || '',
    ]);

    const csv = [
      headers.join(','),
      ...rows.map((row) =>
        row
          .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `aws-guardian-events-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [events]);

  // Set default date range (last 7 days)
  const getDefaultDates = () => {
    if (!startDate && !endDate) {
      const today = new Date();
      const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
      return {
        defaultStart: sevenDaysAgo.toISOString().split('T')[0],
        defaultEnd: today.toISOString().split('T')[0],
      };
    }
    return { defaultStart: startDate, defaultEnd: endDate };
  };

  const { defaultStart, defaultEnd } = getDefaultDates();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center">
          <Activity className="w-6 h-6 mr-2 text-amber-500" />
          Event Timeline
        </h1>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="flex items-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={exportToCSV}
            disabled={events.length === 0}
            className="flex items-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded border border-slate-700 transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-4 space-y-4">
        <div className="flex items-center text-slate-400">
          <Filter className="w-4 h-4 mr-2" />
          <span className="text-sm font-medium">Filters:</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium">Type</label>
            <select
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All Types</option>
              <option value="cost">Cost</option>
              <option value="ec2">EC2</option>
              <option value="s3">S3</option>
              <option value="auto_response">Auto Response</option>
              <option value="summary">Summary</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium">Severity</label>
            <select
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium flex items-center">
              <Calendar className="w-3 h-3 mr-1" />
              Start Date
            </label>
            <input
              type="date"
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={startDate || defaultStart}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium flex items-center">
              <Calendar className="w-3 h-3 mr-1" />
              End Date
            </label>
            <input
              type="date"
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={endDate || defaultEnd}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          <div className="text-sm text-slate-500 font-mono flex items-center space-x-2">
            <span>Showing {events.length} events of {total} total</span>
            {isError && <span className="text-red-400 text-xs">(fallback data)</span>}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-12 text-center">
            <Activity className="w-12 h-12 mx-auto text-slate-600 mb-4" />
            <p className="text-slate-500 text-lg">No events match the selected filters</p>
            <p className="text-slate-600 text-sm mt-1">Adjust your filters or check back later</p>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline */}
            <div className="space-y-4">
              {events.map((event, idx) => {
                const date = new Date(event.timestamp);
                const dateStr = date.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                });
                const timeStr = date.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                });

                let severityIcon = '🔵';
                let severityColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                if (event.severity === 'critical') {
                  severityIcon = '🔴';
                  severityColor = 'bg-red-500/10 text-red-400 border-red-500/20';
                }
                if (event.severity === 'warning') {
                  severityIcon = '🟡';
                  severityColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                }

                const isExpanded = expandedEvent === event.event_id;

                return (
                  <div key={event.event_id ?? idx} className="group">
                    <button
                      onClick={() =>
                        setExpandedEvent(isExpanded ? null : event.event_id || null)
                      }
                      className="w-full text-left bg-[#1a1d27] border border-slate-800 rounded-lg p-4 hover:border-slate-700 hover:bg-[#202530] transition-all"
                    >
                      <div className="flex items-start space-x-4">
                        {/* Timeline dot */}
                        <div className="flex flex-col items-center pt-1">
                          <div className="text-lg">{severityIcon}</div>
                          {idx < events.length - 1 && (
                            <div className="w-0.5 h-12 bg-slate-700 mt-2" />
                          )}
                        </div>

                        {/* Event content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <div>
                                <span className="uppercase tracking-wider text-xs font-bold text-slate-300">
                                  {event.event_type.replace('_', ' ')}
                                </span>
                              </div>
                              <span className={`px-2.5 py-1 rounded text-xs font-medium border ${severityColor}`}>
                                {event.severity.toUpperCase()}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <div className="text-right">
                                <div className="font-mono text-xs text-slate-400">{dateStr}</div>
                                <div className="font-mono text-xs text-slate-500">{timeStr}</div>
                              </div>
                              {event.auto_response && (
                                <div className="text-green-400">✓</div>
                              )}
                              <div className={`text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
                                <ChevronDown className="w-4 h-4" />
                              </div>
                            </div>
                          </div>

                          <p className="text-slate-300 text-sm mt-2">
                            {event.details?.message ?? 'No details available'}
                          </p>

                          {isExpanded && (
                            <div className="mt-4 pt-4 border-t border-slate-700 space-y-3">
                              {/* Event details */}
                              <div>
                                <h4 className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">
                                  Event Details
                                </h4>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div>
                                    <span className="text-slate-500">Event ID:</span>
                                    <div className="font-mono text-slate-400 truncate">{event.event_id}</div>
                                  </div>
                                  <div>
                                    <span className="text-slate-500">Type:</span>
                                    <div className="text-slate-400">{event.event_type}</div>
                                  </div>
                                </div>
                              </div>

                              {/* Auto response details */}
                              {event.auto_response && (
                                <div>
                                  <h4 className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">
                                    Auto Response Action
                                  </h4>
                                  <div className="bg-slate-800/50 rounded p-3 space-y-2">
                                    <div className="flex items-center justify-between">
                                      <span className="text-slate-500 text-xs">Action:</span>
                                      <span className="text-slate-300 text-xs font-medium">
                                        {event.auto_response.action}
                                      </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                      <span className="text-slate-500 text-xs">Resource:</span>
                                      <span className="text-slate-300 text-xs font-mono truncate">
                                        {event.auto_response.resource_id}
                                      </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                      <span className="text-slate-500 text-xs">Status:</span>
                                      <span className={`text-xs font-medium ${
                                        event.auto_response.status === 'success'
                                          ? 'text-green-400'
                                          : 'text-red-400'
                                      }`}>
                                        {event.auto_response.status.toUpperCase()}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Raw details */}
                              {event.details && Object.keys(event.details).length > 1 && (
                                <div>
                                  <h4 className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">
                                    Additional Details
                                  </h4>
                                  <div className="bg-slate-900/50 rounded p-2 font-mono text-xs text-slate-400 overflow-x-auto max-h-32 overflow-y-auto">
                                    <pre>{JSON.stringify(event.details, null, 2)}</pre>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
