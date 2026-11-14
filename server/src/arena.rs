use crate::{frames::Encoder, models::Start, worker::Worker};
use anyhow::{Context, Result};
use std::{
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};
use tokio::{
    sync::Mutex,
    task::JoinHandle,
    time::{sleep, timeout},
};

pub struct Arena {
    config: Arc<Start>,
    worker: Arc<Mutex<Worker>>,
    birth_lock: Arc<Mutex<()>>,
    birth_rate_lock: Arc<Mutex<()>>,
    outward: Arc<AtomicBool>,
    dead_frames: Vec<u8>,
    living: Vec<bool>,
    pending: Vec<Option<JoinHandle<Result<()>>>>,
    encoder: Arc<std::sync::Mutex<Encoder>>,
}

impl Arena {
    pub async fn start(path: &Path, config: Start) -> Result<Self> {
        let worker = timeout(Duration::from_secs(30), Worker::start(path, &config)).await??;
        let count = config.organisms.len();
        Ok(Self {
            config: Arc::new(config),
            worker: Arc::new(Mutex::new(worker)),
            birth_lock: Arc::new(Mutex::new(())),
            birth_rate_lock: Arc::new(Mutex::new(())),
            outward: Arc::new(AtomicBool::new(false)),
            dead_frames: vec![0; count],
            living: vec![false; count],
            pending: (0..count).map(|_| None).collect(),
            encoder: Arc::new(std::sync::Mutex::new(Encoder::new()?)),
        })
    }

    pub async fn frame(&mut self) -> Result<JoinHandle<Result<(Vec<u8>, usize)>>> {
        for index in 0..self.pending.len() {
            if self.pending[index]
                .as_ref()
                .is_some_and(|task| task.is_finished())
            {
                self.pending[index].take().unwrap().await??;
                self.dead_frames[index] = 0;
            }
        }
        let mut worker = self.worker.lock().await;
        timeout(Duration::from_secs(30), worker.frame()).await??;
        let alive = worker.masses.iter().filter(|mass| **mass > 0.001).count();
        for (index, mass) in worker.masses.iter().enumerate() {
            if self.pending[index].is_some() {
                continue;
            }
            self.dead_frames[index] = if *mass <= 0.001 {
                self.dead_frames[index].saturating_add(1)
            } else {
                0
            };
            if *mass > 0.001 {
                self.living[index] = true;
            }
            if self.dead_frames[index] == 5 && self.living[index] {
                eprintln!("Hexapod died: slot={index}");
                self.living[index] = false;
            }
            if self.dead_frames[index] >= 5
                && !self.config.preview
                && !self.outward.load(Ordering::Relaxed)
            {
                self.pending[index] = Some(self.schedule_birth(index));
            }
        }
        let size = worker.size;
        let mut pixels = std::mem::replace(&mut worker.pixels, vec![0; size * size * 3]);
        drop(worker);
        let config = Arc::clone(&self.config);
        let encoder = Arc::clone(&self.encoder);
        Ok(tokio::task::spawn_blocking(move || {
            let jpeg = encoder
                .lock()
                .map_err(|_| anyhow::anyhow!("JPEG encoder lock poisoned"))?
                .encode(
                    &mut pixels,
                    size,
                    config.pixel_size as usize,
                    config.output_size,
                )?;

            Ok((jpeg, alive))
        }))
    }

    fn schedule_birth(&self, index: usize) -> JoinHandle<Result<()>> {
        let config = Arc::clone(&self.config);
        let worker = Arc::clone(&self.worker);
        let birth_lock = Arc::clone(&self.birth_lock);
        let birth_rate_lock = Arc::clone(&self.birth_rate_lock);
        let outward = Arc::clone(&self.outward);
        tokio::spawn(async move {
            let _rate = birth_rate_lock.lock().await;
            let minimum = 1.0 / config.birth_rate_max;
            let maximum = 1.0 / config.birth_rate_min;
            let seconds = minimum + (maximum - minimum) * rand::random::<f64>();
            sleep(Duration::try_from_secs_f64(seconds).context("Invalid birth interval")?).await;
            let _birth = birth_lock.lock().await;
            if !outward.load(Ordering::Relaxed) {
                let scale = rand::random_range(config.scale_min..=config.scale_max);
                let angle = rand::random::<f64>() * std::f64::consts::TAU;
                let mut worker = worker.lock().await;
                timeout(
                    Duration::from_secs(30),
                    worker.command(&format!("r {index} {scale} 128 128 {angle}\n")),
                )
                .await??;
                eprintln!("Hexapod born: slot={index} scale={scale}");
            }
            Ok(())
        })
    }

    pub async fn movement(&mut self, command: &str, outward: bool) -> Result<()> {
        let _birth = self.birth_lock.lock().await;
        let mut worker = self.worker.lock().await;
        timeout(Duration::from_secs(30), worker.command(command)).await??;
        self.outward.store(outward, Ordering::Relaxed);
        Ok(())
    }

    pub async fn close(&mut self) -> Result<()> {
        for task in self.pending.iter_mut().filter_map(Option::take) {
            task.abort();
            let _ = task.await;
        }
        self.worker.lock().await.close().await
    }
}

impl Drop for Arena {
    fn drop(&mut self) {
        for task in self.pending.iter().flatten() {
            task.abort();
        }
    }
}
