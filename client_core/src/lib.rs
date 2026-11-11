pub mod archive;
pub mod config;
mod recording;
mod stream;

use anyhow::{Context, Result, bail};
use recording::Recording;
use sdl3::{
    event::Event,
    keyboard::Keycode,
    pixels::PixelFormat,
    render::{BlendMode, ScaleMode},
};
use std::{
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, RecvTimeoutError},
    },
    thread,
    time::{Duration, Instant},
};
use stream::StreamEvent;

pub trait Inputs {
    fn poll(&mut self) -> Result<Option<String>> {
        Ok(None)
    }
    fn population(&mut self, _fraction: f64) -> Result<()> {
        Ok(())
    }
    fn event(&mut self, _event: &Event) -> Option<&'static str> {
        None
    }
    fn caption(&self) -> &'static str {
        "Hexapod stream"
    }
}

#[derive(Default)]
pub struct Options {
    pub url: String,
    pub config: Option<PathBuf>,
    pub record: Option<PathBuf>,
    pub fullscreen: bool,
    pub fit_display: bool,
    pub replay: Option<PathBuf>,
}

pub fn install_interrupt(stop: Arc<AtomicBool>) -> Result<()> {
    static TARGET: std::sync::OnceLock<std::sync::Mutex<Arc<AtomicBool>>> =
        std::sync::OnceLock::new();
    if let Some(target) = TARGET.get() {
        *target
            .lock()
            .map_err(|_| anyhow::anyhow!("Signal lock poisoned"))? = stop;
        return Ok(());
    }
    TARGET
        .set(std::sync::Mutex::new(stop))
        .map_err(|_| anyhow::anyhow!("Signal handler already initialized"))?;
    ctrlc::set_handler(|| {
        if let Some(target) = TARGET.get() {
            if let Ok(stop) = target.lock() {
                stop.store(true, Ordering::Relaxed);
            }
        }
    })?;
    Ok(())
}

pub fn run(options: Options, mut inputs: Option<Box<dyn Inputs>>) -> Result<()> {
    let mut config = if options.replay.is_none() {
        config::load(&options.url, options.config.as_deref())?
    } else {
        serde_json::json!({})
    };
    if inputs.is_some() {
        config["population_updates"] = true.into();
    }
    let stop = Arc::new(AtomicBool::new(false));
    install_interrupt(Arc::clone(&stop))?;
    let sdl = sdl3::init().map_err(anyhow::Error::msg)?;
    let video = sdl.video().map_err(anyhow::Error::msg)?;
    let initial_size = if options.fit_display { 800 } else { 512 };
    let mut window = video
        .window("Hexapod stream — connecting…", initial_size, initial_size)
        .position_centered()
        .high_pixel_density()
        .build()?;
    if options.fullscreen {
        window.set_fullscreen(true).map_err(anyhow::Error::msg)?;
        sdl.mouse().show_cursor(false);
    }
    if options.fit_display {
        let (width, height) = window.size_in_pixels();
        config["output_size"] = width.min(height).clamp(1, 1024).into();
    }
    let mut canvas = window.into_canvas();
    let texture_creator = canvas.texture_creator();
    let mut texture = None;
    let mut texture_size = (0, 0);
    let mut decoder = turbojpeg::Decompressor::new()?;
    let mut events = sdl.event_pump().map_err(anyhow::Error::msg)?;
    let mut recording = None;
    let (frames_tx, frames) = mpsc::sync_channel(2);
    let (commands, commands_rx) = mpsc::channel();
    let network_stop = Arc::clone(&stop);
    thread::Builder::new()
        .name("hexapod-stream".into())
        .spawn(move || {
            let result = match options.replay {
                Some(directory) => archive::play(&directory, &frames_tx, &network_stop),
                None => stream::run(&options.url, config, &frames_tx, commands_rx, network_stop),
            };
            if let Err(error) = result {
                let _ = frames_tx.send(StreamEvent::Error(format!("{error:#}")));
            }
            let _ = frames_tx.send(StreamEvent::Stopped);
        })?;

    let result = (|| -> Result<()> {
        while !stop.load(Ordering::Relaxed) {
            if let Some(inputs) = inputs.as_mut() {
                if let Some(command) = inputs.poll()? {
                    commands
                        .send(command.into())
                        .context("Stream disconnected")?;
                }
            }
            for event in events.poll_iter() {
                let command = match event {
                    Event::Quit { .. }
                    | Event::KeyDown {
                        keycode: Some(Keycode::Escape),
                        ..
                    } => {
                        return Ok(());
                    }
                    _ => inputs.as_mut().and_then(|inputs| inputs.event(&event)),
                };
                if let Some(command) = command {
                    commands
                        .send(tungstenite::Utf8Bytes::from_static(command))
                        .context("Stream disconnected")?;
                }
            }
            match frames.recv_timeout(Duration::from_millis(5)) {
                Ok(StreamEvent::Started { size, fps }) => {
                    let density = canvas.window().pixel_density().max(1.0);
                    let window_size = (size as f32 / density).round().max(1.0) as u32;
                    if !options.fullscreen {
                        canvas.window_mut().set_size(window_size, window_size)?;
                    }
                    if options.fit_display {
                        canvas.set_logical_size(
                            size,
                            size,
                            sdl3::sys::render::SDL_RendererLogicalPresentation::LETTERBOX,
                        )?;
                    }
                    canvas.window_mut().set_title(
                        inputs
                            .as_ref()
                            .map_or("Hexapod stream", |inputs| inputs.caption()),
                    )?;
                    if let Some(path) = options.record.as_deref() {
                        recording = Some(Recording::start(path, fps)?);
                    }
                }
                Ok(StreamEvent::Frame(jpeg)) => {
                    let header = decoder.read_header(&jpeg).context("Invalid JPEG frame")?;
                    let (width, height) = (header.width, header.height);
                    if !(1..=1024).contains(&width) || !(1..=1024).contains(&height) {
                        bail!("Invalid JPEG dimensions: {width}x{height}");
                    }
                    if texture_size != (width, height) {
                        let mut next = texture_creator.create_texture_streaming(
                            PixelFormat::RGBA32,
                            width as u32,
                            height as u32,
                        )?;
                        next.set_scale_mode(ScaleMode::Nearest);
                        next.set_blend_mode(BlendMode::None);
                        texture = Some(next);
                        texture_size = (width, height);
                    }
                    let texture = texture.as_mut().context("Missing frame texture")?;
                    texture.with_lock(None, |pixels, pitch| {
                        decoder.decompress(
                            &jpeg,
                            turbojpeg::Image {
                                pixels,
                                width,
                                pitch,
                                height,
                                format: turbojpeg::PixelFormat::RGBA,
                            },
                        )
                    })??;
                    canvas
                        .copy(texture, None, None)
                        .map_err(anyhow::Error::msg)?;
                    canvas.present();
                    if let Some(recording) = recording.as_mut() {
                        recording
                            .video
                            .as_mut()
                            .context("Recording already closed")?
                            .write(jpeg, Instant::now())?;
                    }
                }
                Ok(StreamEvent::Population(fraction)) => {
                    if let Some(inputs) = inputs.as_mut() {
                        inputs.population(fraction)?;
                    }
                }
                Ok(StreamEvent::Error(error)) => bail!("{error}"),
                Ok(StreamEvent::Stopped) | Err(RecvTimeoutError::Disconnected) => break,
                Err(RecvTimeoutError::Timeout) => {}
            }
        }
        Ok(())
    })();
    stop.store(true, Ordering::Relaxed);
    let close_result = recording.map_or(Ok(()), Recording::finish);
    result.and(close_result)
}
