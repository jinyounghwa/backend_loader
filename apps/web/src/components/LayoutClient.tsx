'use client';

import { useEffect, useState } from 'react';
import NotificationPermissionModal from './NotificationPermissionModal';
import OfflineBanner from './OfflineBanner';
import { useNotificationContext } from './NotificationProvider';

// Notification permission modal component
function NotificationPrompt() {
  const { permission, requestPermission, isSupported } = useNotificationContext();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!isSupported) return;
    if (permission === 'default') {
      setShowModal(true);
    }
  }, [permission, isSupported]);

  const handleAllow = async () => {
    await requestPermission();
    setShowModal(false);
  };

  return (
    <NotificationPermissionModal
      isOpen={showModal}
      onAllow={handleAllow}
      onDeny={() => setShowModal(false)}
    />
  );
}

// SSE notification stream listener component
function NotificationStreamListener() {
  const { notify, permission, isSupported } = useNotificationContext();
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    if (!isSupported || permission !== 'granted' || isListening) return;

    setIsListening(true);
    const eventSource = new EventSource('/api/notifications');

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'connected') {
          console.log('✅ Notification stream connected');
          return;
        }
        notify(data.title, {
          body: data.body,
          tag: data.tag,
          requireInteraction: data.requireInteraction,
        });
      } catch (error) {
        console.error('Failed to parse notification:', error);
      }
    };

    eventSource.onerror = () => {
      console.error('❌ Notification stream error');
      eventSource.close();
      setIsListening(false);
    };

    return () => {
      eventSource.close();
      setIsListening(false);
    };
  }, [isSupported, permission, notify, isListening]);

  return null;
}

// Service Worker registration & cache management
function ServiceWorkerManager() {
  useEffect(() => {
    // Register Service Worker (production-only recommended)
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          console.log('✅ Service Worker registered:', reg);
          // Check for updates periodically
          setInterval(() => {
            reg.update();
          }, 60000);
        })
        .catch((err) => {
          console.warn('Service Worker registration failed:', err);
        });
    }

    // Cache invalidation on network recovery
    const handleOnline = () => {
      console.log('🔄 Network recovered, clearing API cache');
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'CLEAR_API_CACHE',
        });
      }
      // Reload page to get fresh data
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    };

    window.addEventListener('online', handleOnline);
    return () => {
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  return null;
}

export function LayoutClient() {
  return (
    <>
      <NotificationPrompt />
      <NotificationStreamListener />
      <ServiceWorkerManager />
      <OfflineBanner />
    </>
  );
}
