'use client';

import { Bell, Search, Clock } from 'lucide-react';
import { mockDashboardSummary } from '@/lib/mock-data';

export function Header() {
  const { last_check, next_check, system_health } = mockDashboardSummary;
  
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const h = date.getHours().toString().padStart(2, '0');
    const m = date.getMinutes().toString().padStart(2, '0');
    return `${h}:${m}`;
  };

  return (
    <header className="h-16 bg-[#1a1d27]/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center text-slate-400">
        <Search className="w-4 h-4 mr-2" />
        <span className="text-sm font-mono">Search resources... (Press '/')</span>
      </div>
      
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-4 text-sm font-mono">
          <div className="flex items-center text-slate-400">
            <Clock className="w-4 h-4 mr-1.5" />
            <span>Last check: {formatTime(last_check)}</span>
          </div>
          <div className="text-slate-500">|</div>
          <div className="text-amber-500/80">
            Next check in: 55:00
          </div>
        </div>
        
        <div className="relative">
          <Bell className="w-5 h-5 text-slate-400 hover:text-slate-200 cursor-pointer transition-colors" />
          {system_health !== 'healthy' && (
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[#1a1d27]" />
          )}
        </div>
        
        <div className="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-bold text-slate-300">
          AD
        </div>
      </div>
    </header>
  );
}
