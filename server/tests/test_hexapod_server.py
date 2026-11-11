import math
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from lenia.server.models import Start
from lenia.server.presets import default_config


class HexapodServerTests(unittest.TestCase):
    def test_default_fleet_needs_no_resource_files(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('Unexpected resource access')):
            config = Start.model_validate(default_config())

        self.assertEqual(config.simulation, 'hexapod')
        self.assertEqual(config.boundary, 'circle')
        self.assertEqual(len(config.organisms), 50)
        self.assertTrue(all(item.scale == 1 for item in config.organisms))
        self.assertTrue(all(math.hypot(item.x - 512, item.y - 512) <= 401 for item in config.organisms))
        self.assertTrue(all(set(item.model_dump()) == {'scale', 'x', 'y'} for item in config.organisms))

    def test_rejects_other_simulations_and_catalog_fields(self):
        base = {'action': 'start', 'organisms': [{}]}
        invalid = (
            {'simulation': 'lenia'}, {'boundary': 'wrap'}, {'excluded_types': []},
            {'organisms': [{'type': 528}]}, {'organisms': [{'velocity': 25}]},
            {'organisms': [{'x': 512}]}, {'organisms': [{}] * 101}, {'fps': 61},
        )
        for updates in invalid:
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                Start.model_validate({**base, **updates})
