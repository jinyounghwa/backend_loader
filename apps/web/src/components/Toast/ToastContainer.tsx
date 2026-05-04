'use client';

import { useToast } from '@/lib/hooks/useToast';
import ToastItem from './ToastItem';

export default function ToastContainer() {
  const { toasts } = useToast();

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm pointer-events-none">
      <div className="space-y-3 pointer-events-auto">
        {toasts.map(toast => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </div>
    </div>
  );
}
