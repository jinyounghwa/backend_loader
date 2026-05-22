'use client';

interface AuditLogsFilterProps {
  value: {
    startTime: string;
    endTime: string;
    eventType: string;
    offset: number;
    limit: number;
  };
  onChange: (
    filters: AuditLogsFilterProps['value']
  ) => void;
}

export function AuditLogsFilter({ value, onChange }: AuditLogsFilterProps) {
  const handleStartTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...value, startTime: e.target.value, offset: 0 });
  };

  const handleEndTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...value, endTime: e.target.value, offset: 0 });
  };

  const handleEventTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...value, eventType: e.target.value, offset: 0 });
  };

  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...value, limit: parseInt(e.target.value), offset: 0 });
  };

  const handleClear = () => {
    onChange({
      startTime: '',
      endTime: '',
      eventType: '',
      offset: 0,
      limit: 50,
    });
  };

  return (
    <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">필터</h3>
        <button
          onClick={handleClear}
          className="text-sm px-3 py-1 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded transition-colors"
        >
          초기화
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            시작 시간
          </label>
          <input
            type="datetime-local"
            value={value.startTime}
            onChange={handleStartTimeChange}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            종료 시간
          </label>
          <input
            type="datetime-local"
            value={value.endTime}
            onChange={handleEndTimeChange}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            이벤트 타입
          </label>
          <select
            value={value.eventType}
            onChange={handleEventTypeChange}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="">모든 이벤트</option>
            <option value="$connect">연결 (Connect)</option>
            <option value="$disconnect">연결 해제 (Disconnect)</option>
            <option value="message">메시지</option>
            <option value="broadcast">브로드캐스트</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            페이지 크기
          </label>
          <select
            value={value.limit}
            onChange={handleLimitChange}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="10">10개</option>
            <option value="25">25개</option>
            <option value="50">50개</option>
            <option value="100">100개</option>
            <option value="200">200개</option>
          </select>
        </div>
      </div>
    </div>
  );
}
