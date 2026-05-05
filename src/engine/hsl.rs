use crate::model::CrsSettings;

/// The 8 HSL color ranges used by Adobe Camera Raw.
/// Center hue angles in degrees.
const HUE_CENTERS: [f64; 8] = [
    0.0,    // Red
    30.0,   // Orange
    60.0,   // Yellow
    120.0,  // Green
    180.0,  // Aqua
    240.0,  // Blue
    300.0,  // Purple
    330.0,  // Magenta
];

/// Convert RGB (0..1) to HSL (hue in degrees, S and L in 0..1).
fn rgb_to_hsl(r: f64, g: f64, b: f64) -> (f64, f64, f64) {
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let l = (max + min) / 2.0;

    if (max - min).abs() < 1e-10 {
        return (0.0, 0.0, l);
    }

    let d = max - min;
    let s = if l > 0.5 {
        d / (2.0 - max - min)
    } else {
        d / (max + min)
    };

    let h = if (max - r).abs() < 1e-10 {
        let mut h = (g - b) / d;
        if g < b {
            h += 6.0;
        }
        h * 60.0
    } else if (max - g).abs() < 1e-10 {
        ((b - r) / d + 2.0) * 60.0
    } else {
        ((r - g) / d + 4.0) * 60.0
    };

    (h % 360.0, s, l)
}

/// Convert HSL (hue in degrees, S and L in 0..1) to RGB (0..1).
fn hsl_to_rgb(h: f64, s: f64, l: f64) -> (f64, f64, f64) {
    if s.abs() < 1e-10 {
        return (l, l, l);
    }

    let q = if l < 0.5 {
        l * (1.0 + s)
    } else {
        l + s - l * s
    };
    let p = 2.0 * l - q;
    let h_norm = h / 360.0;

    let r = hue_to_rgb(p, q, h_norm + 1.0 / 3.0);
    let g = hue_to_rgb(p, q, h_norm);
    let b = hue_to_rgb(p, q, h_norm - 1.0 / 3.0);

    (r, g, b)
}

fn hue_to_rgb(p: f64, q: f64, mut t: f64) -> f64 {
    if t < 0.0 { t += 1.0; }
    if t > 1.0 { t -= 1.0; }

    if t < 1.0 / 6.0 {
        p + (q - p) * 6.0 * t
    } else if t < 1.0 / 2.0 {
        q
    } else if t < 2.0 / 3.0 {
        p + (q - p) * (2.0 / 3.0 - t) * 6.0
    } else {
        p
    }
}

/// Compute the angular distance between two hue angles (0..360), result in [0, 180].
fn hue_distance(h1: f64, h2: f64) -> f64 {
    let d = (h1 - h2).abs() % 360.0;
    if d > 180.0 { 360.0 - d } else { d }
}

/// Compute smooth falloff weight for a hue relative to a color range center.
/// Uses a cosine falloff within the range width.
fn hue_weight(hue: f64, center: f64, half_width: f64) -> f64 {
    let dist = hue_distance(hue, center);
    if dist >= half_width {
        0.0
    } else {
        let t = dist / half_width;
        // Smooth cosine falloff
        (1.0 + (t * std::f64::consts::PI).cos()) / 2.0
    }
}

/// Apply HSL selective adjustments: per-range Hue, Saturation, and Luminance shifts.
///
/// Each of the 8 color ranges has its own H/S/L adjustment (-100..+100).
/// A smooth cosine falloff blends between adjacent ranges.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let hue_adj = [
        settings.hue_adjustment_red,
        settings.hue_adjustment_orange,
        settings.hue_adjustment_yellow,
        settings.hue_adjustment_green,
        settings.hue_adjustment_aqua,
        settings.hue_adjustment_blue,
        settings.hue_adjustment_purple,
        settings.hue_adjustment_magenta,
    ];
    let sat_adj = [
        settings.saturation_adjustment_red,
        settings.saturation_adjustment_orange,
        settings.saturation_adjustment_yellow,
        settings.saturation_adjustment_green,
        settings.saturation_adjustment_aqua,
        settings.saturation_adjustment_blue,
        settings.saturation_adjustment_purple,
        settings.saturation_adjustment_magenta,
    ];
    let lum_adj = [
        settings.luminance_adjustment_red,
        settings.luminance_adjustment_orange,
        settings.luminance_adjustment_yellow,
        settings.luminance_adjustment_green,
        settings.luminance_adjustment_aqua,
        settings.luminance_adjustment_blue,
        settings.luminance_adjustment_purple,
        settings.luminance_adjustment_magenta,
    ];

    // Early exit if all adjustments are zero
    let all_zero = hue_adj.iter().chain(sat_adj.iter()).chain(lum_adj.iter())
        .all(|v| v.abs() < 1e-10);
    if all_zero {
        return rgb;
    }

    let (h, s, l) = rgb_to_hsl(rgb[0], rgb[1], rgb[2]);

    // Achromatic colors are unaffected by HSL adjustments
    if s < 1e-6 {
        return rgb;
    }

    // Half-width of each hue range (degrees). Ranges overlap for smooth blending.
    let half_width = 30.0;

    let mut hue_shift = 0.0;
    let mut sat_shift = 0.0;
    let mut lum_shift = 0.0;

    for i in 0..8 {
        let w = hue_weight(h, HUE_CENTERS[i], half_width);
        if w > 1e-10 {
            hue_shift += w * hue_adj[i];
            sat_shift += w * sat_adj[i];
            lum_shift += w * lum_adj[i];
        }
    }

    // Apply shifts
    // Hue: -100..+100 maps to ±30° shift
    let new_h = (h + hue_shift * 0.3) % 360.0;
    let new_h = if new_h < 0.0 { new_h + 360.0 } else { new_h };

    // Saturation: -100..+100 maps to multiplicative factor
    let sat_factor = 1.0 + sat_shift / 100.0;
    let new_s = (s * sat_factor).clamp(0.0, 1.0);

    // Luminance: -100..+100 maps to additive shift of ±0.5
    let new_l = (l + lum_shift / 200.0).clamp(0.0, 1.0);

    let (r, g, b) = hsl_to_rgb(new_h, new_s, new_l);
    [r.clamp(0.0, 1.0), g.clamp(0.0, 1.0), b.clamp(0.0, 1.0)]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_adjustments_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.8, 0.2, 0.3];
        let out = apply(rgb, &settings);
        assert!((out[0] - rgb[0]).abs() < 1e-10);
        assert!((out[1] - rgb[1]).abs() < 1e-10);
        assert!((out[2] - rgb[2]).abs() < 1e-10);
    }

    #[test]
    fn achromatic_unaffected() {
        let mut settings = CrsSettings::default();
        settings.saturation_adjustment_red = 100.0;
        let gray = [0.5, 0.5, 0.5];
        let out = apply(gray, &settings);
        assert!((out[0] - 0.5).abs() < 1e-10);
    }

    #[test]
    fn red_hue_shift() {
        let mut settings = CrsSettings::default();
        settings.hue_adjustment_red = 50.0;
        // Pure-ish red
        let rgb = [0.9, 0.1, 0.1];
        let out = apply(rgb, &settings);
        let (h_out, _, _) = rgb_to_hsl(out[0], out[1], out[2]);
        let (h_in, _, _) = rgb_to_hsl(rgb[0], rgb[1], rgb[2]);
        // Hue should have shifted positively
        assert!(hue_distance(h_out, h_in) > 5.0);
    }

    #[test]
    fn blue_saturation_boost() {
        let mut settings = CrsSettings::default();
        settings.saturation_adjustment_blue = 80.0;
        // Blue-ish color
        let rgb = [0.2, 0.2, 0.7];
        let out = apply(rgb, &settings);
        let (_, s_in, _) = rgb_to_hsl(rgb[0], rgb[1], rgb[2]);
        let (_, s_out, _) = rgb_to_hsl(out[0], out[1], out[2]);
        assert!(s_out > s_in, "Blue saturation should increase");
    }

    #[test]
    fn rgb_hsl_roundtrip() {
        let test_vals = [
            [0.8, 0.2, 0.3],
            [0.1, 0.9, 0.5],
            [0.5, 0.5, 0.8],
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
        ];
        for rgb in &test_vals {
            let (h, s, l) = rgb_to_hsl(rgb[0], rgb[1], rgb[2]);
            let (r, g, b) = hsl_to_rgb(h, s, l);
            assert!((r - rgb[0]).abs() < 1e-10, "R mismatch for {:?}", rgb);
            assert!((g - rgb[1]).abs() < 1e-10, "G mismatch for {:?}", rgb);
            assert!((b - rgb[2]).abs() < 1e-10, "B mismatch for {:?}", rgb);
        }
    }
}
