'use client';

import { useEffect } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { Toast } from '@/types/toast';
import { useToast } from '@/lib/hooks/useToast';

interface ToastItemProps {
  toast: Toast;
}

export default function ToastItem({ toast }: ToastItemProps) {
  const { dismissToast } = useToast();

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        dismissToast(toast.id);
      }, toast.duration);
      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, dismissToast]);

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />;
      default:
        return <Info className="w-5 h-5 text-blue-400 flex-shrink-0" />;
    }
  };

  const getBgColor = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-green-500/10 border-green-500/30';
      case 'error':
        return 'bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/30';
      default:
        return 'bg-blue-500/10 border-blue-500/30';
    }
  };

  return (
    <div
      className={`
        animate-in fade-in slide-in-from-right-4 duration-300
        mb-3 p-4 rounded-lg border flex gap-3 ${getBgColor()}
      `}
    >
      {getIcon()}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-100">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-slate-400 mt-1">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => dismissToast(toast.id)}
        className="text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
