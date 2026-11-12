import unittest
import os
from unittest.mock import Mock, patch

from lenia_client.person import CameraSensor, PersonProximity
from lenia_client.person_camera import person_height
from lenia_client.sensors import steering_command


class PersonTests(unittest.TestCase):
    def test_filters_objects_and_low_confidence_and_uses_nearest_person(self):
        self.assertAlmostEqual(person_height(
            [[0, 0, .9, 1], [.1, .1, .8, .5], [.1, .5, .6, 1], [0, 0, 1, 1]],
            [.9, .8, .9, .5], [1, 0, 0, 0]), .7)
        self.assertEqual(person_height([], [], []), 0)

    def test_clips_boxes_and_rejects_invalid_coordinates(self):
        self.assertEqual(person_height([[-.2, 0, 1.2, 1]], [.9], [0]), 1)
        self.assertEqual(person_height([[0, 0, float('nan'), 1]], [.9], [0]), 0)

    def test_three_frames_and_hysteresis(self):
        detector = PersonProximity(.5)
        for _ in range(2):
            detector.update(.6)
            self.assertFalse(detector.active)
        detector.update(.6)
        self.assertTrue(detector.active)
        for _ in range(5):
            detector.update(.45)
        self.assertTrue(detector.active)
        for _ in range(3):
            detector.update(0)
        self.assertFalse(detector.active)

    def test_unconfirmed_spikes_do_not_accumulate(self):
        detector = PersonProximity()
        for height in [.6, .6, 0, .6, .6]:
            detector.update(height)
        self.assertFalse(detector.active)

    def test_threshold_tuning_and_motion_combination(self):
        for threshold, expected in ((.3, True), (.7, False)):
            detector = PersonProximity(threshold)
            for _ in range(3):
                detector.update(.5)
            self.assertEqual(detector.active, expected)
            self.assertEqual(steering_command(detector.active, False, detector.strength)['direction'],
                             'outward' if expected else 'inward')
            command = steering_command(detector.active, True, detector.strength, 1)
            expected_speed = round(1 + detector.strength, 2) if expected else 2
            self.assertEqual(command['speed_multiplier'], expected_speed)

    def test_invalid_thresholds(self):
        for threshold in (0, 1, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                PersonProximity(threshold)


class CameraWorkerTests(unittest.TestCase):
    def setUp(self):
        read, self.writer = os.pipe()
        self.process = Mock(stdout=os.fdopen(read, 'rb'), returncode=1)
        self.process.poll.return_value = None
        with patch('lenia_client.person.subprocess.Popen', return_value=self.process):
            self.sensor = CameraSensor()

    def tearDown(self):
        self.sensor.close()
        os.close(self.writer)

    def test_partial_messages_and_fresh_confirmations(self):
        os.write(self.writer, b'{"height":')
        self.sensor.poll()
        self.assertFalse(self.sensor.received)
        os.write(self.writer, b'0.8}\n{"height":0.8}\n{"height":0.8}\n')
        self.sensor.poll()
        self.assertTrue(self.sensor.received)
        self.assertTrue(self.sensor.active)
        # Polling repeatedly without new inference cannot clear/reconfirm state.
        self.sensor.poll()
        self.assertTrue(self.sensor.active)

    def test_worker_exit_is_reported(self):
        self.process.poll.return_value = 1
        with self.assertRaisesRegex(OSError, 'exited'):
            self.sensor.poll()

    def test_stale_inference_is_reported(self):
        os.write(self.writer, b'{"height":0}\n')
        self.sensor.poll()
        self.sensor.last_sample -= 6
        with self.assertRaisesRegex(OSError, 'timed out'):
            self.sensor.poll()
