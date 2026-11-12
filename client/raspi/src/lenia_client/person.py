import json
import math
import os
from pathlib import Path
import subprocess
import time


class PersonProximity:
    def __init__(self, threshold=0.5):
        if not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError('Person proximity must be greater than 0 and less than 1')
        self.threshold = threshold
        self.active = False
        self.height = 0.0
        self.confirmations = 0

    def update(self, height):
        if not math.isfinite(height) or not 0 <= height <= 1:
            raise ValueError('Invalid person box height')
        self.height = height
        near = height >= (self.threshold * 0.8 if self.active else self.threshold)
        if near == self.active:
            self.confirmations = 0
        else:
            self.confirmations += 1
            if self.confirmations >= 3:
                self.active = near
                self.confirmations = 0
                print(f'Person proximity: height={height:.2f}, {"near" if near else "clear"}', flush=True)

    @property
    def strength(self):
        return min(1.0, max(0.0, (self.height - self.threshold) / (1 - self.threshold))) if self.active else 0.0


class CameraSensor(PersonProximity):
    def __init__(self, threshold=0.5):
        super().__init__(threshold)
        self.buffer = b''
        self.last_sample = time.monotonic()
        self.received = False
        self.process = subprocess.Popen(
            ['/usr/bin/python3', '-u', str(Path(__file__).with_name('person_camera.py'))],
            stdout=subprocess.PIPE,
        )
        os.set_blocking(self.process.stdout.fileno(), False)

    def poll(self):
        if self.process.poll() is not None:
            raise OSError(f'Person camera exited with status {self.process.returncode}; check camera logs')
        while True:
            try:
                chunk = os.read(self.process.stdout.fileno(), 65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            self.buffer += chunk
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                sample = json.loads(line)
                self.update(sample['height'])
                self.last_sample = time.monotonic()
                self.received = True
        # First-time model loading can take minutes. Motion remains available.
        if time.monotonic() - self.last_sample > (5 if self.received else 180):
            raise OSError('Person camera inference timed out')

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        finally:
            self.process.stdout.close()
