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
use std::{collections::VecDeque, path::PathBuf, sync::Arc, time::Duration};
use tokio::{sync::watch, time::timeout};

#[derive(Clone)]
pub struct AppState {
    pub auth: Arc<crate::auth::Auth>,
    pub worker: Arc<PathBuf>,
    pub shutdown: watch::Receiver<bool>,
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/", get(|| async { Html(include_str!("../viewer.html")) }))
        .route("/preset", get(|| async { Json(models::preset()) }))
        .route("/ws", any(upgrade))
        .route("/login", axum::routing::post(crate::auth::login))
        .layer(axum::middleware::from_fn_with_state(
            state.clone(),
            crate::auth::authorize,
        ))
        .with_state(state)
}

async fn upgrade(
    State(state): State<AppState>,
    headers: axum::http::HeaderMap,
    ws: WebSocketUpgrade,
) -> Response {
    let Some(permit) = state.auth.acquire(&headers) else {
        return axum::response::IntoResponse::into_response(
            axum::http::StatusCode::TOO_MANY_REQUESTS,
        );
    };
    ws.max_message_size(4 * 1024 * 1024)
        .max_frame_size(4 * 1024 * 1024)
        .on_upgrade(move |socket| async move {
            let _permit = permit;
            handle(socket, state).await;
        })
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
    let mut pending = VecDeque::<tokio::task::JoinHandle<Result<(Vec<u8>, usize)>>>::new();
    loop {
        let command = tokio::select! {
            result = async { pending.front_mut().unwrap().await }, if !pending.is_empty() => {
                let (jpeg, alive) = result??;
                pending.pop_front();
                if config.population_updates {
                    socket.send(Message::Text(json!({"status": "population", "alive": alive, "total": config.organisms.len()}).to_string().into())).await?;
                }
                socket.send(Message::Binary(jpeg.into())).await?;
                continue;
            }
            command = receive(socket, 60), if pending.len() < 2 => command?,
        };
        let Some(command) = command else {
            break;
        };

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
                pending.push_back(arena.frame().await?);
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
