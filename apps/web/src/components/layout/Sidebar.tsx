'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Shield, LayoutDashboard, DollarSign, Server, Database, Activity, MessageCircle } from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Cost', href: '/cost', icon: DollarSign },
  { name: 'EC2', href: '/ec2', icon: Server },
  { name: 'S3', href: '/s3', icon: Database },
  { name: 'Events', href: '/events', icon: Activity },
  { name: 'Telegram', href: '/telegram', icon: MessageCircle },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#1a1d27] border-r border-slate-800 flex flex-col h-screen sticky top-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <Shield className="w-6 h-6 text-amber-500 mr-3" />
        <span className="text-lg font-bold text-slate-100 tracking-wider">AWS GUARDIAN</span>
      </div>
      
      <nav className="flex-1 py-6 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center px-3 py-2.5 rounded-md transition-colors group ${
                isActive 
                  ? 'bg-slate-800/50 text-amber-500' 
                  : 'text-slate-400 hover:bg-slate-800/30 hover:text-slate-200'
              }`}
            >
              <Icon className={`w-5 h-5 mr-3 ${isActive ? 'text-amber-500' : 'text-slate-500 group-hover:text-slate-400'}`} />
              <span className="font-medium">{item.name}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]" />
              )}
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-800">
        <div className="bg-slate-900/50 rounded-md p-3 border border-slate-800/50">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 font-mono">System Status</div>
          <div className="flex items-center">
            <div className="w-2 h-2 rounded-full bg-green-500 mr-2 shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse" />
            <span className="text-sm text-slate-300 font-mono">Active Monitoring</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
