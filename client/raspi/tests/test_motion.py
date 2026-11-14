import struct
import unittest
from unittest.mock import Mock

from hexapods_client.motion import MotionDetector, MotionSensor
from hexapods_client.sensors import steering_command


class MotionTests(unittest.TestCase):
    def detector(self, **settings):
        detector = MotionDetector(**settings)
        detector.update((0, 0, 1), (0, 0, 0), 0)
        return detector

    def test_signed_acceleration_vectors_and_diagonals(self):
        for acceleration, expected in (((.2, 0, 1), (1, 0)), ((0, -.2, 1), (0, -1)),
                                       ((.3, .4, 1), (.6, .8))):
            detector = self.detector()
            self.assertTrue(detector.update(acceleration, (0, 0, 0), .05))
            for actual, target in zip(detector.vector, expected):
                self.assertAlmostEqual(actual, target)

    def test_continued_motion_keeps_initial_direction_and_strength_without_timeout(self):
        detector = self.detector()
        detector.update((.2, 0, 1), (0, 0, 0), .05)
        expected = detector.vector, detector.strength
        for now, acceleration in ((.1, (-1, 1, 1)), (6, (1, -1, 1)), (20, (0, 2, 1))):
            self.assertTrue(detector.update(acceleration, (100, -100, 0), now))
            self.assertEqual((detector.vector, detector.strength), expected)

    def test_quiet_releases_direction_and_next_gesture_selects_a_new_one(self):
        detector = self.detector()
        detector.update((.2, 0, 1), (0, 0, 0), .05)
        self.assertTrue(detector.update((.2, 0, 1), (0, 0, 0), .1))
        self.assertTrue(detector.update((.2, 0, 1), (0, 0, 0), .3))
        self.assertFalse(detector.update((.2, 0, 1), (0, 0, 0), .4))
        self.assertTrue(detector.update((.2, -.3, 1), (0, 0, 0), .5))
        self.assertEqual(detector.vector, (0, -1))

    def test_rotation_alone_does_not_trigger_and_prevents_release(self):
        detector = self.detector()
        self.assertFalse(detector.update((0, 0, 1), (100, 100, 0), .05))
        detector.update((.2, 0, 1), (0, 0, 0), .1)
        self.assertTrue(detector.update((.2, 0, 1), (30, 0, 0), 6))
        self.assertTrue(detector.update((.2, 0, 1), (0, 0, 0), 6.1))
        self.assertFalse(detector.update((.2, 0, 1), (0, 0, 0), 6.4))

    def test_stationary_gravity_in_any_orientation_does_not_trigger(self):
        for gravity in ((0, 0, 1), (1, 0, 0), (0, -1, 0)):
            detector = MotionDetector()
            for sample in range(20):
                self.assertFalse(detector.update(gravity, (0, 0, 0), sample * .05))

    def test_z_only_and_xy_noise_do_not_trigger(self):
        detector = self.detector()
        self.assertFalse(detector.update((.01, -.01, 2), (0, 0, 100), .05))

    def test_perturbation_strength_increases_and_caps(self):
        strengths = tuple(self.trigger_strength(acceleration) for acceleration in (.12, .24, .36, .48, 1))
        for actual, expected in zip(strengths, (0, 1/3, 2/3, 1, 1)):
            self.assertAlmostEqual(actual, expected)

    def trigger_strength(self, acceleration):
        detector = self.detector()
        detector.update((acceleration, 0, 1), (0, 0, 0), .05)
        return detector.strength

    def test_movement_follows_mapped_vector_with_escape(self):
        command = steering_command(False, True, 0, .2, (.6, .8))
        self.assertEqual(command, {'action': 'movement', 'direction': 'vector',
                                  'vector': {'x': .8, 'y': .6}, 'escape': True,
                                  'speed_multiplier': 1.2})
        inverted = steering_command(False, True, motion_vector=(1, 0), screen_x='-x', screen_y='y')
        self.assertEqual(inverted['vector'], {'x': -1, 'y': 0})
        self.assertEqual(steering_command(False, False, motion_vector=(1, 0))['direction'], 'inward')

    def test_camera_keeps_radial_escape_and_its_own_speed_during_pulse(self):
        for strength in (0, .25, .8, 1):
            camera_only = steering_command(True, False, strength)
            during_pulse = steering_command(True, True, strength, 1, (.6, .8))
            self.assertEqual(during_pulse, camera_only)
            self.assertEqual(during_pulse['direction'], 'outward')
            self.assertEqual(during_pulse['speed_multiplier'], 1 + strength)

    def test_invalid_detector_settings(self):
        for field in ('threshold_g', 'threshold_dps', 'hold_seconds'):
            for value in (0, -1, float('nan'), float('inf')):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    MotionDetector(**{field: value})

    def test_sensor_decodes_little_endian_acceleration_and_gyro(self):
        sensor = MotionSensor.__new__(MotionSensor)
        sensor.detector = Mock()
        sensor._read = Mock(side_effect=[b'\x03', struct.pack('<6h', 1000, -2000, 0, 0, 0, 16384)])
        sensor.poll()
        acceleration, rotation, _ = sensor.detector.update.call_args.args
        self.assertAlmostEqual(acceleration[2], .999424)
        self.assertEqual(rotation, (8.75, -17.5, 0))

    def test_stale_readings_cannot_release_or_change_direction(self):
        from unittest.mock import patch

        sensor = MotionSensor.__new__(MotionSensor)
        sensor.detector = self.detector()
        sensor.detector.update((.2, 0, 1), (0, 0, 0), .05)
        sensor._read = Mock(return_value=b'\x00')
        with patch('hexapods_client.motion.time.monotonic', side_effect=(.5, 1.1)):
            self.assertTrue(sensor.poll())
            self.assertTrue(sensor.poll())
        self.assertEqual(sensor.detector.vector, (1, 0))


class SensorMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def test_sensor_poll_maps_vector_and_keeps_camera_controls_radial(self):
        from unittest.mock import patch
        from hexapods_client.sensors import SensorInputs

        with patch('hexapods_client.sensors.CameraSensor') as camera, \
                patch('hexapods_client.sensors.MotionSensor') as motion, \
                patch('hexapods_client.sensors.IndicatorLight'):
            camera.return_value.active = False
            camera.return_value.strength = .8
            motion.return_value.poll.return_value = True
            motion.return_value.strength = .2
            motion.return_value.vector = (.6, .8)
            inputs = SensorInputs('/dev/i2c-1', .5, .12, '-x', 'y')
            self.assertEqual(inputs.poll()['vector'], {'x': -.6, 'y': .8})
            self.assertEqual(inputs.poll()['speed_multiplier'], 1.2)
            camera.return_value.active = True
            self.assertEqual(inputs.poll(), steering_command(True, False, .8))
            camera.return_value.active = False
            self.assertEqual(inputs.poll()['direction'], 'vector')
            inputs.close()

    async def test_camera_transitions_preserve_latched_motion_direction(self):
        from unittest.mock import patch
        from hexapods_client.sensors import SensorInputs

        detector = MotionDetector()
        detector.update((0, 0, 1), (0, 0, 0), 0)
        detector.update((.2, 0, 1), (0, 0, 0), .05)
        with patch('hexapods_client.sensors.CameraSensor') as camera, \
                patch('hexapods_client.sensors.MotionSensor') as motion, \
                patch('hexapods_client.sensors.IndicatorLight'):
            inputs = SensorInputs('/dev/i2c-1', .5, .12)
            motion.return_value.vector = detector.vector
            motion.return_value.strength = detector.strength
            motion.return_value.poll.side_effect = (True, True, True, False)
            camera.return_value.strength = .8
            camera.return_value.active = False
            self.assertEqual(inputs.poll()['direction'], 'vector')
            camera.return_value.active = True
            self.assertEqual(inputs.poll(), steering_command(True, False, .8))
            camera.return_value.active = False
            self.assertEqual(inputs.poll()['direction'], 'vector')
            self.assertEqual(inputs.poll()['direction'], 'inward')
            self.assertEqual(detector.vector, (1, 0))
            inputs.close()

    async def test_initial_mode_and_transitions_and_cleanup(self):
        import asyncio
        from unittest.mock import patch
        from hexapods_client.sensors import monitor_sensors

        inputs = Mock()
        idle, near, moving = (steering_command(False, False), steering_command(True, False), steering_command(False, True))
        inputs.poll.side_effect = [idle, near, moving, moving, near, idle, OSError('disconnected')]
        commands = asyncio.Queue()
        with patch('hexapods_client.sensors.SensorInputs', return_value=inputs):
            with self.assertRaisesRegex(OSError, 'disconnected'):
                await monitor_sensors(commands)
        self.assertEqual([commands.get_nowait() for _ in range(commands.qsize())],
                         [idle, near, moving, near, idle])
        inputs.close.assert_called_once()

    async def test_partial_startup_failure_closes_camera(self):
        from unittest.mock import patch
        from hexapods_client.sensors import SensorInputs
        with patch('hexapods_client.sensors.CameraSensor') as camera, patch('hexapods_client.sensors.MotionSensor', side_effect=OSError('missing motion sensor')):
            with self.assertRaisesRegex(OSError, 'missing motion sensor'):
                SensorInputs('/dev/i2c-1', .5, .12)
            camera.return_value.close.assert_called_once()
