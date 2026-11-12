import unittest
from unittest.mock import Mock, patch

from lenia_client.indicator import IndicatorLight
from lenia_client.sensors import SensorInputs


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        self.gpio = Mock()
        self.led = IndicatorLight(self.gpio)

    def test_population_controls_brightness(self):
        for fraction in (1, .5, .2, 0, 1, -1, 2):
            expected = .25 * min(1, max(0, fraction))
            self.led.update(fraction)
            self.assertAlmostEqual(self.led.brightness, expected)
            self.gpio.set_brightness.assert_called_with(expected)

    def test_shutdown_stops_pwm_drives_low_and_releases_chip(self):
        self.led.close()
        self.gpio.close.assert_called_once()

    def test_sensors_do_not_override_population_indicator(self):
        inputs = SensorInputs.__new__(SensorInputs)
        inputs.proximity = Mock(strength=0)
        inputs.motion = Mock(strength=0, vector=(0.0, 0.0))
        inputs.population = {'fraction': .5}
        inputs.screen_x, inputs.screen_y = 'y', 'x'
        inputs.indicator = Mock()
        for near, moving in [(False, False), (True, False), (False, True), (True, True)]:
            inputs.proximity.active = near
            inputs.motion.poll.return_value = moving
            inputs.poll()
            inputs.indicator.update.assert_called_with(.5)

    def test_indicator_failure_closes_open_sensors(self):
        with patch('lenia_client.sensors.CameraSensor') as near, patch('lenia_client.sensors.MotionSensor') as motion, patch('lenia_client.sensors.IndicatorLight', side_effect=OSError('GPIO busy')):
            with self.assertRaisesRegex(OSError, 'GPIO busy'):
                SensorInputs('/dev/i2c-1', .5, .12)
            near.return_value.close.assert_called_once()
            motion.return_value.close.assert_called_once()


class HardwarePWMTests(unittest.TestCase):
    def test_hardware_duty_scaling_clamping_and_shutdown(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            root = Path(directory)
            chip = root / 'devices' / '1f00098000.pwm' / 'pwm' / 'pwmchip0'
            channel = chip / 'pwm2'
            channel.mkdir(parents=True)
            (root / 'pwmchip0').symlink_to(chip, target_is_directory=True)
            configure = Mock()
            pwm = HardwarePWM(root, configure)
            configure.assert_called_once()
            self.assertEqual((channel / 'period').read_text(), '500000')
            self.assertEqual((channel / 'enable').read_text(), '1')
            for brightness, duty in [(0.25, 125000), (-1, 0), (2, 500000)]:
                pwm.set_brightness(brightness)
                self.assertEqual(int((channel / 'duty_cycle').read_text()), duty)
            pwm.close()
            self.assertEqual((channel / 'duty_cycle').read_text(), '0')
            self.assertEqual((channel / 'enable').read_text(), '1')

    def test_missing_rp1_controller_is_reported(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(OSError, 'RP1 PWM0 controller unavailable'):
                HardwarePWM(Path(directory))

    def test_pwm1_controller_is_not_selected_for_gpio18(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            root = Path(directory)
            chip = root / 'devices' / '1f0009c000.pwm' / 'pwm' / 'pwmchip0'
            chip.mkdir(parents=True)
            (root / 'pwmchip0').symlink_to(chip, target_is_directory=True)
            with self.assertRaisesRegex(OSError, 'RP1 PWM0 controller unavailable'):
                HardwarePWM(root)
