use anyhow::{Context, Result, bail};
use serde_json::Value;
use std::{
    io::ErrorKind,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{Receiver, SyncSender},
    },
    time::{Duration, Instant},
};
use tungstenite::{Bytes, Message, Utf8Bytes, stream::MaybeTlsStream};

#[derive(Debug)]
pub enum StreamEvent {
    Started { size: u32, fps: u32 },
    Frame(Bytes),
    Population(f64),
    Error(String),
    Stopped,
}

pub fn run(
    address: &str,
    config: Value,
    events: &SyncSender<StreamEvent>,
    commands: Receiver<Utf8Bytes>,
    stop: Arc<AtomicBool>,
) -> Result<()> {
    let limits = tungstenite::protocol::WebSocketConfig::default()
        .max_message_size(Some(4 * 1024 * 1024))
        .max_frame_size(Some(4 * 1024 * 1024));
    let (mut socket, _) = tungstenite::client::connect_with_config(address, Some(limits), 3)
        .context("Cannot connect to WebSocket server")?;
    let tcp = match socket.get_mut() {
        MaybeTlsStream::Plain(tcp) => tcp,
        MaybeTlsStream::Rustls(tls) => tls.get_mut(),
        _ => bail!("Unsupported WebSocket transport"),
    };
    tcp.set_nodelay(true)?;
    tcp.set_read_timeout(Some(Duration::from_millis(100)))?;
    tcp.set_write_timeout(Some(Duration::from_secs(30)))?;
    socket.send(Message::Text(serde_json::to_string(&config)?.into()))?;
    let mut started = false;
    let mut last_message = Instant::now();
    while !stop.load(Ordering::Relaxed) {
        for command in commands.try_iter() {
            socket.send(Message::Text(command))?;
        }
        let message = match socket.read() {
            Ok(message) => message,
            Err(tungstenite::Error::Io(error))
                if matches!(error.kind(), ErrorKind::WouldBlock | ErrorKind::TimedOut) =>
            {
                if last_message.elapsed() >= Duration::from_secs(60) {
                    bail!("Timed out waiting for a server frame");
                }
                continue;
            }
            Err(error) => return Err(error.into()),
        };
        last_message = Instant::now();
        match message {
            Message::Text(text) => {
                let status: Value = serde_json::from_str(&text).context("Invalid server status")?;
                if let Some(error) = status["error"].as_str() {
                    bail!("{error}");
                }
                match status["status"].as_str() {
                    Some("started") => {
                        let size = status["size"]
                            .as_u64()
                            .filter(|size| (1..=1024).contains(size));
                        let fps = status["fps"]
                            .as_u64()
                            .filter(|fps| (1..=u32::MAX as u64).contains(fps));
                        let (Some(size), Some(fps)) = (size, fps) else {
                            bail!("Invalid stream dimensions or FPS");
                        };
                        if started {
                            bail!("Server started the stream twice");
                        }
                        started = true;
                        events.send(StreamEvent::Started {
                            size: size as u32,
                            fps: fps as u32,
                        })?;
                        socket.send(Message::Text(Utf8Bytes::from_static("next")))?;
                    }
                    Some("population") => {
                        if let (Some(alive), Some(total)) =
                            (status["alive"].as_u64(), status["total"].as_u64())
                        {
                            if total > 0 && alive <= total {
                                events
                                    .send(StreamEvent::Population(alive as f64 / total as f64))?;
                            }
                        }
                    }
                    Some("stopped") => break,
                    _ => {}
                }
            }
            Message::Binary(jpeg) => {
                if !started {
                    bail!("Received frame before stream started");
                }
                socket.send(Message::Text(Utf8Bytes::from_static("next")))?;
                events.send(StreamEvent::Frame(jpeg))?;
            }
            Message::Ping(_) => socket.flush()?,
            Message::Close(_) => break,
            _ => {}
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{net::TcpListener, sync::mpsc, thread};

    #[test]
    fn streams_frames_and_requests_next_before_display() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = format!("ws://{}/ws", listener.local_addr().unwrap());
        let (requested, next_requested) = mpsc::channel();
        let server = thread::spawn(move || {
            let (tcp, _) = listener.accept().unwrap();
            tcp.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
            let mut socket = tungstenite::accept(tcp).unwrap();
            let config: Value =
                serde_json::from_str(socket.read().unwrap().to_text().unwrap()).unwrap();
            assert_eq!(config["action"], "start");
            socket
                .send(Message::Text(
                    r#"{"status":"started","size":4,"fps":240}"#.into(),
                ))
                .unwrap();
            assert_eq!(socket.read().unwrap().to_text().unwrap(), "outward");
            assert_eq!(socket.read().unwrap().to_text().unwrap(), "next");
            socket
                .send(Message::Text(
                    r#"{"status":"population","alive":2,"total":4}"#.into(),
                ))
                .unwrap();
            socket.send(Message::Binary(vec![1, 2, 3].into())).unwrap();
            assert_eq!(socket.read().unwrap().to_text().unwrap(), "next");
            requested.send(()).unwrap();
            socket
                .send(Message::Text(r#"{"status":"stopped"}"#.into()))
                .unwrap();
        });
        let (events_tx, events) = mpsc::sync_channel(2);
        let (commands, commands_rx) = mpsc::channel();
        commands.send(Utf8Bytes::from_static("outward")).unwrap();
        let network = thread::spawn(move || {
            run(
                &address,
                serde_json::json!({"action":"start"}),
                &events_tx,
                commands_rx,
                Arc::new(AtomicBool::new(false)),
            )
        });
        assert!(matches!(
            events.recv_timeout(Duration::from_secs(2)).unwrap(),
            StreamEvent::Started { size: 4, fps: 240 }
        ));
        next_requested.recv_timeout(Duration::from_secs(2)).unwrap();
        assert!(
            matches!(events.recv_timeout(Duration::from_secs(2)).unwrap(), StreamEvent::Population(fraction) if fraction == 0.5)
        );
        match events.recv_timeout(Duration::from_secs(2)).unwrap() {
            StreamEvent::Frame(jpeg) => assert_eq!(jpeg.as_ref(), [1, 2, 3]),
            event => panic!("Unexpected stream event: {event:?}"),
        }
        network.join().unwrap().unwrap();
        server.join().unwrap();
    }

    #[test]
    fn reports_server_errors() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = format!("ws://{}/ws", listener.local_addr().unwrap());
        let server = thread::spawn(move || {
            let (tcp, _) = listener.accept().unwrap();
            let mut socket = tungstenite::accept(tcp).unwrap();
            socket.read().unwrap();
            socket
                .send(Message::Text(r#"{"error":"bad configuration"}"#.into()))
                .unwrap();
        });
        let (events, _receiver) = mpsc::sync_channel(2);
        let (_commands, commands_rx) = mpsc::channel();
        let error = run(
            &address,
            serde_json::json!({}),
            &events,
            commands_rx,
            Arc::new(AtomicBool::new(false)),
        )
        .unwrap_err();
        assert!(error.to_string().contains("bad configuration"));
        server.join().unwrap();
    }
}
