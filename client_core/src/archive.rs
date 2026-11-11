use crate::stream::StreamEvent;
use anyhow::{Context, Result, bail};
use serde_json::{Value, json};
use std::{
    fs,
    io::ErrorKind,
    path::{Component, Path},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::SyncSender,
    },
    thread,
    time::{Duration, Instant},
};
use tungstenite::{Message, stream::MaybeTlsStream};

pub fn collect(
    address: &str,
    config: Value,
    directory: &Path,
    seconds: f64,
    stop: &AtomicBool,
) -> Result<()> {
    if !seconds.is_finite() || seconds <= 0.0 {
        bail!("Capture duration must be positive and finite");
    }
    fs::create_dir_all(directory)?;
    let staging = tempfile::Builder::new()
        .prefix(".capture-")
        .tempdir_in(directory)?;
    let (mut socket, _) = tungstenite::connect(address)?;
    let tcp = match socket.get_mut() {
        MaybeTlsStream::Plain(tcp) => tcp,
        MaybeTlsStream::Rustls(tls) => tls.get_mut(),
        _ => bail!("Unsupported WebSocket transport"),
    };
    tcp.set_nodelay(true)?;
    tcp.set_read_timeout(Some(Duration::from_millis(100)))?;
    tcp.set_write_timeout(Some(Duration::from_secs(30)))?;
    socket.send(Message::Text(config.to_string().into()))?;
    let mut fps = None;
    let mut frames = Vec::new();
    let mut last_message = Instant::now();
    loop {
        if stop.load(Ordering::Relaxed) {
            bail!("Capture interrupted; previous recording preserved");
        }
        let message = match socket.read() {
            Ok(message) => message,
            Err(tungstenite::Error::Io(error))
                if matches!(error.kind(), ErrorKind::TimedOut | ErrorKind::WouldBlock) =>
            {
                if last_message.elapsed() > Duration::from_secs(30) {
                    bail!("Capture timed out");
                }
                continue;
            }
            Err(error) => return Err(error.into()),
        };
        last_message = Instant::now();
        match message {
            Message::Text(text) => {
                let status: Value = serde_json::from_str(&text)?;
                if let Some(error) = status["error"].as_str() {
                    bail!("{error}");
                }
                match status["status"].as_str() {
                    Some("started") => {
                        if fps.is_some() {
                            bail!("Stream started twice");
                        }
                        let rate = status["fps"]
                            .as_u64()
                            .filter(|rate| (1..=u32::MAX as u64).contains(rate))
                            .context("Invalid recording FPS")?;
                        fps = Some(rate);
                        socket.send(Message::Text("next".into()))?;
                    }
                    Some("stopped") => bail!("Server stopped before capture completed"),
                    _ => {}
                }
            }
            Message::Binary(jpeg) => {
                let rate = fps.context("Frame before start status")?;
                let name = format!("{:06}.jpg", frames.len());
                fs::write(staging.path().join(&name), &jpeg)?;
                frames.push(name);
                if frames.len() as f64 >= (seconds * rate as f64).ceil() {
                    break;
                }
                socket.send(Message::Text("next".into()))?;
            }
            Message::Ping(_) => socket.flush()?,
            Message::Close(_) => bail!("Connection closed during capture"),
            _ => {}
        }
    }
    // Publish a new generation first, and switch its manifest last.
    let generation = staging.keep();
    let prefix = generation
        .file_name()
        .context("Missing generation directory")?;
    let frames: Vec<_> = frames
        .iter()
        .map(|name| Path::new(prefix).join(name).to_string_lossy().into_owned())
        .collect();
    let manifest = json!({"fps": fps, "frames": frames});
    let pending = directory.join("manifest.json.pending");
    fs::write(&pending, serde_json::to_vec(&manifest)?)?;
    fs::rename(pending, directory.join("manifest.json"))?;
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path != generation
            && path
                .file_name()
                .is_some_and(|name| name.to_string_lossy().starts_with(".capture-"))
            && path.is_dir()
        {
            fs::remove_dir_all(path)?;
        }
    }
    let _ = socket.close(None);
    println!("Saved {} frames to {}", frames.len(), directory.display());
    Ok(())
}

pub fn load(directory: &Path) -> Result<(u32, Vec<tungstenite::Bytes>)> {
    let manifest: Value = serde_json::from_slice(&fs::read(directory.join("manifest.json"))?)?;
    let fps = manifest["fps"]
        .as_f64()
        .filter(|rate| rate.is_finite() && *rate >= 1.0 && *rate <= u32::MAX as f64)
        .context("Invalid recording FPS")? as u32;
    let frames = manifest["frames"]
        .as_array()
        .filter(|frames| !frames.is_empty())
        .context("Recording has no frames")?;
    let images = frames
        .iter()
        .map(|frame| {
            let name = frame
                .as_str()
                .or_else(|| frame["file"].as_str())
                .context("Invalid frame filename")?;
            let path = Path::new(name);
            if path
                .components()
                .any(|part| !matches!(part, Component::Normal(_)))
            {
                bail!("Frame path must stay inside recording directory");
            }
            Ok(fs::read(directory.join(path))?.into())
        })
        .collect::<Result<Vec<_>>>()?;
    Ok((fps, images))
}

pub(crate) fn play(
    directory: &Path,
    events: &SyncSender<StreamEvent>,
    stop: &AtomicBool,
) -> Result<()> {
    let (fps, images) = load(directory)?;
    let mut decoder = turbojpeg::Decompressor::new()?;
    let header = decoder.read_header(&images[0])?;
    events.send(StreamEvent::Started {
        size: header.width as u32,
        fps,
    })?;
    let interval = Duration::from_secs_f64(1.0 / fps as f64);
    let mut deadline = Instant::now();
    for image in images.iter().cycle() {
        if stop.load(Ordering::Relaxed) {
            break;
        }
        events.send(StreamEvent::Frame(image.clone()))?;
        deadline += interval;
        while Instant::now() < deadline && !stop.load(Ordering::Relaxed) {
            thread::sleep(
                deadline
                    .saturating_duration_since(Instant::now())
                    .min(Duration::from_millis(10)),
            );
        }
        deadline = deadline.max(Instant::now());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{net::TcpListener, sync::Arc};

    #[test]
    fn capture_publishes_manifest_and_failure_preserves_previous() {
        let directory = tempfile::tempdir().unwrap();
        fs::write(
            directory.path().join("manifest.json"),
            br#"{"fps":30,"frames":["old.jpg"]}"#,
        )
        .unwrap();
        fs::write(directory.path().join("old.jpg"), [7, 8, 9]).unwrap();
        let stopped = AtomicBool::new(true);
        assert!(collect("ws://invalid", json!({}), directory.path(), 0.0, &stopped).is_err());
        assert_eq!(load(directory.path()).unwrap().1[0].as_ref(), [7, 8, 9]);
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = format!("ws://{}/ws", listener.local_addr().unwrap());
        let server = thread::spawn(move || {
            let (tcp, _) = listener.accept().unwrap();
            tcp.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
            let mut socket = tungstenite::accept(tcp).unwrap();
            socket.read().unwrap();
            socket
                .send(Message::Text(r#"{"status":"started","fps":2}"#.into()))
                .unwrap();
            for _ in 0..2 {
                assert_eq!(socket.read().unwrap().to_text().unwrap(), "next");
                socket.send(Message::Binary(vec![1, 2, 3].into())).unwrap();
            }
        });
        collect(
            &address,
            json!({"action":"start"}),
            directory.path(),
            1.0,
            &AtomicBool::new(false),
        )
        .unwrap();
        let (fps, images) = load(directory.path()).unwrap();
        assert_eq!(fps, 2);
        assert_eq!(images.len(), 2);
        assert_eq!(images[0].as_ref(), [1, 2, 3]);
        server.join().unwrap();
        let (events, _receiver) = std::sync::mpsc::sync_channel(2);
        assert!(play(directory.path(), &events, &Arc::new(AtomicBool::new(true))).is_err());
    }

    #[test]
    fn rejects_path_traversal_and_empty_recordings() {
        let directory = tempfile::tempdir().unwrap();
        for frames in [
            json!(["../outside.jpg"]),
            json!([]),
            json!(["/tmp/outside.jpg"]),
        ] {
            fs::write(
                directory.path().join("manifest.json"),
                json!({"fps":60,"frames":frames}).to_string(),
            )
            .unwrap();
            assert!(load(directory.path()).is_err());
        }
    }
}
