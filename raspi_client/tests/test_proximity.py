import unittest
from unittest.mock import Mock, patch

from lenia_client.proximity import ProximitySensor


class ProximityTests(unittest.TestCase):
    def sensor(self, values):
        sensor = ProximitySensor.__new__(ProximitySensor)
        sensor.threshold = 30
        sensor.release_threshold = 22
        sensor.active = False
        sensor.confirmations = 0
        samples = []
        for value in values:
            samples.extend([b'\x01', bytes([value & 255, value >> 8])])
        sensor._read = Mock(side_effect=samples)
        return sensor

    def test_confirmation_hysteresis_and_no_repeated_commands(self):
        sensor = self.sensor([30, 29, 30, 31, 28, 22, 21, 20])
        self.assertEqual([sensor.poll() for _ in range(8)],
                         [None, None, None, True, None, None, None, False])

    def test_reflection_strength_increases_and_caps(self):
        sensor = self.sensor([30, 30, 105, 180, 330, 1000])
        strengths = []
        for _ in range(6):
            sensor.poll()
            strengths.append(sensor.strength)
        self.assertEqual(strengths, [0, 0, .25, .5, 1, 1])
        sensor.active = False
        self.assertEqual(sensor.strength, 0)

    def test_stale_sample_is_ignored(self):
        sensor = self.sensor([])
        sensor._read = Mock(return_value=b'\x00')
        self.assertIsNone(sensor.poll())
        sensor._read.assert_called_once_with(0x8C, 1)

    def test_saturation_triggers_presence(self):
        sensor = self.sensor([0x8000, 0x8000])
        self.assertIsNone(sensor.poll())
        self.assertEqual(sensor.poll(), True)

    def test_maximum_led_configuration_and_background_calibration(self):
        with patch('lenia_client.proximity.os.open', return_value=42), patch('lenia_client.proximity.fcntl.ioctl'), patch('lenia_client.proximity.os.write') as write, patch('lenia_client.proximity.os.read', side_effect=[b'\x92'] + [b'\xea\x00'] * 20), patch('lenia_client.proximity.os.close'), patch('lenia_client.proximity.time.sleep'):
            sensor = ProximitySensor()
            self.assertEqual(sensor.threshold, 249)
            self.assertEqual(sensor.release_threshold, 241)
            self.assertTrue(any(call.args == (42, b'\x82\x1c') for call in write.call_args_list))
            self.assertTrue(any(call.args == (42, b'\x83\x0f') for call in write.call_args_list))

    def test_failed_identification_closes_device(self):
        with patch('lenia_client.proximity.os.open', return_value=42), patch('lenia_client.proximity.fcntl.ioctl'), patch('lenia_client.proximity.os.write'), patch('lenia_client.proximity.os.read', return_value=b'\x00'), patch('lenia_client.proximity.os.close') as close:
            with self.assertRaises(OSError):
                ProximitySensor()
            close.assert_called_once_with(42)

