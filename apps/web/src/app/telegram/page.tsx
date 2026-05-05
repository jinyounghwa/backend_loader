'use client';

import { mockTelegramChat } from '@/lib/mock-telegram-chat';
import { Bot } from 'lucide-react';

export default function TelegramPage() {
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-4xl mx-auto bg-[#0f1117] border border-slate-800 rounded-xl overflow-hidden">
      <div className="flex items-center px-6 py-4 bg-[#1a1d27] border-b border-slate-800">
        <div className="relative">
          <div className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6 text-slate-300" />
          </div>
          <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-[#1a1d27] rounded-full"></div>
        </div>
        <div className="ml-4">
          <h1 className="text-lg font-semibold text-slate-100">AWS Guardian Bot</h1>
          <p className="text-sm text-slate-400">bot</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0f1117]">
        {mockTelegramChat.map((day, dayIdx) => (
          <div key={dayIdx} className="space-y-6">
            <div className="flex justify-center">
              <div className="px-4 py-1 text-xs font-medium text-slate-400 bg-slate-800/50 rounded-full">
                {day.date}
              </div>
            </div>

            <div className="space-y-4">
              {day.messages.map((msg) => {
                const isUser = msg.role === 'user';
                
                let botBorderClass = '';
                if (!isUser) {
                  if (msg.status === 'success') botBorderClass = 'border-l-2 border-l-green-500';
                  else if (msg.status === 'failed') botBorderClass = 'border-l-2 border-l-red-500';
                  else if (msg.text.includes('경고') || msg.text.includes('초과')) botBorderClass = 'border-l-2 border-l-amber-500';
                }

                return (
                  <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {!isUser && (
                      <div className="w-8 h-8 bg-slate-800 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-auto mb-5">
                        <span className="text-sm">🤖</span>
                      </div>
                    )}
                    
                    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
                      <div 
                        className={`px-4 py-3 text-sm whitespace-pre-line font-mono ${
                          isUser 
                            ? 'bg-amber-500/20 border border-amber-500/30 rounded-2xl rounded-tr-sm text-amber-50' 
                            : `bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm text-slate-200 ${botBorderClass}`
                        }`}
                      >
                        {msg.text}
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 px-1">
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 bg-[#1a1d27] border-t border-slate-800 text-center">
        <p className="text-sm text-slate-500">이 대화는 텔레그램 봇과의 대화 기록입니다</p>
      </div>
    </div>
  );
}
