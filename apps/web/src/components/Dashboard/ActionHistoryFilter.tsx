'use client';

import { memo, useState } from 'react';
import { X } from 'lucide-react';

type ActionType = 'stop_instance' | 'block_bucket' | 'remediate' | 'rollback';
type ActionStatus = 'success' | 'failed' | 'pending';

interface ActionHistoryFilterProps {
  onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
  type: ActionType | 'all';
  status: ActionStatus | 'all';
}

const ACTION_TYPES: Array<ActionType | 'all'> = ['all', 'stop_instance', 'block_bucket', 'remediate', 'rollback'];
const STATUSES: Array<ActionStatus | 'all'> = ['all', 'pending', 'success', 'failed'];

function ActionHistoryFilter({ onFilterChange }: ActionHistoryFilterProps) {
  const [filters, setFilters] = useState<FilterState>({ type: 'all', status: 'all' });
  const [isOpen, setIsOpen] = useState(false);

  const handleTypeChange = (type: ActionType | 'all') => {
    const newFilters = { ...filters, type };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleStatusChange = (status: ActionStatus | 'all') => {
    const newFilters = { ...filters, status };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const defaultFilters: FilterState = { type: 'all', status: 'all' };
    setFilters(defaultFilters);
    onFilterChange(defaultFilters);
  };

  const isFiltered = filters.type !== 'all' || filters.status !== 'all';

  const getLabel = (type: ActionType | 'all') => {
    const labels: Record<string, string> = {
      all: 'All Types',
      stop_instance: 'Stop Instance',
      block_bucket: 'Block Bucket',
      remediate: 'Remediate',
      rollback: 'Rollback',
    };
    return labels[type];
  };

  const getStatusLabel = (status: ActionStatus | 'all') => {
    const labels: Record<string, string> = {
      all: 'All Status',
      pending: 'Pending',
      success: 'Success',
      failed: 'Failed',
    };
    return labels[status];
  };

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors text-sm"
      >
        <span>🔍 Filters</span>
        {isFiltered && (
          <span className="inline-flex items-center justify-center w-5 h-5 text-xs bg-blue-500/20 border border-blue-500/40 rounded-full">
            {(filters.type !== 'all' ? 1 : 0) + (filters.status !== 'all' ? 1 : 0)}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="mt-3 p-4 rounded-lg border border-slate-700/50 bg-slate-800/30">
          <div className="space-y-4">
            {/* Type Filter */}
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase block mb-2">
                Action Type
              </label>
              <div className="flex flex-wrap gap-2">
                {ACTION_TYPES.map(type => (
                  <button
                    key={type}
                    onClick={() => handleTypeChange(type)}
                    className={`px-3 py-1.5 rounded text-xs transition-colors ${
                      filters.type === type
                        ? 'bg-blue-500/30 border border-blue-400 text-blue-300'
                        : 'bg-slate-700/30 border border-slate-600 text-slate-400 hover:bg-slate-700/50'
                    }`}
                  >
                    {getLabel(type)}
                  </button>
                ))}
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase block mb-2">
                Status
              </label>
              <div className="flex flex-wrap gap-2">
                {STATUSES.map(status => (
                  <button
                    key={status}
                    onClick={() => handleStatusChange(status)}
                    className={`px-3 py-1.5 rounded text-xs transition-colors ${
                      filters.status === status
                        ? 'bg-blue-500/30 border border-blue-400 text-blue-300'
                        : 'bg-slate-700/30 border border-slate-600 text-slate-400 hover:bg-slate-700/50'
                    }`}
                  >
                    {getStatusLabel(status)}
                  </button>
                ))}
              </div>
            </div>

            {/* Reset Button */}
            {isFiltered && (
              <button
                onClick={handleReset}
                className="w-full flex items-center justify-center space-x-1 px-3 py-2 rounded border border-slate-600 text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors text-xs"
              >
                <X className="w-3 h-3" />
                <span>Clear Filters</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(ActionHistoryFilter);
