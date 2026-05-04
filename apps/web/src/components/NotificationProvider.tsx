'use client';

import { createContext, useContext, useCallback, useEffect, useState, ReactNode } from 'react';
import { useNotification, type NotificationOptions } from '@/lib/hooks/useNotification';

export interface NotificationContextType {
  notify: (title: string, options?: NotificationOptions) => void;
  requestPermission: () => Promise<boolean>;
  permission: NotificationPermission;
  isSupported: boolean;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { permission, requestPermission, sendNotification, isSupported } = useNotification();
  const [lastNotifications, setLastNotifications] = useState<{ [key: string]: number }>({});

  const notify = useCallback(
    (title: string, options?: NotificationOptions) => {
      if (!isSupported || permission !== 'granted') return;

      const tag = options?.tag || 'default';
      const now = Date.now();
      const lastTime = lastNotifications[tag] || 0;

      // 스로틀링: 같은 tag의 알림이 3초 이내에 오지 않음
      if (now - lastTime < 3000) {
        console.log(`Notification throttled for tag: ${tag}`);
        return;
      }

      setLastNotifications((prev) => ({ ...prev, [tag]: now }));

      const notification = sendNotification(title, {
        ...options,
        requireInteraction: options?.requireInteraction ?? false,
      });

      if (notification) {
        notification.addEventListener('click', () => {
          window.focus();
          notification.close();
        });
      }
    },
    [isSupported, permission, sendNotification, lastNotifications]
  );

  // 초기 권한 확인 및 요청 (선택사항)
  useEffect(() => {
    if (!isSupported) return;
    if (permission === 'default') {
      // 자동 요청하지 않음, 사용자가 명시적으로 요청해야 함
    }
  }, [isSupported, permission]);

  return (
    <NotificationContext.Provider value={{ notify, requestPermission, permission, isSupported }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotificationContext() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationContext must be used within NotificationProvider');
  }
  return context;
}
