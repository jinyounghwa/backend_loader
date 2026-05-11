'use client';

import { useState } from 'react';
import { Download, FileText, File, Calendar } from 'lucide-react';

export default function GuardianReportDownload() {
  const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleDownload = async (format: 'json' | 'csv') => {
    try {
      setLoading(true);
      setMessage(null);

      const params = new URLSearchParams();
      params.set('format', format);
      params.set('startDate', startDate);
      params.set('endDate', endDate);

      const response = await fetch(`/api/guardian/reports/events?${params}`);
      if (!response.ok) throw new Error('Failed to download report');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `events-report-${new Date().toISOString().split('T')[0]}.${format === 'csv' ? 'csv' : 'json'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setMessage({ type: 'success', text: `${format.toUpperCase()} report downloaded` });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to download report' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-6">
      <div className="mb-6 flex items-center gap-3">
        <FileText className="w-5 h-5 text-slate-400" />
        <h2 className="text-lg font-semibold text-slate-100">Download Reports</h2>
      </div>

      {message && (
        <div
          className={`mb-4 rounded px-4 py-3 text-sm ${
            message.type === 'success'
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Date Range */}
      <div className="mb-6 grid grid-cols-2 gap-4">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">Start Date</label>
          <div className="flex items-center gap-2 rounded border border-slate-600 bg-slate-800 px-3 py-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="flex-1 bg-transparent text-slate-200 focus:outline-none"
            />
          </div>
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">End Date</label>
          <div className="flex items-center gap-2 rounded border border-slate-600 bg-slate-800 px-3 py-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="flex-1 bg-transparent text-slate-200 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Download Buttons */}
      <div className="space-y-3">
        <button
          onClick={() => handleDownload('csv')}
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 font-medium text-white transition-all hover:bg-emerald-700 disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <File className="w-4 h-4" />
          Download as CSV
        </button>

        <button
          onClick={() => handleDownload('json')}
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-all hover:bg-blue-700 disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <FileText className="w-4 h-4" />
          Download as JSON
        </button>
      </div>

      {/* Info */}
      <div className="mt-4 rounded border border-slate-700/30 bg-slate-800/30 px-4 py-3 text-xs text-slate-400">
        Reports include all events within the selected date range. Data can be used for compliance and analysis.
      </div>
    </div>
  );
}
