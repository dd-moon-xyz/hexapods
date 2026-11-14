use crate::app::AppState;
use anyhow::{Context, Result, ensure};
use axum::{
    Json,
    extract::{Request, State},
    http::{HeaderMap, StatusCode, header},
    middleware::Next,
    response::{IntoResponse, Response},
};
use rand::RngExt;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use tokio::sync::{OwnedSemaphorePermit, Semaphore};

pub struct Auth {
    tokens: HashMap<String, Arc<Semaphore>>,
    sessions: Mutex<HashMap<String, (String, Instant)>>,
    anonymous: bool,
}

impl Auth {
    pub fn load(anonymous: bool) -> Result<Arc<Self>> {
        let configured = std::env::var("HEXAPODS_TOKEN_HASHES").unwrap_or_default();
        Self::new(&configured, anonymous)
    }

    fn new(configured: &str, anonymous: bool) -> Result<Arc<Self>> {
        let mut tokens = HashMap::new();
        for entry in configured.split(',').filter(|entry| !entry.is_empty()) {
            let (name, hash) = entry
                .split_once(':')
                .context("Use client:sha256hex in HEXAPODS_TOKEN_HASHES")?;
            ensure!(
                !name.is_empty()
                    && hash.len() == 64
                    && hash.bytes().all(|byte| byte.is_ascii_hexdigit()),
                "Invalid client name or SHA-256 token hash"
            );
            ensure!(
                tokens
                    .insert(hash.to_ascii_lowercase(), Arc::new(Semaphore::new(1)))
                    .is_none(),
                "Duplicate token hash"
            );
        }
        ensure!(
            anonymous || !tokens.is_empty(),
            "Configure HEXAPODS_TOKEN_HASHES or explicitly use --allow-unauthenticated for trusted local access"
        );
        Ok(Arc::new(Self {
            tokens,
            sessions: Mutex::new(HashMap::new()),
            anonymous,
        }))
    }

    fn bearer(&self, headers: &HeaderMap) -> Option<String> {
        let token = headers
            .get(header::AUTHORIZATION)?
            .to_str()
            .ok()?
            .strip_prefix("Bearer ")?;
        let hash = format!("{:x}", Sha256::digest(token.as_bytes()));
        self.tokens.contains_key(&hash).then_some(hash)
    }

    fn identity(&self, headers: &HeaderMap) -> Option<String> {
        if let Some(hash) = self.bearer(headers) {
            return Some(hash);
        }
        let cookie = headers
            .get(header::COOKIE)?
            .to_str()
            .ok()?
            .split(';')
            .filter_map(|part| part.trim().split_once('='))
            .find_map(|(name, value)| (name == "__Host-hexapods").then_some(value))?;
        let sessions = self.sessions.lock().unwrap();
        let (hash, expires) = sessions.get(cookie)?;
        (*expires > Instant::now()).then(|| hash.clone())
    }

    pub fn acquire(&self, headers: &HeaderMap) -> Option<Option<OwnedSemaphorePermit>> {
        if self.anonymous {
            return Some(None);
        }
        let hash = self.identity(headers)?;
        self.tokens
            .get(&hash)?
            .clone()
            .try_acquire_owned()
            .ok()
            .map(Some)
    }
}

fn same_origin(headers: &HeaderMap) -> bool {
    let Some(origin) = headers
        .get(header::ORIGIN)
        .and_then(|value| value.to_str().ok())
    else {
        return false;
    };
    std::env::var("HEXAPODS_BROWSER_ORIGIN").is_ok_and(|allowed| allowed == origin)
}

pub async fn authorize(State(state): State<AppState>, request: Request, next: Next) -> Response {
    let path = request.uri().path();
    if state.auth.anonymous || path == "/" || path == "/login" {
        return next.run(request).await;
    }
    if request.headers().contains_key(header::ORIGIN) && !same_origin(request.headers()) {
        return StatusCode::FORBIDDEN.into_response();
    }
    if state.auth.identity(request.headers()).is_none() {
        return (
            StatusCode::UNAUTHORIZED,
            [(header::WWW_AUTHENTICATE, "Bearer")],
        )
            .into_response();
    }
    next.run(request).await
}

#[derive(Deserialize)]
pub struct Login {
    token: String,
}

pub async fn login(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(login): Json<Login>,
) -> Response {
    if !same_origin(&headers) {
        return StatusCode::FORBIDDEN.into_response();
    }
    let hash = format!("{:x}", Sha256::digest(login.token.as_bytes()));
    if !state.auth.tokens.contains_key(&hash) {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    let session = format!("{:032x}", rand::rng().random::<u128>())
        + &format!("{:032x}", rand::rng().random::<u128>());
    let mut sessions = state.auth.sessions.lock().unwrap();
    sessions.retain(|_, (_, expires)| *expires > Instant::now());
    if sessions.len() >= 1024 {
        return StatusCode::TOO_MANY_REQUESTS.into_response();
    }
    sessions.insert(
        session.clone(),
        (hash, Instant::now() + Duration::from_secs(3600)),
    );
    (
        StatusCode::NO_CONTENT,
        [
            (
                header::SET_COOKIE,
                format!("__Host-hexapods={session}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=3600"),
            ),
            (header::CACHE_CONTROL, "no-store".into()),
        ],
    )
        .into_response()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokens_are_required_and_validated() {
        assert!(Auth::new("", false).is_err());
        assert!(Auth::new("pi:invalid", false).is_err());
        let hash = format!("{:x}", Sha256::digest(b"test-secret"));
        let auth = Auth::new(&format!("pi:{hash}"), false).unwrap();
        let mut headers = HeaderMap::new();
        assert!(auth.identity(&headers).is_none());
        headers.insert(header::AUTHORIZATION, "Bearer wrong".parse().unwrap());
        assert!(auth.identity(&headers).is_none());
        headers.insert(header::AUTHORIZATION, "Bearer test-secret".parse().unwrap());
        let permit = auth.acquire(&headers).unwrap();
        assert!(auth.acquire(&headers).is_none());
        drop(permit);
        assert!(auth.acquire(&headers).is_some());
    }

    #[test]
    fn expired_sessions_are_rejected() {
        let hash = format!("{:x}", Sha256::digest(b"secret"));
        let auth = Auth::new(&format!("pi:{hash}"), false).unwrap();
        let mut headers = HeaderMap::new();
        headers.insert(header::COOKIE, "__Host-hexapods=session".parse().unwrap());
        auth.sessions.lock().unwrap().insert(
            "session".into(),
            (hash.clone(), Instant::now() + Duration::from_secs(60)),
        );
        assert_eq!(auth.identity(&headers), Some(hash.clone()));
        auth.sessions.lock().unwrap().insert(
            "session".into(),
            (hash, Instant::now() - Duration::from_secs(1)),
        );
        assert!(auth.identity(&headers).is_none());
    }

    #[tokio::test]
    async fn authentication_precedes_websocket_upgrade_and_worker_start() {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        use tokio_tungstenite::tungstenite::client::IntoClientRequest;
        let hash = format!("{:x}", Sha256::digest(b"secret"));
        let (_shutdown, shutdown) = tokio::sync::watch::channel(false);
        let state = AppState {
            auth: Auth::new(&format!("pi:{hash}"), false).unwrap(),
            worker: Arc::new("/nonexistent-worker".into()),
            shutdown,
        };
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            axum::serve(listener, crate::app::router(state))
                .await
                .unwrap();
        });
        for (path, authorization, expected) in [
            ("/preset", "", "401"),
            ("/ws", "", "401"),
            ("/preset", "Authorization: Bearer wrong\r\n", "401"),
            ("/preset", "Authorization: Bearer secret\r\n", "200"),
            (
                "/preset",
                "Authorization: Bearer secret\r\nOrigin: https://untrusted.invalid\r\n",
                "403",
            ),
        ] {
            let mut stream = tokio::net::TcpStream::connect(address).await.unwrap();
            stream.write_all(format!("GET {path} HTTP/1.1\r\nHost: localhost\r\n{authorization}Connection: close\r\n\r\n").as_bytes()).await.unwrap();
            let mut response = String::new();
            stream.read_to_string(&mut response).await.unwrap();
            assert!(
                response.starts_with(&format!("HTTP/1.1 {expected}")),
                "{response}"
            );
        }
        let mut request = format!("ws://{address}/ws").into_client_request().unwrap();
        request
            .headers_mut()
            .insert(header::AUTHORIZATION, "Bearer secret".parse().unwrap());
        let (mut socket, response) = tokio_tungstenite::connect_async(request.clone())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::SWITCHING_PROTOCOLS);
        let error = tokio_tungstenite::connect_async(request).await.unwrap_err();
        assert!(
            matches!(error, tokio_tungstenite::tungstenite::Error::Http(response) if response.status() == StatusCode::TOO_MANY_REQUESTS)
        );
        socket.close(None).await.unwrap();
        server.abort();
    }
}
