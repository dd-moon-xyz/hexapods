use anyhow::{Result, bail, ensure};
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Organism {
    pub scale: f64,
    pub x: u32,
    pub y: u32,
}

impl Default for Organism {
    fn default() -> Self {
        Self {
            scale: 1.0,
            x: 128,
            y: 128,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Start {
    pub action: String,
    pub simulation: String,
    pub boundary: String,
    pub size: u32,
    pub output_size: Option<u32>,
    pub fps: u32,
    pub pixel_size: u32,
    pub dt: f64,
    pub space_speed_multiplier: f64,
    pub population_updates: bool,
    pub preview: bool,
    pub scale_min: f64,
    pub scale_max: f64,
    pub birth_rate_min: f64,
    pub birth_rate_max: f64,
    pub interaction_count_min: u32,
    pub interaction_count_max: u32,
    pub organisms: Vec<Organism>,
}

impl Default for Start {
    fn default() -> Self {
        Self {
            action: String::new(),
            simulation: "hexapod".into(),
            boundary: "circle".into(),
            size: 512,
            output_size: None,
            fps: 60,
            pixel_size: 1,
            dt: 0.1,
            space_speed_multiplier: 2.0,
            population_updates: false,
            preview: false,
            scale_min: 1.0,
            scale_max: 1.1,
            birth_rate_min: 1.0,
            birth_rate_max: 5.0,
            interaction_count_min: 1,
            interaction_count_max: 10,
            organisms: Vec::new(),
        }
    }
}

impl Start {
    pub fn parse(text: &str) -> Result<Self> {
        let config: Self = serde_json::from_str(text)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<()> {
        ensure!(self.action == "start", "Expected action 'start'");
        ensure!(
            self.simulation == "hexapod" && self.boundary == "circle",
            "Only hexapods in a circular arena are supported"
        );
        ensure!(
            (256..=1024).contains(&self.size),
            "World size must be 256–1024"
        );
        ensure!(
            self.output_size
                .is_none_or(|size| (1..=1024).contains(&size)),
            "Output size must be 1–1024"
        );
        ensure!(self.fps > 0, "Recording FPS must be positive");
        ensure!(
            (1..=16).contains(&self.pixel_size),
            "Pixel size must be 1–16"
        );
        ensure!(
            self.dt.is_finite() && self.dt > 0.0 && self.dt <= 0.2,
            "dt must be positive and at most 0.2"
        );
        ensure!(
            self.space_speed_multiplier.is_finite() && self.space_speed_multiplier >= 1.0,
            "Space speed multiplier must be at least 1"
        );
        ensure!(
            self.scale_min.is_finite()
                && self.scale_max.is_finite()
                && self.scale_min >= 1.0
                && self.scale_min <= self.scale_max
                && self.scale_max <= 10.0,
            "Scale bounds must be finite, ordered numbers between 1 and 10"
        );
        ensure!(
            self.birth_rate_min.is_finite()
                && self.birth_rate_min > 0.0
                && self.birth_rate_max.is_finite()
                && self.birth_rate_max >= self.birth_rate_min,
            "Birth rates must be positive, finite, and ordered"
        );
        ensure!(
            Duration::try_from_secs_f64(1.0 / self.birth_rate_min).is_ok(),
            "Birth interval is too large"
        );
        ensure!(
            self.interaction_count_min >= 1
                && self.interaction_count_min <= self.interaction_count_max
                && self.interaction_count_max <= i32::MAX as u32,
            "Interaction counts must be positive, ordered native integers"
        );
        ensure!(
            (1..=100).contains(&self.organisms.len()),
            "Provide 1–100 organisms"
        );
        ensure!(
            !self.preview || self.organisms.len() == 1,
            "Preview requires exactly one organism"
        );
        ensure!(
            self.organisms
                .iter()
                .all(|item| (1.0..=10.0).contains(&item.scale)
                    && item.x < self.size
                    && item.y < self.size),
            "Organism scales must be 1–10 and positions must be inside the world"
        );
        Ok(())
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Vector {
    x: f64,
    y: f64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Movement {
    action: String,
    direction: String,
    speed_multiplier: f64,
    vector: Option<Vector>,
    escape: Option<bool>,
}

pub fn movement_command(text: &str) -> Result<(String, bool)> {
    let value: serde_json::Value = serde_json::from_str(text)?;
    let movement: Movement = serde_json::from_value(value.clone())?;
    ensure!(movement.action == "movement", "Expected action 'movement'");
    let speed = movement.speed_multiplier;
    ensure!(
        speed.is_finite() && speed > 0.0 && speed <= 10.0,
        "Movement speed must be positive and at most 10"
    );
    match movement.direction.as_str() {
        "vector" => {
            let Some(vector) = movement.vector else {
                bail!("Vector movement requires a vector")
            };
            let Some(escape) = movement.escape else {
                bail!("Vector movement requires an escape flag")
            };
            ensure!(
                vector.x.is_finite()
                    && vector.y.is_finite()
                    && vector.x.abs() <= 1.0
                    && vector.y.abs() <= 1.0
                    && (vector.x != 0.0 || vector.y != 0.0),
                "Invalid movement vector"
            );
            Ok((
                format!("v {} {} {} {speed}\n", vector.x, vector.y, u8::from(escape)),
                escape,
            ))
        }
        "inward" | "outward" => {
            ensure!(
                value.get("vector").is_none() && value.get("escape").is_none(),
                "Radial movement cannot include vector or escape fields"
            );
            let outward = movement.direction == "outward";
            Ok((format!("m {} {speed}\n", u8::from(outward)), outward))
        }
        _ => bail!("Unknown movement direction"),
    }
}

pub fn preset() -> Start {
    let organisms = (0..50)
        .map(|_| {
            let angle = rand::random::<f64>() * std::f64::consts::TAU;
            let radius = 400.0 * rand::random::<f64>().sqrt();
            Organism {
                scale: 1.0,
                x: (512.0 + radius * angle.cos()).round() as u32,
                y: (512.0 + radius * angle.sin()).round() as u32,
            }
        })
        .collect();
    Start {
        action: "start".into(),
        size: 1024,
        organisms,
        ..Start::default()
    }
}
