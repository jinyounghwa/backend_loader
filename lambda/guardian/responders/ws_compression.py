"""
WebSocket 메시지 압축 유틸리티
gzip 기반 메시지 압축으로 대역폭 절감
"""

import base64
import gzip
import json
from typing import Dict, Any, Union


class WebSocketMessageCompressor:
    """WebSocket 메시지 압축 및 해제"""

    def __init__(self, compression_enabled: bool = True, min_size_bytes: int = 1024):
        """
        Args:
            compression_enabled: 압축 활성화 여부
            min_size_bytes: 압축 최소 크기 (이 이상만 압축)
        """
        self.compression_enabled = compression_enabled
        self.min_size_bytes = min_size_bytes
        self.stats = {
            "total_compressed": 0,
            "total_uncompressed": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0,
        }

    def compress_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        메시지를 JSON 문자열로 변환 후 gzip 압축

        Args:
            message: 압축할 메시지

        Returns:
            {
                "type": "compressed" | "uncompressed",
                "data": base64 문자열,
                "original_size": 원본 크기,
                "compressed_size": 압축 크기
            }
        """
        if not self.compression_enabled:
            return self._create_uncompressed_message(message)

        # JSON 직렬화
        json_str = json.dumps(message, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")
        original_size = len(json_bytes)

        # 최소 크기 미만이면 압축하지 않음
        if original_size < self.min_size_bytes:
            return self._create_uncompressed_message(message)

        # gzip 압축
        compressed_bytes = gzip.compress(json_bytes, compresslevel=6)
        compressed_size = len(compressed_bytes)

        # 압축 효율이 낮으면 압축하지 않음 (90% 이상)
        if compressed_size >= original_size * 0.9:
            return self._create_uncompressed_message(message)

        encoded = base64.b64encode(compressed_bytes).decode("ascii")

        self.stats["total_compressed"] += 1
        self.stats["total_original_bytes"] += original_size
        self.stats["total_compressed_bytes"] += compressed_size

        return {
            "type": "compressed",
            "data": encoded,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "ratio": round((compressed_size / original_size) * 100, 1),
        }

    def decompress_message(self, compressed_data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Base64 디코딩 후 gzip 해제

        Args:
            compressed_data: 압축된 Base64 문자열 또는 바이트

        Returns:
            원본 메시지 dict
        """
        try:
            # Base64 디코딩
            if isinstance(compressed_data, str):
                compressed_data = compressed_data.encode("ascii")

            compressed_bytes = base64.b64decode(compressed_data)

            # gzip 해제
            json_bytes = gzip.decompress(compressed_bytes)
            json_str = json_bytes.decode("utf-8")

            # JSON 파싱
            message = json.loads(json_str)

            self.stats["total_uncompressed"] += 1

            return message

        except Exception as e:
            return {"error": f"Decompression failed: {str(e)}"}

    def _create_uncompressed_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """비압축 메시지 생성"""
        json_str = json.dumps(message, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")
        size = len(json_bytes)

        encoded = base64.b64encode(json_bytes).decode("ascii")

        self.stats["total_uncompressed"] += 1
        self.stats["total_original_bytes"] += size

        return {"type": "uncompressed", "data": encoded, "size": size}

    def get_compression_stats(self) -> Dict[str, Any]:
        """압축 통계"""
        total_compressed = self.stats["total_compressed"]
        total_original = self.stats["total_original_bytes"]
        total_compressed_bytes = self.stats["total_compressed_bytes"]

        avg_ratio = 0
        if total_compressed > 0:
            avg_ratio = (total_compressed_bytes / total_original) * 100

        total_messages = self.stats["total_compressed"] + self.stats["total_uncompressed"]

        return {
            "total_messages": total_messages,
            "compressed_count": total_compressed,
            "uncompressed_count": self.stats["total_uncompressed"],
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed_bytes,
            "avg_compression_ratio": round(avg_ratio, 1),
            "total_bytes_saved": total_original - total_compressed_bytes,
            "compression_enabled": self.compression_enabled,
            "min_size_bytes": self.min_size_bytes,
        }


# 글로벌 압축기 인스턴스
_compressor = WebSocketMessageCompressor(
    compression_enabled=True, min_size_bytes=1024  # 1KB 이상만 압축
)


def compress_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """메시지 압축"""
    return _compressor.compress_message(message)


def decompress_message(compressed_data: Union[str, bytes]) -> Dict[str, Any]:
    """메시지 해제"""
    return _compressor.decompress_message(compressed_data)


def get_compression_stats() -> Dict[str, Any]:
    """압축 통계"""
    return _compressor.get_compression_stats()
