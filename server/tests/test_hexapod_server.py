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
        self.assertEqual(config.birth_rate_min, 1)
        self.assertEqual(config.birth_rate_max, 5)
        self.assertEqual(len(config.organisms), 50)
        self.assertTrue(all(item.scale == 1 for item in config.organisms))
        self.assertTrue(all(math.hypot(item.x - 512, item.y - 512) <= 401 for item in config.organisms))
        self.assertTrue(all(set(item.model_dump()) == {'scale', 'x', 'y'} for item in config.organisms))

    def test_birth_rate_defaults_and_custom_bounds(self):
        base = {'action': 'start', 'organisms': [{}]}
        config = Start.model_validate(base)
        self.assertEqual((config.birth_rate_min, config.birth_rate_max), (1, 5))
        for minimum, maximum in ((2, 8), (3, 3), (.5, 2)):
            config = Start.model_validate({**base, 'birth_rate_min': minimum, 'birth_rate_max': maximum})
            self.assertEqual((config.birth_rate_min, config.birth_rate_max), (minimum, maximum))

    def test_interaction_bounds(self):
        base = {'action': 'start', 'organisms': [{}]}
        config = Start.model_validate(base)
        self.assertEqual((config.interaction_count_min, config.interaction_count_max), (1, 10))
        config = Start.model_validate({**base, 'interaction_count_min': 3, 'interaction_count_max': 3})
        self.assertEqual((config.interaction_count_min, config.interaction_count_max), (3, 3))
        for minimum, maximum in ((0, 10), (5, 1), (1, 0), (1.5, 10), (True, 10)):
            with self.subTest(minimum=minimum, maximum=maximum), self.assertRaises(ValidationError):
                Start.model_validate({**base, 'interaction_count_min': minimum, 'interaction_count_max': maximum})

    def test_rejects_invalid_birth_rates(self):
        base = {'action': 'start', 'organisms': [{}]}
        for minimum, maximum in ((0, 5), (-1, 5), (5, 1), (1, 0), (math.inf, 5), (1, math.nan)):
            with self.subTest(minimum=minimum, maximum=maximum), self.assertRaises(ValidationError):
                Start.model_validate({**base, 'birth_rate_min': minimum, 'birth_rate_max': maximum})

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
