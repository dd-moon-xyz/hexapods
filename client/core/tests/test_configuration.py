import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from client_core.client import load_preset, main


class ConfigurationTests(unittest.TestCase):
    def test_preset_uses_server_http_endpoint(self):
        for url, endpoint in (
            ('ws://localhost:9876/ws', 'http://localhost:9876/preset'),
            ('wss://example.test/hexapods/ws', 'https://example.test/hexapods/preset'),
        ):
            with self.subTest(url=url), patch('client_core.client.urlopen', return_value=io.BytesIO(b'{"fps": 60}')) as fetch:
                self.assertEqual(load_preset(url), {'fps': 60})
                self.assertEqual(fetch.call_args.args[0].full_url, endpoint)
                self.assertEqual(fetch.call_args.kwargs, {"timeout": 30})

    def test_default_launch_defers_preset_loading_to_runtime(self):
        config = {'action': 'start', 'organisms': [{}]}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch('sys.argv', ['local-client']),
            patch('client_core.client.load_preset', return_value=config) as fetch,
            patch('client_core.client.run', new_callable=AsyncMock) as run,
        ):
            main()

        fetch.assert_not_called()
        run.assert_awaited_once_with('ws://127.0.0.1:9877/ws', None)

    def test_explicit_configuration_bypasses_preset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            config = {'action': 'start', 'organisms': [{'scale': 2}]}
            path.write_text(json.dumps(config))
            with (
                patch('sys.argv', ['local-client', '--url', 'ws://remote:9876/ws', '--config', str(path)]),
                patch('client_core.client.load_preset') as fetch,
                patch('client_core.client.run', new_callable=AsyncMock) as run,
            ):
                main()

        fetch.assert_not_called()
        run.assert_awaited_once_with('ws://remote:9876/ws', config)

    def test_environment_configures_server_url_and_cli_overrides_it(self):
        for arguments, expected in (
            ([], 'ws://environment.test:9999/ws'),
            (['--url', 'ws://override.test/ws'], 'ws://override.test/ws'),
        ):
            with (
                self.subTest(arguments=arguments),
                patch.dict(os.environ, {'SERVER_ADDRESS': 'environment.test:9999'}),
                patch('sys.argv', ['local-client', *arguments]),
                patch('client_core.client.load_preset', return_value={}) as fetch,
                patch('client_core.client.run', new_callable=AsyncMock) as run,
            ):
                main()

            fetch.assert_not_called()
            run.assert_awaited_once_with(expected, None)
