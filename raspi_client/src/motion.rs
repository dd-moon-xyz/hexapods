use anyhow::{Result, bail};
use std::{
    fs::{File, OpenOptions},
    io::{Read, Write},
    os::fd::AsRawFd,
    time::{Duration, Instant},
};

pub struct Detector {
    threshold: f64,
    previous: Option<[f64; 2]>,
    quiet: Option<Instant>,
    pub active: bool,
    pub strength: f64,
    pub vector: [f64; 2],
}
impl Detector {
    pub fn new(threshold: f64) -> Self {
        Self {
            threshold,
            previous: None,
            quiet: None,
            active: false,
            strength: 0.0,
            vector: [0.0; 2],
        }
    }
    pub fn update(&mut self, acceleration: [f64; 2], rotation: [f64; 2], now: Instant) {
        let previous = self.previous.replace(acceleration).unwrap_or(acceleration);
        let change = [acceleration[0] - previous[0], acceleration[1] - previous[1]];
        let delta = change[0].hypot(change[1]);
        if delta >= self.threshold || rotation[0].hypot(rotation[1]) >= 20.0 {
            self.quiet = None;
        } else {
            self.quiet.get_or_insert(now);
        }
        if self.active
            && self
                .quiet
                .is_some_and(|quiet| now.duration_since(quiet) >= Duration::from_millis(250))
        {
            self.active = false;
        }
        if !self.active && delta >= self.threshold {
            self.vector = [change[0] / delta, change[1] / delta];
            self.strength = ((delta / self.threshold - 1.0) / 3.0).clamp(0.0, 1.0);
            self.active = true;
        }
    }
}
pub struct Motion {
    file: File,
    pub detector: Detector,
}
impl Motion {
    pub fn open(device: &str, threshold: f64) -> Result<Self> {
        let file = OpenOptions::new().read(true).write(true).open(device)?;
        // Linux i2c-dev I2C_SLAVE takes the address as an integer argument.
        if unsafe { libc::ioctl(file.as_raw_fd(), 0x0703, 0x6a as libc::c_ulong) } < 0 {
            return Err(std::io::Error::last_os_error().into());
        }
        let mut sensor = Self {
            file,
            detector: Detector::new(threshold),
        };
        if ![0x69, 0x6a].contains(&sensor.read::<1>(0x0f)?[0]) {
            bail!("Unsupported motion sensor at 0x6a");
        }
        for (register, value) in [(0x12, 0x44), (0x10, 0x40), (0x11, 0x40)] {
            sensor.write(register, value)?;
        }
        Ok(sensor)
    }
    fn write(&mut self, register: u8, value: u8) -> Result<()> {
        self.file.write_all(&[register, value])?;
        Ok(())
    }
    fn read<const N: usize>(&mut self, register: u8) -> Result<[u8; N]> {
        self.file.write_all(&[register])?;
        let mut data = [0; N];
        self.file.read_exact(&mut data)?;
        Ok(data)
    }
    pub fn poll(&mut self, now: Instant) -> Result<()> {
        if self.read::<1>(0x1e)?[0] & 3 != 3 {
            self.detector.quiet = None;
            return Ok(());
        }
        let raw = self.read::<12>(0x22)?;
        let values: Vec<_> = raw
            .chunks_exact(2)
            .map(|pair| i16::from_le_bytes([pair[0], pair[1]]) as f64)
            .collect();
        self.detector.update(
            [values[3] * 0.000061, values[4] * 0.000061],
            [values[0] * 0.00875, values[1] * 0.00875],
            now,
        );
        Ok(())
    }
}
impl Drop for Motion {
    fn drop(&mut self) {
        let _ = self.write(0x10, 0);
        let _ = self.write(0x11, 0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn latches_first_vector_until_fresh_quiet() {
        let mut d = Detector::new(0.12);
        let now = Instant::now();
        d.update([0.0, 0.0], [0.0, 0.0], now);
        d.update([0.24, 0.0], [0.0, 0.0], now);
        assert!(d.active);
        assert_eq!(d.vector, [1.0, 0.0]);
        d.update([0.24, 0.4], [0.0, 0.0], now);
        assert_eq!(d.vector, [1.0, 0.0]);
        d.update([0.24, 0.4], [0.0, 0.0], now);
        d.update([0.24, 0.4], [0.0, 0.0], now + Duration::from_millis(250));
        assert!(!d.active);
    }
}
