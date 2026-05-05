'use client';

import { useState, useCallback } from 'react';
import { useEvents } from '@/hooks/useGuardianData';
import { Activity, Filter, Download, RefreshCw, ChevronDown, Calendar, DollarSign, Server, Database, Zap, ClipboardList, MapPin, Box } from 'lucide-react';

function getRelativeTime(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return '방금 전';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}분 전`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}시간 전`;
  if (diffInSeconds < 172800) return '어제';
  return `${Math.floor(diffInSeconds / 86400)}일 전`;
}

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
      alert('내보낼 이벤트가 없습니다.');
      return;
    }

    const headers = ['이벤트 ID', '발생 시간', '유형', '심각도', '제목', '설명', '자동 대응 액션', '자동 대응 상태', '리소스 ID'];
    const rows = events.map((event) => [
      event.event_id || '',
      event.timestamp || '',
      event.event_type || '',
      event.severity || '',
      event.details?.title || '',
      event.details?.description || '',
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

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'cost': return <DollarSign className="w-5 h-5" />;
      case 'ec2': return <Server className="w-5 h-5" />;
      case 's3': return <Database className="w-5 h-5" />;
      case 'auto_response': return <Zap className="w-5 h-5" />;
      case 'summary': return <ClipboardList className="w-5 h-5" />;
      default: return <Activity className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center">
          <Activity className="w-6 h-6 mr-2 text-amber-500" />
          이벤트 타임라인
        </h1>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="flex items-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            새로고침
          </button>
          <button
            onClick={exportToCSV}
            disabled={events.length === 0}
            className="flex items-center px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded border border-slate-700 transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4 mr-2" />
            CSV 내보내기
          </button>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-4 space-y-4">
        <div className="flex items-center text-slate-400">
          <Filter className="w-4 h-4 mr-2" />
          <span className="text-sm font-medium">필터:</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium">유형</label>
            <select
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">모든 유형</option>
              <option value="cost">비용 (Cost)</option>
              <option value="ec2">EC2</option>
              <option value="s3">S3</option>
              <option value="auto_response">자동 대응</option>
              <option value="summary">요약</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium">심각도</label>
            <select
              className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-amber-500"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="all">모든 심각도</option>
              <option value="critical">위험 (Critical)</option>
              <option value="warning">경고 (Warning)</option>
              <option value="info">정보 (Info)</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-xs text-slate-500 uppercase tracking-wider font-medium flex items-center">
              <Calendar className="w-3 h-3 mr-1" />
              시작일
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
              종료일
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
            <span>전체 {total}개 중 {events.length}개 표시</span>
            {isError && <span className="text-red-400 text-xs">(대체 데이터)</span>}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-12 text-center">
            <Activity className="w-12 h-12 mx-auto text-slate-600 mb-4" />
            <p className="text-slate-500 text-lg">선택한 필터와 일치하는 이벤트가 없습니다</p>
            <p className="text-slate-600 text-sm mt-1">필터를 조정하거나 나중에 다시 확인해주세요</p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((event, idx) => {
              const date = new Date(event.timestamp);
              const dateStr = date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              });
              const timeStr = date.toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              });
              const relativeTime = getRelativeTime(event.timestamp);

              let severityColor = 'border-l-blue-500 bg-blue-500/5 hover:bg-blue-500/10';
              let iconColor = 'text-blue-400 bg-blue-500/10';
              
              if (event.severity === 'critical') {
                severityColor = 'border-l-red-500 bg-red-500/5 hover:bg-red-500/10';
                iconColor = 'text-red-400 bg-red-500/10';
              } else if (event.severity === 'warning') {
                severityColor = 'border-l-amber-500 bg-amber-500/5 hover:bg-amber-500/10';
                iconColor = 'text-amber-400 bg-amber-500/10';
              }

              const isExpanded = expandedEvent === event.event_id;

              return (
                <div key={event.event_id ?? idx} className="group">
                  <button
                    onClick={() =>
                      setExpandedEvent(isExpanded ? null : event.event_id || null)
                    }
                    className={`w-full text-left border-y border-r border-slate-800 border-l-4 rounded-lg p-4 transition-all ${severityColor}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`p-2 rounded-full shrink-0 mt-1 ${iconColor}`}>
                        {getEventIcon(event.event_type)}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                          <div>
                            <h3 className="text-base font-bold text-slate-200 mb-1">
                              {event.details?.title || event.details?.message || '알 수 없는 이벤트'}
                            </h3>
                            <p className="text-sm text-slate-400 leading-relaxed">
                              {event.details?.description || event.details?.message || '상세 정보가 없습니다.'}
                            </p>
                            
                            <div className="flex flex-wrap gap-2 mt-3">
                              {event.details?.resource && (
                                <span className="inline-flex items-center px-2 py-1 rounded bg-slate-800/80 text-slate-300 text-xs font-medium border border-slate-700">
                                  <Box className="w-3 h-3 mr-1.5 text-slate-400" />
                                  {event.details.resource}
                                </span>
                              )}
                              {event.details?.region && (
                                <span className="inline-flex items-center px-2 py-1 rounded bg-slate-800/80 text-slate-300 text-xs font-medium border border-slate-700">
                                  <MapPin className="w-3 h-3 mr-1.5 text-slate-400" />
                                  {event.details.region}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-col items-end shrink-0">
                            <span className="text-sm font-medium text-slate-300">{relativeTime}</span>
                            <span className="text-xs text-slate-500 mt-1">{dateStr} {timeStr}</span>
                          </div>
                        </div>

                        {event.auto_response && (
                          <div className="mt-4 p-3 rounded-md bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className={`p-1.5 rounded-full ${event.auto_response.status === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                <Zap className="w-4 h-4" />
                              </div>
                              <div>
                                <div className="text-xs text-slate-500 mb-0.5">자동 대응 조치</div>
                                <div className="text-sm font-medium text-slate-300">
                                  {event.auto_response.action} <span className="text-slate-500 mx-1">→</span> {event.auto_response.resource_id}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center">
                              {event.auto_response.status === 'success' ? (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                                  성공 ✅
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                                  실패 ❌
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {isExpanded && (
                          <div className="mt-4 pt-4 border-t border-slate-700/50">
                            <div className="grid grid-cols-2 gap-4 mb-4">
                              <div>
                                <span className="text-xs text-slate-500 block mb-1">이벤트 ID</span>
                                <span className="text-sm font-mono text-slate-300">{event.event_id}</span>
                              </div>
                              <div>
                                <span className="text-xs text-slate-500 block mb-1">이벤트 유형</span>
                                <span className="text-sm text-slate-300 uppercase">{event.event_type}</span>
                              </div>
                            </div>
                            
                            {event.details && Object.keys(event.details).length > 0 && (
                              <div>
                                <span className="text-xs text-slate-500 block mb-2">원시 데이터 (Raw Details)</span>
                                <div className="bg-slate-900/80 rounded p-3 font-mono text-xs text-slate-400 overflow-x-auto border border-slate-800">
                                  <pre>{JSON.stringify(event.details, null, 2)}</pre>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className={`text-slate-500 transition-transform mt-1 ${isExpanded ? 'rotate-180' : ''}`}>
                        <ChevronDown className="w-5 h-5" />
                      </div>
                    </div>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
