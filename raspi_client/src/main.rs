mod camera;
mod indicator;
mod motion;
mod sensors;
mod settings;

use anyhow::{Context, Result, bail};
use client_core::{Options, archive};
use std::{
    path::PathBuf,
    sync::{Arc, atomic::AtomicBool},
};

fn run() -> Result<()> {
    let settings = settings::Settings::load()?;
    let mut options = Options {
        url: settings.url.clone(),
        config: settings.config.clone(),
        fullscreen: !settings.windowed,
        fit_display: true,
        ..Options::default()
    };
    let mut args = std::env::args().skip(1);
    let mode = args.next();
    if mode
        .as_deref()
        .is_some_and(|mode| ["-h", "--help"].contains(&mode))
    {
        println!(
            "Hexapods Raspberry Pi Rust viewer\n\nUsage: raspi-client [collect|replay [--directory DIR] [--seconds N] [--windowed] [--record-only] [--url URL] [--config CONFIG.json] [--output-size N]]\n\nLive mode uses LENIA_* settings in .env; sensors, camera, and LED are enabled."
        );
        return Ok(());
    }
    match mode.as_deref() {
        None => {
            let inputs = sensors::Sensors::open(&settings)?;
            client_core::run(options, Some(Box::new(inputs)))
        }
        Some("collect" | "replay") => {
            let mut directory = PathBuf::from("recordings/default");
            let mut seconds = 30.0_f64;
            let mut output_size = 800_u32;
            let mut record_only = mode.as_deref() == Some("collect");
            while let Some(arg) = args.next() {
                match arg.as_str() {
                    "--windowed" => options.fullscreen = false,
                    "--record-only" => record_only = true,
                    "--directory" | "--seconds" | "--url" | "--config" | "--output-size" => {
                        let value = args
                            .next()
                            .with_context(|| format!("Missing value for {arg}"))?;
                        match arg.as_str() {
                            "--directory" => directory = value.into(),
                            "--seconds" => seconds = value.parse()?,
                            "--url" => options.url = value,
                            "--config" => options.config = Some(value.into()),
                            _ => output_size = value.parse()?,
                        }
                    }
                    _ => bail!("Unknown argument: {arg}"),
                }
            }
            if !(1..=1024).contains(&output_size) || !seconds.is_finite() || seconds <= 0.0 {
                bail!("Invalid output size or capture duration");
            }
            if record_only || !directory.join("manifest.json").exists() {
                let stop = Arc::new(AtomicBool::new(false));
                let signal_stop = Arc::clone(&stop);
                // The viewer installs its own handler; share it through the library.
                client_core::install_interrupt(signal_stop)?;
                let mut config =
                    client_core::config::load(&options.url, options.config.as_deref())?;
                config["output_size"] = output_size.into();
                archive::collect(&options.url, config, &directory, seconds, &stop)?;
            }
            if record_only {
                return Ok(());
            }
            options.replay = Some(directory);
            client_core::run(options, None)
        }
        Some(other) => bail!("Unknown mode: {other}; live mode is configured in .env"),
    }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("Error: {error:#}");
        std::process::exit(1);
    }
}
