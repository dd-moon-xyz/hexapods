use crate::{
    camera::Camera,
    indicator::Indicator,
    motion::{Detector, Motion},
    settings::Settings,
};
use anyhow::Result;
use serde_json::{Value, json};
use std::time::{Duration, Instant};

pub fn steering(
    proximity: bool,
    proximity_strength: f64,
    motion: &Detector,
    axes: &[String; 2],
) -> Value {
    let active = motion.active && !proximity;
    let strength = if proximity {
        proximity_strength
    } else if active {
        motion.strength
    } else {
        0.0
    };
    let speed = round(1.0 + strength.clamp(0.0, 1.0));
    if active && motion.vector[0].hypot(motion.vector[1]) > 0.0 {
        let mapped = axes.each_ref().map(|axis| {
            motion.vector[usize::from(axis.ends_with('y'))]
                * if axis.starts_with('-') { -1.0 } else { 1.0 }
        });
        let length = mapped[0].hypot(mapped[1]);
        return json!({"action":"movement","direction":"vector","vector":{"x":round(mapped[0]/length),"y":round(mapped[1]/length)},"escape":true,"speed_multiplier":speed});
    }
    json!({"action":"movement","direction":if proximity||active {"outward"} else {"inward"},"speed_multiplier":speed})
}
fn round(value: f64) -> f64 {
    (value * 100.0).round_ties_even() / 100.0
}

pub struct Sensors {
    camera: Camera,
    motion: Motion,
    indicator: Indicator,
    axes: [String; 2],
    next: Instant,
    previous: Option<Value>,
}
impl Sensors {
    pub fn open(settings: &Settings) -> Result<Self> {
        Ok(Self {
            camera: Camera::open(settings.proximity)?,
            motion: Motion::open(&settings.device, settings.threshold)?,
            indicator: Indicator::open()?,
            axes: settings.axes.clone(),
            next: Instant::now(),
            previous: None,
        })
    }
}
impl client_core::Inputs for Sensors {
    fn poll(&mut self) -> Result<Option<String>> {
        let now = Instant::now();
        if now < self.next {
            return Ok(None);
        }
        self.next = now + Duration::from_millis(50);
        self.camera.poll(now)?;
        self.motion.poll(now)?;
        let command = steering(
            self.camera.proximity.active,
            self.camera.proximity.strength(),
            &self.motion.detector,
            &self.axes,
        );
        if self.previous.as_ref() == Some(&command) {
            return Ok(None);
        }
        println!("Sensor steering: {command}");
        self.previous = Some(command.clone());
        Ok(Some(command.to_string()))
    }
    fn population(&mut self, fraction: f64) -> Result<()> {
        self.indicator.update(fraction)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn camera_has_priority_and_motion_axes_map() {
        let mut motion = Detector::new(0.12);
        motion.active = true;
        motion.vector = [1.0, 0.0];
        motion.strength = 0.5;
        let axes = ["y".into(), "-x".into()];
        let command = steering(false, 0.0, &motion, &axes);
        assert_eq!(command["vector"]["y"], -1.0);
        assert_eq!(command["speed_multiplier"], 1.5);
        assert_eq!(steering(true, 0.8, &motion, &axes)["direction"], "outward");
        motion.active = false;
        assert_eq!(steering(false, 0.0, &motion, &axes)["direction"], "inward");
    }
}
