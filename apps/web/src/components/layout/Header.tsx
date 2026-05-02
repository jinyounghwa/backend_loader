'use client';

import { Bell, Search, Clock, LogOut } from 'lucide-react';
import { useSession, signOut } from 'next-auth/react';
import { mockDashboardSummary } from '@/lib/mock-data';

export function Header() {
  const { data: session } = useSession();
  const { last_check, next_check, system_health } = mockDashboardSummary;

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const h = date.getHours().toString().padStart(2, '0');
    const m = date.getMinutes().toString().padStart(2, '0');
    return `${h}:${m}`;
  };

  const getInitials = (name: string | null | undefined) => {
    if (!name) return "?";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
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

        <div className="flex items-center space-x-3 border-l border-slate-700 pl-4">
          {session?.user?.image ? (
            <img
              src={session.user.image}
              alt={session.user.name || "User"}
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              {getInitials(session?.user?.name)}
            </div>
          )}
          <div className="text-xs font-mono text-slate-400 hidden sm:block">
            {session?.user?.name}
          </div>
          <button
            onClick={() => signOut()}
            className="p-1.5 hover:bg-slate-700/50 rounded transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4 text-slate-400 hover:text-slate-200" />
          </button>
        </div>
      </div>
    </header>
  );
}
