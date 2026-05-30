"""Mobile device authentication."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class DeviceAuthenticator:
    """Authenticate and manage mobile devices."""

    def __init__(self):
        self.registered_devices: Dict[str, Dict[str, Any]] = {}
        self.biometric_verifications: Dict[str, bool] = {}

    def register_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Register new mobile device."""
        device_id = str(uuid.uuid4())

        device = {
            'device_id': device_id,
            'device_token': device_info.get('device_token'),
            'device_name': device_info.get('device_name'),
            'device_type': device_info.get('device_type'),  # iOS, Android
            'status': 'registered',
            'is_trusted': False,
            'registered_at': datetime.utcnow().isoformat(),
            'last_seen': datetime.utcnow().isoformat()
        }

        self.registered_devices[device_id] = device

        return {
            'device_id': device_id,
            'device_token': device_info.get('device_token'),
            'status': 'registered',
            'is_trusted': False
        }

    def verify_device(self, verification: Dict[str, Any]) -> Dict[str, Any]:
        """Verify device with biometric authentication."""
        device_id = verification.get('device_id')
        biometric_type = verification.get('biometric_type')  # FACE_ID, FINGERPRINT

        # Simulate biometric verification
        authenticated = True

        if device_id in self.registered_devices:
            device = self.registered_devices[device_id]
            device['last_seen'] = datetime.utcnow().isoformat()

        if biometric_type:
            self.biometric_verifications[device_id] = authenticated

        return {
            'authenticated': authenticated,
            'device_id': device_id,
            'biometric_type': biometric_type,
            'verified_at': datetime.utcnow().isoformat()
        }

    def revoke_device(self, device_id: str) -> Dict[str, Any]:
        """Revoke access for compromised device."""
        revoked_at = datetime.utcnow().isoformat()

        if device_id in self.registered_devices:
            device = self.registered_devices[device_id]
            device['status'] = 'revoked'
            device['revoked_at'] = revoked_at
        else:
            # Register and revoke if not exists
            self.registered_devices[device_id] = {
                'device_id': device_id,
                'status': 'revoked',
                'revoked_at': revoked_at
            }

        return {
            'status': 'revoked',
            'device_id': device_id,
            'revoked_at': revoked_at
        }

    def trust_device(self, device_id: str) -> Dict[str, Any]:
        """Mark device as trusted."""
        if device_id in self.registered_devices:
            device = self.registered_devices[device_id]
            device['is_trusted'] = True
            device['trusted_at'] = datetime.utcnow().isoformat()

            return {
                'status': 'trusted',
                'device_id': device_id,
                'is_trusted': True
            }

        return {'status': 'not_found', 'device_id': device_id}

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status and trust level."""
        if device_id in self.registered_devices:
            device = self.registered_devices[device_id]
            return {
                'device_id': device_id,
                'status': device['status'],
                'is_trusted': device['is_trusted'],
                'device_type': device['device_type'],
                'last_seen': device['last_seen']
            }

        return {'status': 'not_found', 'device_id': device_id}
