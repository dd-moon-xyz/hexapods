use anyhow::{Result, ensure};
use std::borrow::Cow;

pub struct Encoder {
    compressor: turbojpeg::Compressor,
}

impl Encoder {
    pub fn new() -> Result<Self> {
        let mut compressor = turbojpeg::Compressor::new()?;
        compressor.set_quality(80)?;
        compressor.set_subsamp(turbojpeg::Subsamp::Sub2x2)?;
        Ok(Self { compressor })
    }

    pub fn encode(
        &mut self,
        raw: &mut [u8],
        size: usize,
        pixel_size: usize,
        output_size: Option<u32>,
    ) -> Result<Vec<u8>> {
        ensure!(raw.len() == size * size * 3, "Invalid RGB frame length");
        let stride = size * 3;
        for y in 0..size / 2 {
            let (top, bottom) = raw.split_at_mut((size - 1 - y) * stride);
            top[y * stride..(y + 1) * stride].swap_with_slice(&mut bottom[..stride]);
        }
        let mut pixels = Cow::Borrowed(&*raw);
        if pixel_size > 1 {
            let small_size = (size / pixel_size).max(1);
            let small = resize_box(&pixels, size, small_size);
            let expanded = (0..size * size * 3)
                .map(|index| {
                    let channel = index % 3;
                    let x = index / 3 % size;
                    let y = index / (size * 3);
                    let source_x = ((2 * x + 1) * small_size / (2 * size)).min(small_size - 1);
                    let source_y = ((2 * y + 1) * small_size / (2 * size)).min(small_size - 1);
                    small[(source_y * small_size + source_x) * 3 + channel]
                })
                .collect();
            pixels = Cow::Owned(expanded);
        }
        let output_size = output_size.unwrap_or(size as u32) as usize;
        if output_size != size {
            pixels = Cow::Owned(resize_box(&pixels, size, output_size));
        }
        self.compressor
            .compress_to_vec(turbojpeg::Image {
                pixels: &pixels,
                width: output_size,
                pitch: output_size * 3,
                height: output_size,
                format: turbojpeg::PixelFormat::RGB,
            })
            .map_err(Into::into)
    }
}

fn edge(pixel: usize, size: usize, output: usize) -> usize {
    (2 * pixel * size + output) / (2 * output)
}

pub fn resize_box(source: &[u8], size: usize, output: usize) -> Vec<u8> {
    let mut rows = vec![0; size * output * 3];
    for y in 0..size {
        for x in 0..output {
            let first = edge(x, size, output).min(size - 1);
            let last = edge(x + 1, size, output).max(first + 1).min(size);
            let count = (last - first) as u32;
            for channel in 0..3 {
                let sum: u32 = (first..last)
                    .map(|column| u32::from(source[(y * size + column) * 3 + channel]))
                    .sum();
                rows[(y * output + x) * 3 + channel] = ((sum + count / 2) / count) as u8;
            }
        }
    }
    let mut pixels = vec![0; output * output * 3];
    for y in 0..output {
        let first = edge(y, size, output).min(size - 1);
        let last = edge(y + 1, size, output).max(first + 1).min(size);
        let count = (last - first) as u32;
        for x in 0..output * 3 {
            let sum: u32 = (first..last)
                .map(|row| u32::from(rows[row * output * 3 + x]))
                .sum();
            pixels[y * output * 3 + x] = ((sum + count / 2) / count) as u8;
        }
    }
    pixels
}
