import asyncio
from types import SimpleNamespace

from services.resilient_sarvam_stt import ResilientSarvamSTTService


class _WebSocket:
    def __init__(self, *, closed=False):
        self.closed = closed


class _SocketClient:
    def __init__(self, *, error=None):
        self._websocket = _WebSocket()
        self.error = error
        self.calls = 0

    async def transcribe(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error


def _service_with_socket(socket_client):
    service = object.__new__(ResilientSarvamSTTService)
    service._socket_client = socket_client
    service._input_audio_codec = "wav"
    service._sample_rate = 16000
    service._config = SimpleNamespace(use_translate_method=False)
    service._reconnect_lock = asyncio.Lock()
    service._last_reconnect_attempt = 0.0
    return service


def test_open_connection_passes_audio_without_reconnect():
    socket_client = _SocketClient()
    service = _service_with_socket(socket_client)

    async def run():
        return [frame async for frame in service.run_stt(b"\x00\x00")]

    assert asyncio.run(run()) == [None]
    assert socket_client.calls == 1


def test_send_failure_reconnects_and_retries_audio_once():
    failed_client = _SocketClient(error=RuntimeError("socket closed"))
    replacement_client = _SocketClient()
    service = _service_with_socket(failed_client)

    async def recover(client):
        assert client is failed_client
        service._socket_client = replacement_client
        return True

    service._recover_connection = recover

    async def run():
        return [frame async for frame in service.run_stt(b"\x00\x00")]

    assert asyncio.run(run()) == [None]
    assert failed_client.calls == 1
    assert replacement_client.calls == 1
