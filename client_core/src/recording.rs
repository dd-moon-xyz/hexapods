use anyhow::{Context, Result, bail};
use std::{
    io::Write,
    path::Path,
    process::{Child, ChildStdin, Command, Stdio},
    thread,
    time::{Duration, Instant},
};
use tungstenite::Bytes;

pub struct VideoRecorder<W: Write> {
    writer: W,
    fps: u32,
    started: Option<Instant>,
    frame: Bytes,
    frames: u64,
}

impl<W: Write> VideoRecorder<W> {
    pub fn new(writer: W, fps: u32) -> Self {
        Self {
            writer,
            fps,
            started: None,
            frame: Bytes::new(),
            frames: 0,
        }
    }

    pub fn advance(&mut self, now: Instant) -> Result<()> {
        if self.frame.is_empty() {
            return Ok(());
        }
        let Some(started) = self.started else {
            return Ok(());
        };
        let target = (now.saturating_duration_since(started).as_secs_f64() * f64::from(self.fps))
            .round_ties_even()
            .max(1.0) as u64;
        while self.frames < target {
            self.writer.write_all(&self.frame)?;
            self.frames += 1;
        }
        Ok(())
    }

    pub fn write(&mut self, frame: Bytes, now: Instant) -> Result<()> {
        if self.started.is_none() {
            self.started = Some(now);
        }
        self.advance(now)?;
        self.frame = frame;
        Ok(())
    }
}

pub struct Recording {
    pub video: Option<VideoRecorder<ChildStdin>>,
    process: Child,
}

impl Recording {
    pub fn start(path: &Path, fps: u32) -> Result<Self> {
        let mut process = Command::new("ffmpeg")
            .args(["-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate"])
            .arg(fps.to_string())
            .args(["-c:v", "mjpeg", "-i", "pipe:0", "-vf",
                "scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
            .arg(path)
            .stdin(Stdio::piped())
            .spawn().context("Cannot start FFmpeg")?;
        let pipe = process
            .stdin
            .take()
            .context("FFmpeg stdin is unavailable")?;
        Ok(Self {
            video: Some(VideoRecorder::new(pipe, fps)),
            process,
        })
    }

    pub fn finish(mut self) -> Result<()> {
        let write_result = self
            .video
            .as_mut()
            .context("Recording already closed")?
            .advance(Instant::now());
        self.video.take();
        let deadline = Instant::now() + Duration::from_secs(10);
        loop {
            if let Some(status) = self.process.try_wait()? {
                write_result?;
                if !status.success() {
                    bail!("Video recording failed: {status}");
                }
                return Ok(());
            }
            if Instant::now() >= deadline {
                bail!("Timed out finalizing video recording");
            }
            thread::sleep(Duration::from_millis(10));
        }
    }
}

impl Drop for Recording {
    fn drop(&mut self) {
        self.video.take();
        let _ = self.process.kill();
        let _ = self.process.wait();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_frame_intervals_and_final_hold() {
        let mut video = VideoRecorder::new(Vec::new(), 30);
        let start = Instant::now();
        for (frame, delay) in [(b"A", 0), (b"B", 100), (b"C", 400)] {
            video
                .write(
                    Bytes::from_static(frame),
                    start + Duration::from_millis(delay),
                )
                .unwrap();
        }
        video.advance(start + Duration::from_millis(500)).unwrap();
        assert_eq!(video.writer, b"AAABBBBBBBBBCCC");
    }

    #[test]
    fn fast_arrivals_do_not_speed_up_recording() {
        let mut video = VideoRecorder::new(Vec::new(), 30);
        let start = Instant::now();
        video.advance(start).unwrap();
        assert!(video.writer.is_empty());
        for index in 0..100 {
            video
                .write(
                    vec![index].into(),
                    start + Duration::from_secs_f64(f64::from(index) / 300.0),
                )
                .unwrap();
        }
        video
            .advance(start + Duration::from_secs_f64(1.0 / 3.0))
            .unwrap();
        assert_eq!(video.writer.len(), 10);
    }

    #[test]
    fn takes_ownership_without_copying_the_jpeg() {
        let frame = Bytes::from(vec![1, 2, 3, 4]);
        let original = frame.as_ptr();
        let mut video = VideoRecorder::new(Vec::new(), 30);
        video.write(frame, Instant::now()).unwrap();
        assert_eq!(video.frame.as_ptr(), original);
    }
}
