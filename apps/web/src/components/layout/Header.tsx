'use client';

import { Bell, Search, Clock, LogOut, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { mockDashboardSummary } from '@/lib/mock-data';

export function Header() {
  const { data: session } = useSession();
  const { last_check, next_check, system_health } = mockDashboardSummary;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
    <>
      <header className="h-14 md:h-16 bg-[#1a1d27]/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-3 md:px-6 sticky top-0 z-10">
        {/* Mobile Menu Toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 hover:bg-slate-800 rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          title="Menu"
        >
          {mobileMenuOpen ? (
            <X className="w-5 h-5 text-slate-400" />
          ) : (
            <Menu className="w-5 h-5 text-slate-400" />
          )}
        </button>

        {/* Desktop Search Bar */}
        <div className="hidden md:flex items-center text-slate-400 flex-1 ml-4">
          <Search className="w-4 h-4 mr-2" />
          <span className="text-sm font-mono">Search resources... (Press '/')</span>
        </div>

        {/* Logo/Title - Mobile */}
        <div className="md:hidden flex-1 flex justify-center">
          <span className="text-xs font-bold text-slate-300">Guardian</span>
        </div>

        {/* Right Section */}
        <div className="hidden md:flex items-center space-x-6">
          <div className="flex items-center space-x-4 text-xs md:text-sm font-mono">
            <div className="flex items-center text-slate-400">
              <Clock className="w-4 h-4 mr-1.5" />
              <span className="hidden lg:inline">Last check: {formatTime(last_check)}</span>
            </div>
            <div className="hidden lg:block text-slate-500">|</div>
            <div className="hidden lg:block text-amber-500/80">
              Next check in: 55:00
            </div>
          </div>

          <div className="relative min-h-[44px] min-w-[44px] flex items-center justify-center">
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
              className="p-2 hover:bg-slate-700/50 rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              title="Sign out"
            >
              <LogOut className="w-4 h-4 text-slate-400 hover:text-slate-200" />
            </button>
          </div>
        </div>

        {/* Mobile Right Icons */}
        <div className="md:hidden flex items-center space-x-3">
          <div className="relative min-h-[44px] min-w-[44px] flex items-center justify-center">
            <Bell className="w-5 h-5 text-slate-400" />
            {system_health !== 'healthy' && (
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </div>
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
        </div>
      </header>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#1a1d27] border-b border-slate-800">
          <div className="p-4 space-y-4">
            <div className="flex items-center text-slate-400 text-sm">
              <Clock className="w-4 h-4 mr-2" />
              <span className="font-mono">Last check: {formatTime(last_check)}</span>
            </div>
            <div className="text-xs font-mono text-slate-400">
              {session?.user?.name}
            </div>
            <button
              onClick={() => {
                signOut();
                setMobileMenuOpen(false);
              }}
              className="w-full p-2 text-left text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </>
  );
}
