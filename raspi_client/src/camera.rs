use anyhow::{Context, Result, bail};
use serde_json::Value;
use std::{
    fs,
    io::{ErrorKind, Read, Write},
    os::fd::AsRawFd,
    process::{Child, ChildStdout, Command, Stdio},
    time::{Duration, Instant},
};

pub struct Proximity {
    threshold: f64,
    pub active: bool,
    height: f64,
    confirmations: u8,
}
impl Proximity {
    pub fn new(threshold: f64) -> Self {
        Self {
            threshold,
            active: false,
            height: 0.0,
            confirmations: 0,
        }
    }
    pub fn update(&mut self, height: f64) -> Result<()> {
        if !height.is_finite() || !(0.0..=1.0).contains(&height) {
            bail!("Invalid person height");
        }
        self.height = height;
        let near = height >= self.threshold * if self.active { 0.8 } else { 1.0 };
        if near == self.active {
            self.confirmations = 0;
        } else {
            self.confirmations += 1;
            if self.confirmations >= 3 {
                self.active = near;
                self.confirmations = 0;
            }
        }
        Ok(())
    }
    pub fn strength(&self) -> f64 {
        if self.active {
            ((self.height - self.threshold) / (1.0 - self.threshold)).clamp(0.0, 1.0)
        } else {
            0.0
        }
    }
}

pub fn person_height(tensor: &[f64]) -> Result<f64> {
    if tensor.len() < 7 || (tensor.len() - 1) % 6 != 0 {
        bail!("Unexpected SSD output tensor layout");
    }
    let capacity = (tensor.len() - 1) / 6;
    let count = tensor[tensor.len() - 1];
    if !count.is_finite() || count < 0.0 || count > capacity as f64 || count.fract() != 0.0 {
        bail!("Invalid SSD detection count");
    }
    Ok((0..count as usize)
        .filter_map(|i| {
            let [y0, x0, y1, x1, score, class] = [
                tensor[i],
                tensor[capacity + i],
                tensor[2 * capacity + i],
                tensor[3 * capacity + i],
                tensor[4 * capacity + i],
                tensor[5 * capacity + i],
            ];
            ([y0, x0, y1, x1, score, class].iter().all(|v| v.is_finite())
                && score >= 0.6
                && class == 0.0
                && y1 > y0
                && x1 > x0)
                .then(|| (y1.min(1.0) - y0.max(0.0)).max(0.0))
        })
        .fold(0.0, f64::max))
}

pub struct Camera {
    process: Child,
    stdout: ChildStdout,
    buffer: Vec<u8>,
    last_sample: Instant,
    received: bool,
    pub proximity: Proximity,
    _config: tempfile::NamedTempFile,
}
impl Camera {
    pub fn open(threshold: f64) -> Result<Self> {
        let source = "/usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json";
        let original: Value = serde_json::from_slice(&fs::read(source).context(
            "Install imx500-all/rpicam-apps-imx500-postprocess for native camera inference",
        )?)?;
        let mut stage = original["imx500_object_detection"].clone();
        let fields = stage
            .as_object_mut()
            .context("Missing IMX500 object detection stage")?;
        // Keep native firmware loading; Rust consumes the original SSD tensors.
        fields.remove("save_input_tensor");
        fields.remove("temporal_filter");
        let mut config = tempfile::NamedTempFile::new()?;
        config.write_all(&serde_json::to_vec(
            &serde_json::json!({"imx500_object_detection": stage}),
        )?)?;
        config.flush()?;
        let mut process = Command::new("rpicam-vid")
            .args([
                "--nopreview",
                "--timeout",
                "0",
                "--width",
                "640",
                "--height",
                "480",
                "--framerate",
                "26",
                "--codec",
                "yuv420",
                "--output",
                "/dev/null",
                "--metadata",
                "-",
                "--metadata-format",
                "txt",
                "--post-process-file",
            ])
            .arg(config.path())
            .stdout(Stdio::piped())
            .spawn()
            .context("Cannot start native rpicam-vid camera worker")?;
        let stdout = process
            .stdout
            .take()
            .context("Missing camera metadata output")?;
        let flags = unsafe { libc::fcntl(stdout.as_raw_fd(), libc::F_GETFL) };
        if flags < 0
            || unsafe { libc::fcntl(stdout.as_raw_fd(), libc::F_SETFL, flags | libc::O_NONBLOCK) }
                < 0
        {
            let error = std::io::Error::last_os_error();
            let _ = process.kill();
            let _ = process.wait();
            return Err(error.into());
        }
        Ok(Self {
            process,
            stdout,
            buffer: Vec::new(),
            last_sample: Instant::now(),
            received: false,
            proximity: Proximity::new(threshold),
            _config: config,
        })
    }
    pub fn poll(&mut self, now: Instant) -> Result<()> {
        if let Some(status) = self.process.try_wait()? {
            bail!("Native person camera exited: {status}");
        }
        let mut chunk = [0; 65536];
        loop {
            match self.stdout.read(&mut chunk) {
                Ok(0) => break,
                Ok(count) => self.buffer.extend_from_slice(&chunk[..count]),
                Err(error) if error.kind() == ErrorKind::WouldBlock => break,
                Err(error) if error.kind() == ErrorKind::Interrupted => continue,
                Err(error) => return Err(error.into()),
            }
            if self.buffer.len() > 1024 * 1024 {
                bail!("Camera metadata exceeded buffer limit");
            }
        }
        while let Some(end) = self.buffer.iter().position(|byte| *byte == b'\n') {
            let line = std::str::from_utf8(&self.buffer[..end])?;
            if let Some(values) = line.strip_prefix("CnnOutputTensor=") {
                let values = values
                    .trim()
                    .strip_prefix('[')
                    .and_then(|s| s.strip_suffix(']'))
                    .context("Malformed camera tensor metadata")?;
                let tensor = values
                    .split(',')
                    .map(|s| s.trim().parse::<f64>().map_err(anyhow::Error::from))
                    .collect::<Result<Vec<_>>>()?;
                self.proximity.update(person_height(&tensor)?)?;
                self.last_sample = now;
                self.received = true;
            }
            self.buffer.drain(..=end);
        }
        let timeout = if self.received { 5 } else { 180 };
        if now.duration_since(self.last_sample) > Duration::from_secs(timeout) {
            bail!("Person camera inference timed out");
        }
        Ok(())
    }
}
impl Drop for Camera {
    fn drop(&mut self) {
        let _ = self.process.kill();
        let _ = self.process.wait();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn ssd_planar_tensor_and_proximity_hysteresis() {
        assert_eq!(
            person_height(&[0.1, 0.0, 0.9, 1.0, 0.9, 0.0, 1.0]).unwrap(),
            0.8
        );
        assert_eq!(
            person_height(&[0.1, 0.0, 0.9, 1.0, 0.59, 0.0, 1.0]).unwrap(),
            0.0
        );
        assert!(person_height(&[0.0]).is_err());
        let mut p = Proximity::new(0.5);
        for _ in 0..3 {
            p.update(0.6).unwrap();
        }
        assert!(p.active);
        p.update(0.41).unwrap();
        assert!(p.active);
        for _ in 0..3 {
            p.update(0.39).unwrap();
        }
        assert!(!p.active);
    }
}
