import fcntl
import math
import os
import struct
import time


class MotionDetector:
    def __init__(self, threshold_g=0.12, threshold_dps=20.0, hold_seconds=0.25):
        if not all(math.isfinite(value) and value > 0
                   for value in (threshold_g, threshold_dps, hold_seconds)):
            raise ValueError("Motion thresholds and timing settings must be positive and finite")
        self.threshold_g = threshold_g
        self.threshold_dps = threshold_dps
        self.hold_seconds = hold_seconds
        self.previous_acceleration = None
        self.strength = 0.0
        self.vector = (0.0, 0.0)
        self.quiet_since = None
        self.armed = True

    def update(self, acceleration, rotation, now):
        if self.previous_acceleration is None:
            self.previous_acceleration = acceleration
        change = tuple(value - base for value, base in zip(acceleration[:2], self.previous_acceleration[:2]))
        delta = math.hypot(*change)
        spin = math.hypot(*rotation[:2])
        self.previous_acceleration = acceleration
        if delta >= self.threshold_g or spin >= self.threshold_dps:
            self.quiet_since = None
        else:
            if self.quiet_since is None:
                self.quiet_since = now

        if not self.armed and self.quiet_since is not None and now - self.quiet_since >= self.hold_seconds:
            self.armed = True

        if self.armed and delta >= self.threshold_g:
            self.vector = tuple(value / delta for value in change)
            intensity = delta / self.threshold_g
            self.strength = min(1.0, max(0.0, (intensity - 1.0) / 3.0))
            self.armed = False
        return self.active(now)

    def active(self, now):
        return not self.armed


class MotionSensor:
    def __init__(self, device='/dev/i2c-1', threshold_g=0.12):
        self.detector = MotionDetector(threshold_g=threshold_g)
        self.fd = os.open(device, os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, 0x0703, 0x6A)
            identity = self._read(0x0F, 1)[0]
            if identity not in (0x69, 0x6A):
                raise OSError(f'Unsupported motion sensor ID: 0x{identity:02x}')
            self._write(0x12, 0x44)  # BDU and register auto-increment, little endian.
            self._write(0x10, 0x40)  # Accelerometer: 104 Hz, ±2 g (0.061 mg/LSB).
            self._write(0x11, 0x40)  # Gyroscope: 104 Hz, ±245 dps (8.75 mdps/LSB).
            print(f'Motion sensor ready at 0x6a: ID=0x{identity:02x}, threshold={threshold_g} g', flush=True)
        except BaseException:
            os.close(self.fd)
            raise

    def _write(self, register, value):
        os.write(self.fd, bytes((register, value)))

    def _read(self, register, size):
        os.write(self.fd, bytes((register,)))
        return os.read(self.fd, size)

    def poll(self):
        now = time.monotonic()
        # Require fresh gyro and accelerometer data to confirm motion or quiet.
        if self._read(0x1E, 1)[0] & 3 != 3:
            self.detector.quiet_since = None
            return self.detector.active(now)
        gx, gy, gz, ax, ay, az = struct.unpack('<6h', self._read(0x22, 12))
        return self.detector.update(
            tuple(value * 0.000061 for value in (ax, ay, az)),
            tuple(value * 0.00875 for value in (gx, gy, gz)), now,
        )

    @property
    def strength(self):
        return self.detector.strength

    @property
    def vector(self):
        return self.detector.vector

    def close(self):
        try:
            self._write(0x10, 0)
            self._write(0x11, 0)
        finally:
            os.close(self.fd)
