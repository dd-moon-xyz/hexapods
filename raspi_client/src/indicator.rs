use anyhow::{Context, Result, bail};
use std::{
    fs,
    io::ErrorKind,
    path::{Path, PathBuf},
    process::Command,
    thread,
    time::Duration,
};

const PERIOD: u32 = 500_000;
pub struct Indicator {
    channel: PathBuf,
    duty: u32,
}
impl Indicator {
    pub fn open() -> Result<Self> {
        let chips = fs::read_dir("/sys/class/pwm")?
            .filter_map(|entry| entry.ok())
            .map(|entry| entry.path())
            .filter(|path| {
                path.file_name()
                    .is_some_and(|name| name.to_string_lossy().starts_with("pwmchip"))
                    && fs::canonicalize(path)
                        .ok()
                        .and_then(|path| {
                            path.parent()?
                                .parent()?
                                .file_name()
                                .map(|name| name == "1f00098000.pwm")
                        })
                        .unwrap_or(false)
            })
            .collect::<Vec<_>>();
        if chips.len() != 1 {
            bail!("RP1 PWM0 controller unavailable; see wiki/wiring/indicator-led.md");
        }
        let chip = &chips[0];
        let channel = chip.join("pwm2");
        if !channel.exists() {
            match fs::write(chip.join("export"), "2") {
                Ok(()) => {}
                Err(error) if error.raw_os_error() == Some(libc::EBUSY) => {}
                Err(error) => return Err(error.into()),
            }
        }
        let mut light = Self { channel, duty: 0 };
        for attempt in 0..40 {
            match write(&light.channel, "duty_cycle", 0) {
                Ok(()) => break,
                Err(error)
                    if matches!(
                        error.kind(),
                        ErrorKind::NotFound | ErrorKind::PermissionDenied
                    ) && attempt < 39 =>
                {
                    thread::sleep(Duration::from_millis(25))
                }
                Err(error) => return Err(error.into()),
            }
        }
        write(&light.channel, "enable", 0)?;
        write(&light.channel, "period", PERIOD)?;
        fs::write(light.channel.join("polarity"), "normal")?;
        if !Command::new("/usr/bin/pinctrl")
            .args(["set", "18", "a3"])
            .status()
            .context("Cannot configure GPIO18 PWM pin")?
            .success()
        {
            bail!("pinctrl failed");
        }
        write(&light.channel, "enable", 1)?;
        light.update(1.0)?;
        Ok(light)
    }
    pub fn update(&mut self, fraction: f64) -> Result<()> {
        let duty = (fraction.clamp(0.0, 1.0) * 0.25 * PERIOD as f64).round_ties_even() as u32;
        if duty != self.duty {
            write(&self.channel, "duty_cycle", duty)?;
            self.duty = duty;
        }
        Ok(())
    }
}
fn write(path: &Path, field: &str, value: u32) -> std::io::Result<()> {
    fs::write(path.join(field), value.to_string())
}
impl Drop for Indicator {
    fn drop(&mut self) {
        let _ = write(&self.channel, "duty_cycle", 0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn brightness_tracks_population_and_shutdown_sets_zero() {
        let directory = tempfile::tempdir().unwrap();
        let mut indicator = Indicator {
            channel: directory.path().into(),
            duty: 0,
        };
        indicator.update(0.5).unwrap();
        assert_eq!(
            fs::read_to_string(directory.path().join("duty_cycle")).unwrap(),
            "62500"
        );
        drop(indicator);
        assert_eq!(
            fs::read_to_string(directory.path().join("duty_cycle")).unwrap(),
            "0"
        );
    }
}
