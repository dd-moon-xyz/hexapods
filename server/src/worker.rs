use crate::models::Start;
use anyhow::{Context, Result, ensure};
use std::{path::Path, process::Stdio};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader},
    process::{Child, ChildStdin, ChildStdout, Command},
};

pub struct Worker {
    process: Child,
    input: ChildStdin,
    output: BufReader<ChildStdout>,
    metadata: Vec<u8>,
    pub pixels: Vec<u8>,
    pub masses: Vec<f32>,
    pub size: usize,
}

impl Worker {
    pub async fn start(path: &Path, config: &Start) -> Result<Self> {
        let mut process = Command::new(path)
            .arg(if config.preview {
                "--stream-hexapod-preview"
            } else {
                "--stream-hexapod"
            })
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| format!("Cannot start CUDA worker {}", path.display()))?;
        let input = process.stdin.take().context("Worker stdin unavailable")?;
        let output = BufReader::new(process.stdout.take().context("Worker stdout unavailable")?);
        let count = config.organisms.len();
        let mut worker = Self {
            process,
            input,
            output,
            metadata: vec![0; count * 4],
            pixels: Vec::new(),
            masses: vec![0.0; count],
            size: config.size as usize,
        };
        // The native fps field integrates injury; it does not pace CUDA frames.
        let mut header = format!(
            "{} 60 {} {} {count} {} {}\n",
            config.size,
            config.dt,
            config.space_speed_multiplier,
            config.interaction_count_min,
            config.interaction_count_max
        );
        for item in &config.organisms {
            header.push_str(&format!("{} {} {}\n", item.scale, item.x, item.y));
        }
        worker.command(&header).await?;
        if config.pixel_size == 1 && config.output_size.is_some_and(|size| size < config.size) {
            worker.size = config.output_size.unwrap() as usize;
            worker.command(&format!("s {}\n", worker.size)).await?;
        }
        worker.pixels.resize(worker.size * worker.size * 3, 0);
        Ok(worker)
    }

    pub async fn command(&mut self, command: &str) -> Result<()> {
        self.input.write_all(command.as_bytes()).await?;
        self.input.flush().await?;
        let mut response = String::new();
        self.output.read_line(&mut response).await?;
        ensure!(
            response == "READY\n",
            "CUDA worker failed to acknowledge command; check GPU access and rebuild server/native/build/hexapods"
        );
        Ok(())
    }

    pub async fn frame(&mut self) -> Result<()> {
        self.input.write_all(b"n\n").await?;
        self.input.flush().await?;
        self.output.read_exact(&mut self.metadata).await?;
        for (mass, bytes) in self.masses.iter_mut().zip(self.metadata.chunks_exact(4)) {
            *mass = f32::from_ne_bytes(bytes.try_into()?);
        }
        self.output.read_exact(&mut self.pixels).await?;
        Ok(())
    }

    pub async fn close(&mut self) -> Result<()> {
        if self.process.try_wait()?.is_none() {
            self.process.kill().await?;
        }
        self.process.wait().await?;
        Ok(())
    }
}
