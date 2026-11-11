use anyhow::{Context, Result, bail};
use serde_json::Value;
use std::{fs, path::Path, time::Duration};
use url::Url;

pub const DEFAULT_URL: &str = "ws://127.0.0.1:9877/ws";

pub fn preset_url(address: &str) -> Result<Url> {
    let mut url = Url::parse(address).context("Invalid WebSocket URL")?;
    let scheme = match url.scheme() {
        "ws" => "http",
        "wss" => "https",
        _ => bail!("Expected a ws:// or wss:// server URL"),
    };
    url.set_scheme(scheme)
        .map_err(|_| anyhow::anyhow!("Invalid URL scheme"))?;
    let prefix = url.path().rsplit_once('/').map_or("", |(prefix, _)| prefix);
    let path = format!("{prefix}/preset");
    url.set_path(&path);
    url.set_query(None);
    url.set_fragment(None);
    Ok(url)
}

pub fn load(address: &str, path: Option<&Path>) -> Result<Value> {
    let text = match path {
        Some(path) => fs::read_to_string(path).context("Cannot read start configuration")?,
        None => ureq::get(preset_url(address)?.as_str())
            .config()
            .timeout_global(Some(Duration::from_secs(30)))
            .build()
            .call()
            .context("Cannot fetch server preset")?
            .body_mut()
            .read_to_string()?,
    };
    let config: Value = serde_json::from_str(&text).context("Invalid start configuration JSON")?;
    if !config.is_object() {
        bail!("Start configuration must be a JSON object");
    }
    Ok(config)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preset_paths_preserve_tls_and_prefix() {
        for (address, expected) in [
            ("ws://localhost:9876/ws", "http://localhost:9876/preset"),
            (
                "wss://example.test/hexapods/ws?token=x#fragment",
                "https://example.test/hexapods/preset",
            ),
        ] {
            assert_eq!(preset_url(address).unwrap().as_str(), expected);
        }
        assert!(preset_url("http://example.test/ws").is_err());
    }
}
