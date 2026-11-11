use anyhow::{Context, Result, bail};
use std::{collections::HashMap, env, fs, path::PathBuf};

pub struct Settings {
    pub url: String,
    pub config: Option<PathBuf>,
    pub windowed: bool,
    pub device: String,
    pub threshold: f64,
    pub axes: [String; 2],
    pub proximity: f64,
}

pub fn dotenv(text: &str) -> Result<HashMap<String, String>> {
    text.lines()
        .filter_map(|line| {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                return None;
            }
            Some((|| {
                let (key, value) = line
                    .strip_prefix("export ")
                    .unwrap_or(line)
                    .split_once('=')
                    .context("Invalid .env assignment")?;
                let value = value.trim();
                let value = match value.as_bytes().first() {
                    Some(b'"' | b'\'') => {
                        let quote = value.as_bytes()[0] as char;
                        let end = value[1..].find(quote).context("Unclosed .env quote")? + 1;
                        let trailing = value[end + 1..].trim();
                        if !trailing.is_empty() && !trailing.starts_with('#') {
                            bail!("Invalid trailing .env value");
                        }
                        value[1..end].to_owned()
                    }
                    _ => value.split(" #").next().unwrap_or("").trim().to_owned(),
                };
                Ok((key.trim().to_owned(), value))
            })())
        })
        .collect()
}

impl Settings {
    pub fn load() -> Result<Self> {
        let file = match fs::read_to_string(".env") {
            Ok(text) => dotenv(&text)?,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => HashMap::new(),
            Err(error) => return Err(error.into()),
        };
        Self::from_values(|key| env::var(key).ok().or_else(|| file.get(key).cloned()))
    }

    fn from_values(get: impl Fn(&str) -> Option<String>) -> Result<Self> {
        let url = get("LENIA_URL").unwrap_or_else(|| "ws://192.168.0.15:9877/ws".into());
        client_core::config::preset_url(&url)?;
        let threshold = get("LENIA_MOTION_THRESHOLD")
            .unwrap_or_else(|| "0.12".into())
            .parse::<f64>()?;
        let proximity = get("LENIA_PERSON_PROXIMITY")
            .unwrap_or_else(|| "0.5".into())
            .parse::<f64>()?;
        if !threshold.is_finite()
            || threshold <= 0.0
            || !proximity.is_finite()
            || !(0.0..1.0).contains(&proximity)
            || proximity == 0.0
        {
            bail!("Invalid motion/proximity threshold");
        }
        let axes = [
            get("LENIA_MOTION_SCREEN_X").unwrap_or_else(|| "y".into()),
            get("LENIA_MOTION_SCREEN_Y").unwrap_or_else(|| "x".into()),
        ];
        if axes
            .iter()
            .any(|axis| !["x", "-x", "y", "-y"].contains(&axis.as_str()))
            || axes[0].ends_with(axes[1].chars().last().unwrap())
        {
            bail!("Screen axes must select different x/y axes, optionally inverted");
        }
        let windowed = match get("LENIA_WINDOWED")
            .unwrap_or_else(|| "false".into())
            .to_lowercase()
            .as_str()
        {
            "true" | "1" | "yes" | "on" => true,
            "false" | "0" | "no" | "off" => false,
            _ => bail!("Invalid LENIA_WINDOWED"),
        };
        Ok(Self {
            url,
            config: get("LENIA_CONFIG")
                .filter(|s| !s.is_empty())
                .map(PathBuf::from),
            windowed,
            device: get("LENIA_MOTION_DEVICE").unwrap_or_else(|| "/dev/i2c-1".into()),
            threshold,
            axes,
            proximity,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn settings_validate_axes_thresholds_and_dotenv() {
        let values = dotenv("# settings\nexport LENIA_URL='ws://localhost:9877/ws' # comment\nLENIA_WINDOWED=true\n").unwrap();
        let settings = Settings::from_values(|key| values.get(key).cloned()).unwrap();
        assert!(settings.windowed);
        assert_eq!(settings.url, "ws://localhost:9877/ws");
        for (key, value) in [
            ("LENIA_MOTION_SCREEN_X", "x"),
            ("LENIA_MOTION_THRESHOLD", "NaN"),
            ("LENIA_PERSON_PROXIMITY", "1"),
        ] {
            assert!(Settings::from_values(|name| (name == key).then(|| value.into())).is_err());
        }
    }
}
