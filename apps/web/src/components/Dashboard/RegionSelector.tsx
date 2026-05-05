'use client';

import { useCallback, useEffect, useState, memo } from 'react';
import { Globe } from 'lucide-react';

const AVAILABLE_REGIONS = [
  { code: 'ap-northeast-1', name: 'Tokyo' },
  { code: 'us-east-1', name: 'N. Virginia' },
  { code: 'us-west-2', name: 'Oregon' },
  { code: 'eu-west-1', name: 'Ireland' },
  { code: 'ap-southeast-1', name: 'Singapore' },
];

interface RegionSelectorProps {
  onRegionsChange: (regions: string[]) => void;
}

function RegionSelector({ onRegionsChange }: RegionSelectorProps) {
  const [selectedRegions, setSelectedRegions] = useState<string[]>(['ap-northeast-1']);

  useEffect(() => {
    const stored = localStorage.getItem('selectedRegions');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setSelectedRegions(parsed);
      } catch {
        setSelectedRegions(['ap-northeast-1']);
      }
    }
  }, []);

  const handleToggleRegion = useCallback((region: string) => {
    setSelectedRegions(prev => {
      const updated = prev.includes(region)
        ? prev.filter(r => r !== region)
        : [...prev, region];

      if (updated.length === 0) return prev;

      localStorage.setItem('selectedRegions', JSON.stringify(updated));
      onRegionsChange(updated);
      return updated;
    });
  }, [onRegionsChange]);

  const handleSelectAll = useCallback(() => {
    const allRegions = AVAILABLE_REGIONS.map(r => r.code);
    localStorage.setItem('selectedRegions', JSON.stringify(allRegions));
    setSelectedRegions(allRegions);
    onRegionsChange(allRegions);
  }, [onRegionsChange]);

  const handleClearAll = useCallback(() => {
    const defaultRegions = ['ap-northeast-1'];
    localStorage.setItem('selectedRegions', JSON.stringify(defaultRegions));
    setSelectedRegions(defaultRegions);
    onRegionsChange(defaultRegions);
  }, [onRegionsChange]);

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Globe className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-slate-200">AWS Regions</h3>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleSelectAll}
            className="text-xs px-2 py-1 bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors"
          >
            All
          </button>
          <button
            onClick={handleClearAll}
            className="text-xs px-2 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {AVAILABLE_REGIONS.map(region => (
          <button
            key={region.code}
            onClick={() => handleToggleRegion(region.code)}
            className={`px-3 py-2 rounded text-xs font-medium transition-colors ${
              selectedRegions.includes(region.code)
                ? 'bg-blue-500/30 text-blue-300 border border-blue-400'
                : 'bg-slate-700/50 text-slate-400 border border-slate-600 hover:bg-slate-600/50'
            }`}
          >
            {region.name}
          </button>
        ))}
      </div>
    </div>
  );
}

export default memo(RegionSelector);
