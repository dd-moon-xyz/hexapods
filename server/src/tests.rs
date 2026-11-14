use crate::{
    app,
    arena::Arena,
    frames::{Encoder, resize_box},
    models::{Start, movement_command, preset},
    worker::Worker,
};
use futures_util::{SinkExt, StreamExt};
use serde_json::{Value, json};
use std::{fs, os::unix::fs::PermissionsExt, path::PathBuf, sync::Arc, time::Duration};
use tempfile::TempDir;
use tokio::{
    net::TcpListener,
    sync::watch,
    time::{sleep, timeout},
};
use tokio_tungstenite::{connect_async, tungstenite::Message};

fn config() -> Start {
    Start::parse(r#"{"action":"start","size":256,"birth_rate_min":1000,"birth_rate_max":1000,"organisms":[{}]}"#).unwrap()
}

fn fixture(alive: bool) -> (TempDir, PathBuf) {
    let directory = tempfile::tempdir().unwrap();
    for size in [128, 256] {
        let raw: Vec<u8> = [
            [255, 0, 0].repeat(size * size / 2),
            [0, 0, 255].repeat(size * size / 2),
        ]
        .concat();
        for (name, mass) in [("dead", 0.0_f32), ("alive", 1.0_f32)] {
            let mut frame = mass.to_ne_bytes().to_vec();
            frame.extend_from_slice(&raw);
            fs::write(directory.path().join(format!("{name}-{size}.rgb")), frame).unwrap();
        }
    }
    let path = directory.path().join("worker.sh");
    let state = if alive { "alive" } else { "dead" };
    let script = format!(
        r#"#!/bin/sh
cd '{}'
printf '%s\n' "$1" > mode
echo $$ > pid
IFS= read -r header
printf '%s\n' "$header" >> commands
IFS= read -r organism
size=256
state={state}
printf 'READY\n'
while IFS= read -r command; do
    printf '%s\n' "$command" >> commands
    case "$command" in
        n) cat "$state-$size.rgb" ;;
        's 128') size=128; printf 'READY\n' ;;
        r*) state=alive; printf 'READY\n' ;;
        *) printf 'READY\n' ;;
    esac
done
"#,
        directory.path().display()
    );
    fs::write(&path, script).unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).unwrap();
    (directory, path)
}

#[test]
fn validates_configuration_without_fps_cap() {
    for fps in [1, 60, 240, 10000] {
        let mut value = serde_json::to_value(config()).unwrap();
        value["fps"] = json!(fps);
        assert_eq!(Start::parse(&value.to_string()).unwrap().fps, fps);
    }
    for update in [
        json!({"fps":0}),
        json!({"scale_min":0}),
        json!({"scale_min":3,"scale_max":2}),
        json!({"scale_max":11}),
        json!({"scale_min":1.6,"scale_max":1.5}),
        json!({"size":255}),
        json!({"size":1025}),
        json!({"birth_rate_min":5,"birth_rate_max":1}),
        json!({"interaction_count_min":10,"interaction_count_max":1}),
        json!({"organisms":[{"scale":0}]}),
        json!({"organisms":[{"x":256}]}),
        json!({"organisms":[]}),
        json!({"dt":0}),
        json!({"unknown":true}),
        json!({"population_updates":1}),
    ] {
        let mut value = serde_json::to_value(config()).unwrap();
        value
            .as_object_mut()
            .unwrap()
            .extend(update.as_object().unwrap().clone());
        assert!(
            Start::parse(&value.to_string()).is_err(),
            "accepted {update}"
        );
    }
    assert!(Start::parse(r#"{"organisms":[{}]}"#).is_err());
    preset().validate().unwrap();
    assert_eq!((preset().scale_min, preset().scale_max), (1.0, 1.1));
}

#[test]
fn preview_requires_one_organism() {
    let mut value = serde_json::to_value(config()).unwrap();
    value["preview"] = json!(true);
    assert!(Start::parse(&value.to_string()).unwrap().preview);
    value["organisms"] = json!([{}, {}]);
    assert!(Start::parse(&value.to_string()).is_err());
}

#[tokio::test]
async fn preview_selects_native_mode_and_never_schedules_births() {
    let (directory, path) = fixture(false);
    let mut config = config();
    config.preview = true;
    let mut arena = Arena::start(&path, config).await.unwrap();
    for _ in 0..8 {
        arena.frame().await.unwrap().await.unwrap().unwrap();
    }
    sleep(Duration::from_millis(20)).await;
    arena.frame().await.unwrap().await.unwrap().unwrap();
    arena.close().await.unwrap();
    assert_eq!(
        fs::read_to_string(directory.path().join("mode")).unwrap(),
        "--stream-hexapod-preview\n"
    );
    let commands = fs::read_to_string(directory.path().join("commands")).unwrap();
    assert!(!commands.lines().any(|line| line.starts_with("r ")));
}

#[test]
fn validates_vector_and_radial_commands() {
    let (command, escape) = movement_command(r#"{"action":"movement","direction":"vector","vector":{"x":0.6,"y":-0.8},"escape":true,"speed_multiplier":2}"#).unwrap();
    assert_eq!(command, "v 0.6 -0.8 1 2\n");
    assert!(escape);
    assert!(
        movement_command(
            r#"{"action":"movement","direction":"inward","vector":null,"speed_multiplier":1}"#
        )
        .is_err()
    );
    assert!(movement_command(r#"{"action":"movement","direction":"vector","vector":{"x":0,"y":0},"escape":false,"speed_multiplier":1}"#).is_err());
    assert!(movement_command(r#"{"action":"movement","direction":"vector","vector":{"x":1,"y":0},"speed_multiplier":1}"#).is_err());
}

#[test]
fn flips_bottom_up_rgb_and_preserves_output_dimensions() {
    for (pixel_size, output) in [(1, None), (3, Some(32)), (2, Some(80))] {
        let mut raw = [[255, 0, 0].repeat(64 * 32), [0, 0, 255].repeat(64 * 32)].concat();
        let jpeg = Encoder::new()
            .unwrap()
            .encode(&mut raw, 64, pixel_size, output)
            .unwrap();
        let image = turbojpeg::decompress(&jpeg, turbojpeg::PixelFormat::RGB).unwrap();
        let size = output.unwrap_or(64) as usize;
        assert_eq!((image.width, image.height), (size, size));
        assert!(image.pixels[(size / 8 * size + size / 2) * 3 + 2] > 240);
        assert!(image.pixels[(size * 7 / 8 * size + size / 2) * 3] > 240);
    }
    assert_eq!(
        resize_box(&[0, 0, 0, 20, 20, 20, 40, 40, 40, 60, 60, 60], 2, 1),
        vec![30, 30, 30]
    );
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn worker_reads_metadata_and_negotiates_gpu_resize() {
    let (directory, path) = fixture(true);
    let mut config = config();
    config.output_size = Some(128);
    config.fps = 240;
    let mut worker = Worker::start(&path, &config).await.unwrap();
    worker.frame().await.unwrap();
    assert_eq!(worker.size, 128);
    assert_eq!(worker.pixels.len(), 128 * 128 * 3);
    assert_eq!(worker.masses, [1.0]);
    worker.command("v 1 0 1 2\n").await.unwrap();
    worker.frame().await.unwrap();
    let commands = fs::read_to_string(directory.path().join("commands")).unwrap();
    assert!(commands.starts_with("256 60 "));
    assert!(commands.contains("s 128\n"));
    worker.close().await.unwrap();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn outward_gates_births_and_inward_resumes_them() {
    let (directory, path) = fixture(false);
    let mut start = config();
    start.scale_min = 1.25;
    start.scale_max = 1.25;
    let mut arena = Arena::start(&path, start).await.unwrap();
    arena.movement("o\n", true).await.unwrap();
    for _ in 0..8 {
        assert_eq!(arena.frame().await.unwrap().await.unwrap().unwrap().1, 0);
    }
    arena.movement("i\n", false).await.unwrap();
    arena.frame().await.unwrap().await.unwrap().unwrap();
    sleep(Duration::from_millis(20)).await;
    assert_eq!(arena.frame().await.unwrap().await.unwrap().unwrap().1, 1);
    let commands = fs::read_to_string(directory.path().join("commands")).unwrap();
    assert!(
        commands
            .lines()
            .any(|line| line.starts_with("r 0 1.25 128 128 "))
    );
    arena.close().await.unwrap();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn api_streams_population_movement_and_stop_without_pacing() {
    let (_directory, path) = fixture(true);
    let (shutdown, receiver) = watch::channel(false);
    let state = app::AppState {
        auth: crate::auth::Auth::load(true).unwrap(),
        worker: Arc::new(path),
        shutdown: receiver.clone(),
    };
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let address = listener.local_addr().unwrap();
    let server = tokio::spawn(async move {
        let mut receiver = receiver;
        axum::serve(listener, app::router(state))
            .with_graceful_shutdown(async move {
                let _ = receiver.changed().await;
            })
            .await
            .unwrap();
    });
    let (mut socket, _) = connect_async(format!("ws://{address}/ws")).await.unwrap();
    let mut config = config();
    config.fps = 240;
    config.population_updates = true;
    socket
        .send(Message::Text(
            serde_json::to_string(&config).unwrap().into(),
        ))
        .await
        .unwrap();
    let started = timeout(Duration::from_secs(2), socket.next())
        .await
        .unwrap()
        .unwrap()
        .unwrap();
    let started: Value = serde_json::from_str(started.to_text().unwrap()).unwrap();
    assert_eq!(started["fps"], 240);
    assert!(started["fps_limit"].is_null());
    for command in ["outward", "inward", "inward_fast", "outward_normal"] {
        socket.send(Message::Text(command.into())).await.unwrap();
    }
    for _ in 0..2 {
        socket.send(Message::Text("next".into())).await.unwrap();
    }
    for _ in 0..2 {
        let status = socket.next().await.unwrap().unwrap();
        let status: Value = serde_json::from_str(status.to_text().unwrap()).unwrap();
        assert_eq!(status["alive"], 1);
        let frame = socket.next().await.unwrap().unwrap().into_data();
        assert_eq!(turbojpeg::read_header(&frame).unwrap().width, 256);
    }
    socket.send(Message::Text("stop".into())).await.unwrap();
    assert!(
        socket
            .next()
            .await
            .unwrap()
            .unwrap()
            .to_text()
            .unwrap()
            .contains("stopped")
    );
    socket.close(None).await.unwrap();
    shutdown.send(true).unwrap();
    timeout(Duration::from_secs(2), server)
        .await
        .unwrap()
        .unwrap();
}

#[test]
fn disconnects_are_distinct_from_protocol_and_worker_failures() {
    use tokio_tungstenite::tungstenite::{Error, error::ProtocolError};
    let reset = anyhow::Error::new(axum::Error::new(Error::Protocol(
        ProtocolError::ResetWithoutClosingHandshake,
    )))
    .context("transport");
    assert!(app::disconnected(&reset));
    let broken_pipe = anyhow::Error::new(axum::Error::new(Error::Io(std::io::Error::from(
        std::io::ErrorKind::BrokenPipe,
    ))));
    assert!(app::disconnected(&broken_pipe));
    assert!(!app::disconnected(&anyhow::Error::new(Error::Protocol(
        ProtocolError::UnmaskedFrameFromClient
    ))));
    assert!(!app::disconnected(
        &anyhow::Error::new(std::io::Error::from(std::io::ErrorKind::BrokenPipe))
            .context("CUDA worker")
    ));
}
