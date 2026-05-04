import { memo, useState } from 'react';
import ConfirmationDialog from './Dashboard/ConfirmationDialog';

interface NotificationPermissionModalProps {
  isOpen: boolean;
  onAllow: () => Promise<void>;
  onDeny: () => void;
}

function NotificationPermissionModal({ isOpen, onAllow, onDeny }: NotificationPermissionModalProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleAllow = async () => {
    setIsLoading(true);
    try {
      await onAllow();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ConfirmationDialog
      isOpen={isOpen}
      title="브라우저 알림 활성화"
      message="보안 이벤트와 경고를 실시간으로 받으시겠습니까? 나중에 설정에서 변경할 수 있습니다."
      confirmText="활성화"
      cancelText="나중에"
      isDangerous={false}
      isLoading={isLoading}
      onConfirm={handleAllow}
      onCancel={onDeny}
    />
  );
}

export default memo(NotificationPermissionModal);
