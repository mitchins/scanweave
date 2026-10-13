//! Foreground segmentation: conservative thresholding against a locally
//! estimated paper colour. No whitening, no despeckling (SPEC §5.2).

pub struct Segmentation {
    pub width: usize,
    pub height: usize,
    /// true = foreground ink
    pub fg: Vec<bool>,
    /// median paper colour estimate (corner patches)
    pub paper: [u8; 3],
    /// median ink colour estimate (foreground samples) — reconstruction must
    /// repaint ink in the SOURCE ink colour, not pure black (M0-Q repair:
    /// the whole-page MAE gate correctly caught pure-black over gray-30 ink)
    pub ink: [u8; 3],
}

fn lum(rgb: [u8; 3]) -> f64 {
    0.2126 * rgb[0] as f64 + 0.7152 * rgb[1] as f64 + 0.0722 * rgb[2] as f64
}

pub fn segment(rgb: &[u8], width: u32, height: u32) -> Segmentation {
    let (w, h) = (width as usize, height as usize);
    let px = |x: usize, y: usize| -> [u8; 3] {
        let i = (y * w + x) * 3;
        [rgb[i], rgb[i + 1], rgb[i + 2]]
    };

    // paper estimate: median of 4 corner patches (6x6)
    let patch = |cx: usize, cy: usize| -> [u8; 3] {
        let mut samples = Vec::new();
        for dy in 0..6 {
            for dx in 0..6 {
                let x = (cx + dx).min(w - 1);
                let y = (cy + dy).min(h - 1);
                samples.push(px(x, y));
            }
        }
        let ch = |c: usize| -> u8 {
            let mut v: Vec<u8> = samples.iter().map(|s| s[c]).collect();
            v.sort_unstable();
            v[v.len() / 2]
        };
        [ch(0), ch(1), ch(2)]
    };
    let corners = [
        patch(0, 0),
        patch(w.saturating_sub(6), 0),
        patch(0, h.saturating_sub(6)),
        patch(w.saturating_sub(6), h.saturating_sub(6)),
    ];
    let mut paper = [0u8; 3];
    for c in 0..3 {
        let mut v: Vec<u8> = corners.iter().map(|s| s[c]).collect();
        v.sort_unstable();
        paper[c] = v[2];
    }

    // conservative foreground: channel-distance from paper
    const FG_DELTA: f64 = 60.0;
    let paper_lum = lum(paper);
    let mut fg = vec![false; w * h];
    for y in 0..h {
        for x in 0..w {
            let p = px(x, y);
            let dist = (lum(p) - paper_lum).abs();
            if dist > FG_DELTA {
                fg[y * w + x] = true;
            }
        }
    }

    // ink colour: median over foreground samples
    let mut ink = paper;
    {
        let mut samples = Vec::new();
        for y in 0..h {
            for x in 0..w {
                if fg[y * w + x] {
                    samples.push(px(x, y));
                }
            }
        }
        if !samples.is_empty() {
            for c in 0..3 {
                let mut v: Vec<u8> = samples.iter().map(|s| s[c]).collect();
                v.sort_unstable();
                ink[c] = v[v.len() / 2];
            }
        }
    }

    Segmentation {
        width: w,
        height: h,
        fg,
        paper,
        ink,
    }
}
