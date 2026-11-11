import fcntl
import os
import time


class ProximitySensor:
    def __init__(self, device="/dev/i2c-1", threshold=30):
        if threshold < 2 or threshold > 2047:
            raise ValueError("Proximity threshold must be between 2 and 2047")
        self.threshold = threshold
        self.active = False
        self.value = 0
        self.confirmations = 0
        self.release_threshold = threshold // 2
        self.fd = os.open(device, os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, 0x0703, 0x23)  # I2C_SLAVE
            if self._read(0x86, 1) != b"\x92":
                raise OSError("LTR559 identification failed at address 0x23")
            self._write(0x81, 0)  # Standby while configuring proximity only.
            self._write(0x82, 0x1C)  # 30 kHz, 100% duty cycle, maximum 100 mA.
            self._write(0x83, 15)  # Maximum pulse count for sensitivity.
            self._write(0x84, 0)  # New measurement every 50 ms.
            self._write(0x81, 0x23)  # Active, with saturation indication.
            # Match the reference app: calibrate with the sensor unobstructed.
            baseline = 0
            for _ in range(20):
                time.sleep(0.05)
                low, high = self._read(0x8D, 2)
                if high & 0x80:
                    raise OSError("Proximity sensor saturated during calibration; clear the sensor")
                baseline = max(baseline, low | ((high & 7) << 8))
            self.threshold = max(threshold, baseline + 15)
            self.release_threshold = max(baseline + 7, self.threshold - 8)
            print(f"Proximity baseline={baseline}, trigger={self.threshold}, release={self.release_threshold}; keep sensor clear at startup", flush=True)
        except BaseException:
            os.close(self.fd)
            raise

    def _write(self, register, value):
        os.write(self.fd, bytes((register, value)))

    def _read(self, register, size):
        os.write(self.fd, bytes((register,)))
        return os.read(self.fd, size)

    def poll(self):
        # Return the new presence state only when a fresh reading changes it.
        if not self._read(0x8C, 1)[0] & 1:
            return None
        low, high = self._read(0x8D, 2)
        value = low | ((high & 7) << 8)
        self.value = 2047 if high & 0x80 else value
        # Saturation means a strong reflection; hysteresis avoids edge chatter.
        active = bool(high & 0x80) or value >= (self.release_threshold if self.active else self.threshold)
        if active == self.active:
            self.confirmations = 0
            return None
        self.confirmations += 1
        if self.confirmations < 2:
            return None
        self.confirmations = 0
        self.active = active
        print(f"Proximity: {value}, {'detected' if active else 'clear'}", flush=True)
        return active

    @property
    def strength(self):
        # Relative reflection above detection, reaching full speed at +300 counts.
        return min(1.0, max(0.0, (self.value - self.threshold) / 300)) if self.active else 0.0

    def close(self):
        try:
            self._write(0x81, 0)
        finally:
            os.close(self.fd)
