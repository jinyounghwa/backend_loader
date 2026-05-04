import { memo } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { useOnline } from '@/lib/hooks/useOnline';

function OfflineBanner() {
  const isOnline = useOnline();

  if (isOnline) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 bg-red-900/80 border-t border-red-800 text-white px-4 py-3 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <WifiOff className="w-4 h-4 flex-shrink-0" />
        <span className="text-sm">오프라인 상태입니다. 캐시된 데이터를 사용하고 있습니다.</span>
      </div>
    </div>
  );
}

export default memo(OfflineBanner);
