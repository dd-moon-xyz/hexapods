import asyncio
import io
import os
from unittest.mock import MagicMock, patch

from websockets.asyncio.server import serve

from client_core.auth import headers
from client_core.client import display_stream, load_preset


def test_token_configuration_and_preset_authentication():
    with patch.dict(os.environ, {"HEXAPODS_TOKEN": "client-secret"}):
        assert headers() == {"Authorization": "Bearer client-secret"}
        assert headers("override") == {"Authorization": "Bearer override"}
        assert headers("") == {}
        with patch("client_core.client.urlopen", return_value=io.BytesIO(b'{}')) as fetch:
            assert load_preset("wss://example.test/ws") == {}

        request = fetch.call_args.args[0]
        assert request.full_url == "https://example.test/preset"
        assert request.get_header("Authorization") == "Bearer client-secret"


def test_websocket_sends_token_in_handshake():
    async def check():
        async def server(socket):
            assert socket.request.headers["Authorization"] == "Bearer client-secret"
            await socket.recv()
            await socket.send('{"status": "stopped"}')

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            await asyncio.wait_for(display_stream(
                f"ws://127.0.0.1:{port}/ws", {}, asyncio.Queue(), MagicMock(), token="client-secret",
            ), 5)

    asyncio.run(check())
