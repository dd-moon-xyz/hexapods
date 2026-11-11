use crate::{
    arena::Arena,
    models::{self, Start},
};
use anyhow::{Result, bail};
use axum::{
    Json, Router,
    extract::{
        State,
        ws::{Message, WebSocket, WebSocketUpgrade},
    },
    response::{Html, Response},
    routing::{any, get},
};
use serde_json::json;
use std::{path::PathBuf, sync::Arc, time::Duration};
use tokio::{sync::watch, time::timeout};

#[derive(Clone)]
pub struct AppState {
    pub worker: Arc<PathBuf>,
    pub shutdown: watch::Receiver<bool>,
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/", get(|| async { Html(include_str!("../viewer.html")) }))
        .route("/preset", get(|| async { Json(models::preset()) }))
        .route("/ws", any(upgrade))
        .with_state(state)
}

async fn upgrade(State(state): State<AppState>, ws: WebSocketUpgrade) -> Response {
    ws.max_message_size(4 * 1024 * 1024)
        .max_frame_size(4 * 1024 * 1024)
        .on_upgrade(move |socket| handle(socket, state))
}

async fn handle(mut socket: WebSocket, mut state: AppState) {
    eprintln!("WebSocket session connected");
    let result = tokio::select! {
        result = session(&mut socket, &state.worker) => result,
        _ = state.shutdown.changed() => Ok(()),
    };
    if let Err(error) = result {
        if disconnected(&error) {
            eprintln!("WebSocket session closed");
            return;
        }
        eprintln!("WebSocket session ended: {error:#}");
        let _ = timeout(
            Duration::from_secs(5),
            socket.send(Message::Text(
                json!({"error": format!("{error:#}")}).to_string().into(),
            )),
        )
        .await;
    }
    let _ = timeout(Duration::from_secs(5), socket.send(Message::Close(None))).await;
    eprintln!("WebSocket session closed");
}

pub(crate) fn disconnected(error: &anyhow::Error) -> bool {
    use tokio_tungstenite::tungstenite::{Error, error::ProtocolError};
    error
        .chain()
        .any(|cause| match cause.downcast_ref::<Error>() {
            Some(Error::ConnectionClosed | Error::AlreadyClosed) => true,
            Some(Error::Protocol(
                ProtocolError::ResetWithoutClosingHandshake | ProtocolError::SendAfterClosing,
            )) => true,
            Some(Error::Io(error)) => matches!(
                error.kind(),
                std::io::ErrorKind::ConnectionReset
                    | std::io::ErrorKind::ConnectionAborted
                    | std::io::ErrorKind::BrokenPipe
                    | std::io::ErrorKind::UnexpectedEof
            ),
            _ => false,
        })
}

async fn receive(socket: &mut WebSocket, seconds: u64) -> Result<Option<String>> {
    loop {
        match timeout(Duration::from_secs(seconds), socket.recv()).await? {
            Some(Ok(Message::Text(text))) => return Ok(Some(text.to_string())),
            Some(Ok(Message::Close(_))) | None => return Ok(None),
            Some(Ok(Message::Ping(_))) | Some(Ok(Message::Pong(_))) => continue,
            Some(Ok(Message::Binary(_))) => bail!("Send commands as text messages"),
            Some(Err(error)) => return Err(error.into()),
        }
    }
}

async fn session(socket: &mut WebSocket, path: &std::path::Path) -> Result<()> {
    let Some(start) = receive(socket, 30).await? else {
        return Ok(());
    };
    let config = Start::parse(&start)?;
    let mut arena = Arena::start(path, config.clone()).await?;
    let result = run_session(socket, &config, &mut arena).await;
    let closed = arena.close().await;
    result.and(closed)
}

async fn run_session(socket: &mut WebSocket, config: &Start, arena: &mut Arena) -> Result<()> {
    socket
        .send(Message::Text(
            json!({
                "status": "started", "size": config.output_size.unwrap_or(config.size),
                "fps": config.fps, "fps_limit": null,
            })
            .to_string()
            .into(),
        ))
        .await?;
    while let Some(command) = receive(socket, 60).await? {
        match command.as_str() {
            "stop" => {
                socket
                    .send(Message::Text(
                        json!({"status": "stopped"}).to_string().into(),
                    ))
                    .await?;
                break;
            }
            "next" => {
                let (jpeg, alive) = arena.frame().await?;
                if config.population_updates {
                    socket.send(Message::Text(json!({"status": "population", "alive": alive, "total": config.organisms.len()}).to_string().into())).await?;
                }
                socket.send(Message::Binary(jpeg.into())).await?;
            }
            "outward" => arena.movement("o\n", true).await?,
            "outward_normal" => arena.movement("u\n", true).await?,
            "inward" => arena.movement("i\n", false).await?,
            "inward_fast" => arena.movement("b\n", false).await?,
            text if text.trim_start().starts_with('{') => {
                let (native, outward) = models::movement_command(text)?;
                arena.movement(&native, outward).await?;
            }
            _ => bail!("Send 'next', a movement command, or 'stop'"),
        }
    }
    Ok(())
}
