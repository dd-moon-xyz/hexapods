import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from lenia_client.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_motion_axes_are_distinct_and_allow_mounting_inversions(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, motion_screen_x='-x', motion_screen_y='y')
            self.assertEqual(settings.motion_screen_x, '-x')
            for x, y in (('x', '-x'), ('y', 'y'), ('z', 'x')):
                with self.assertRaises(ValidationError):
                    Settings(_env_file=None, motion_screen_x=x, motion_screen_y=y)

    def test_dotenv_loads_all_client_options_and_environment_overrides(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            env = Path(directory) / '.env'
            env.write_text('SERVER_ADDRESS=localhost:9999\nCONFIG=preset.json\n'
                           'WINDOWED=true\nMOTION_DEVICE=/dev/i2c-2\n'
                           'MOTION_THRESHOLD=0.2\nPERSON_PROXIMITY=0.35\n')
            settings = Settings(_env_file=env)
            self.assertEqual(settings.url, 'ws://localhost:9999/ws')
            self.assertEqual(settings.config, Path('preset.json'))
            self.assertTrue(settings.windowed)
            self.assertEqual(settings.motion_device, '/dev/i2c-2')
            self.assertEqual(settings.motion_threshold, .2)
            self.assertEqual(settings.person_proximity, .35)
            os.environ['SERVER_ADDRESS'] = 'remote:8888'
            self.assertEqual(Settings(_env_file=env).url, 'ws://remote:8888/ws')
            os.environ['PERSON_PROXIMITY'] = '0.7'
            self.assertEqual(Settings(_env_file=env).person_proximity, .7)

    def test_invalid_thresholds_rejected_at_startup(self):
        with patch.dict(os.environ, {}, clear=True):
            for value in ('0', '1', '-1', 'nan', 'inf', 'bad'):
                with self.subTest(value=value), self.assertRaises(ValidationError):
                    Settings(_env_file=None, person_proximity=value)
            for field in ('motion_threshold',):
                for value in (0, -1, float('nan'), float('inf')):
                    with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                        Settings(_env_file=None, **{field: value})

    def test_main_passes_settings_to_runtime_and_loads_json_preset(self):
        from lenia_client.client import main
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            preset = Path(directory) / 'preset.json'
            preset.write_text('{"boundary": "circle"}')
            settings = Settings(_env_file=None, config=preset, person_proximity=.7)
            with patch('sys.argv', ['lenia-client']), \
                    patch('lenia_client.client.Settings', return_value=settings), \
                    patch('lenia_client.client.load_preset') as fetch, \
                    patch('lenia_client.client.run', new_callable=AsyncMock) as run:
                main()
                fetch.assert_not_called()
                self.assertEqual(run.await_args.args, (settings.url, {'boundary': 'circle'}))
            self.assertFalse(run.await_args.kwargs['windowed'])
            self.assertTrue(run.await_args.kwargs['fit_display'])
            self.assertTrue(callable(run.await_args.kwargs['sensor_monitor']))
