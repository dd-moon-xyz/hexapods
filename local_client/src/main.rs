mod controls;

use anyhow::{Context, Result, bail};
use client_core::{Options, config};
use controls::Controls;
use sdl3::event::{Event, WindowEvent};

#[derive(Default)]
struct Keyboard {
    controls: Controls,
}

impl client_core::Inputs for Keyboard {
    fn event(&mut self, event: &Event) -> Option<&'static str> {
        match *event {
            Event::KeyDown {
                keycode: Some(key),
                repeat: false,
                ..
            } => self.controls.key(key, true),
            Event::KeyUp {
                keycode: Some(key), ..
            } => self.controls.key(key, false),
            Event::Window {
                win_event: WindowEvent::FocusLost,
                ..
            } => Some(self.controls.focus_lost()),
            _ => None,
        }
    }
    fn caption(&self) -> &'static str {
        "Hexapod stream — Hold Space/C outward, V inward, Esc to quit"
    }
}

fn parse(mut args: impl Iterator<Item = String>) -> Result<Option<Options>> {
    let mut options = Options {
        url: config::DEFAULT_URL.to_owned(),
        config: None,
        record: None,
        ..Options::default()
    };
    while let Some(option) = args.next() {
        match option.as_str() {
            "-h" | "--help" => {
                println!(
                    "Hexapods Rust + SDL viewer\n\nUsage: local-client [--url URL] [--config CONFIG.json] [--record CAPTURE.mp4]"
                );
                return Ok(None);
            }
            "--url" | "--config" | "--record" => {
                let value = args
                    .next()
                    .with_context(|| format!("Missing value for {option}"))?;
                match option.as_str() {
                    "--url" => options.url = value,
                    "--config" => options.config = Some(value.into()),
                    _ => options.record = Some(value.into()),
                }
            }
            _ => bail!("Unknown option: {option}"),
        }
    }
    Ok(Some(options))
}

fn main() {
    let result = parse(std::env::args().skip(1)).and_then(|options| {
        options.map_or(Ok(()), |options| {
            client_core::run(options, Some(Box::new(Keyboard::default())))
        })
    });
    if let Err(error) = result {
        eprintln!("Error: {error:#}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn default_and_explicit_cli_options() {
        let defaults = parse(std::iter::empty()).unwrap().unwrap();
        assert_eq!(defaults.url, config::DEFAULT_URL);
        assert!(defaults.config.is_none() && defaults.record.is_none());
        let options = parse(
            [
                "--url",
                "ws://remote:9876/ws",
                "--config",
                "config.json",
                "--record",
                "capture.mp4",
            ]
            .into_iter()
            .map(str::to_owned),
        )
        .unwrap()
        .unwrap();
        assert_eq!(options.url, "ws://remote:9876/ws");
        assert_eq!(options.config.unwrap(), PathBuf::from("config.json"));
        assert_eq!(options.record.unwrap(), PathBuf::from("capture.mp4"));
        assert!(parse(["--url".to_owned()].into_iter()).is_err());
        assert!(parse(["--unknown".to_owned()].into_iter()).is_err());
    }
}
