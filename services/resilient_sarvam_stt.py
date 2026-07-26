"""Sarvam STT with bounded recovery from a dropped WebSocket."""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from pipecat.frames.frames import ErrorFrame
from pipecat.services.sarvam.stt import SarvamSTTService


class ResilientSarvamSTTService(SarvamSTTService):
    """Reconnect once when Sarvam's streaming socket closes during a call."""

    _RECONNECT_BACKOFF_SECS = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reconnect_lock = asyncio.Lock()
        self._last_reconnect_attempt = 0.0

    def _connection_is_open(self) -> bool:
        if not self._socket_client:
            return False
        websocket = getattr(self._socket_client, "_websocket", None)
        return websocket is None or not bool(getattr(websocket, "closed", False))

    async def _recover_connection(self, failed_client) -> bool:
        async with self._reconnect_lock:
            if self._socket_client is not failed_client and self._connection_is_open():
                return True

            now = time.monotonic()
            if now - self._last_reconnect_attempt < self._RECONNECT_BACKOFF_SECS:
                return False
            self._last_reconnect_attempt = now

            logger.warning("Sarvam STT connection dropped; reconnecting once")
            await self._disconnect()
            await self._connect()
            return self._connection_is_open()

    async def run_stt(self, audio: bytes):
        if not self._connection_is_open():
            await self._recover_connection(self._socket_client)
        if not self._connection_is_open():
            yield None
            return

        failed_client = self._socket_client
        async for frame in super().run_stt(audio):
            if not isinstance(frame, ErrorFrame):
                yield frame
                continue

            if not await self._recover_connection(failed_client):
                yield frame
                return

            async for retry_frame in super().run_stt(audio):
                yield retry_frame
            return
