mod app;
mod arena;
mod frames;
mod models;
mod worker;

#[cfg(all(test, unix))]
mod tests;

use anyhow::{Context, Result, bail};
use axum::serve::ListenerExt;
use std::{net::SocketAddr, path::PathBuf, sync::Arc};

#[tokio::main]
async fn main() -> Result<()> {
    let mut bind: SocketAddr = "0.0.0.0:9877".parse()?;
    let mut worker = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("native/build/hexapods");
    let mut args = std::env::args().skip(1);
    while let Some(option) = args.next() {
        match option.as_str() {
            "--bind" => bind = args.next().context("Missing --bind address")?.parse()?,
            "--worker" => worker = args.next().context("Missing --worker executable")?.into(),
            "-h" | "--help" => {
                println!(
                    "Uncapped Hexapods Rust server\n\nUsage: server [--bind 0.0.0.0:9877] [--worker /path/to/hexapods]"
                );
                return Ok(());
            }
            _ => bail!("Unknown option: {option}"),
        }
    }
    let (shutdown, receiver) = tokio::sync::watch::channel(false);
    let state = app::AppState {
        worker: Arc::new(worker),
        shutdown: receiver,
    };
    let listener = tokio::net::TcpListener::bind(bind).await?;
    eprintln!("Rust server listening on {}", listener.local_addr()?);
    let listener = listener.tap_io(|stream| {
        if let Err(error) = stream.set_nodelay(true) {
            eprintln!("Cannot enable TCP_NODELAY: {error}");
        }
    });
    axum::serve(listener, app::router(state))
        .with_graceful_shutdown(async move {
            let _ = tokio::signal::ctrl_c().await;
            let _ = shutdown.send(true);
        })
        .await?;
    Ok(())
}
