use crate::model::{CrsSettings, ToneCurvePoint};

/// Apply tone curve transformation using monotone cubic spline interpolation
/// (Fritsch-Carlson method) through user-defined control points.
///
/// The composite curve is applied to all channels, then per-channel curves
/// (Red, Green, Blue) are applied individually.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let r = eval_curve(&settings.tone_curve_pv2012, rgb[0]);
    let g = eval_curve(&settings.tone_curve_pv2012, rgb[1]);
    let b = eval_curve(&settings.tone_curve_pv2012, rgb[2]);

    // Per-channel curves on top of the composite curve
    let r = eval_curve(&settings.tone_curve_pv2012_red, r);
    let g = eval_curve(&settings.tone_curve_pv2012_green, g);
    let b = eval_curve(&settings.tone_curve_pv2012_blue, b);

    [r, g, b]
}

/// Evaluate a tone curve at a given input value (0..1, mapped to 0..255 internally).
fn eval_curve(points: &[ToneCurvePoint], val: f64) -> f64 {
    if points.len() < 2 {
        return val;
    }

    // Check if this is the identity curve (two points: 0,0 and 255,255)
    if points.len() == 2 {
        let p0 = &points[0];
        let p1 = &points[1];
        if (p0.x).abs() < 1e-6 && (p0.y).abs() < 1e-6
            && (p1.x - 255.0).abs() < 1e-6 && (p1.y - 255.0).abs() < 1e-6
        {
            return val;
        }
    }

    let x_input = val * 255.0;

    // Extract sorted x, y arrays
    let n = points.len();
    let xs: Vec<f64> = points.iter().map(|p| p.x).collect();
    let ys: Vec<f64> = points.iter().map(|p| p.y).collect();

    // Clamp to curve range
    if x_input <= xs[0] {
        return (ys[0] / 255.0).clamp(0.0, 1.0);
    }
    if x_input >= xs[n - 1] {
        return (ys[n - 1] / 255.0).clamp(0.0, 1.0);
    }

    // Compute spline slopes using Fritsch-Carlson monotone method
    let slopes = fritsch_carlson_slopes(&xs, &ys);

    // Find the segment
    let mut seg = 0;
    for i in 0..n - 1 {
        if x_input >= xs[i] && x_input < xs[i + 1] {
            seg = i;
            break;
        }
    }

    // Hermite interpolation within the segment
    let h = xs[seg + 1] - xs[seg];
    if h.abs() < 1e-10 {
        return (ys[seg] / 255.0).clamp(0.0, 1.0);
    }

    let t = (x_input - xs[seg]) / h;
    let t2 = t * t;
    let t3 = t2 * t;

    // Hermite basis functions
    let h00 = 2.0 * t3 - 3.0 * t2 + 1.0;
    let h10 = t3 - 2.0 * t2 + t;
    let h01 = -2.0 * t3 + 3.0 * t2;
    let h11 = t3 - t2;

    let y = h00 * ys[seg] + h10 * h * slopes[seg] + h01 * ys[seg + 1] + h11 * h * slopes[seg + 1];

    (y / 255.0).clamp(0.0, 1.0)
}

/// Compute monotone cubic slopes using the Fritsch-Carlson method.
///
/// This ensures the interpolation preserves monotonicity between control points,
/// avoiding overshoot and color artifacts.
fn fritsch_carlson_slopes(xs: &[f64], ys: &[f64]) -> Vec<f64> {
    let n = xs.len();
    if n < 2 {
        return vec![0.0; n];
    }

    // Step 1: Compute secant slopes (delta_k)
    let mut deltas = Vec::with_capacity(n - 1);
    for i in 0..n - 1 {
        let dx = xs[i + 1] - xs[i];
        if dx.abs() < 1e-10 {
            deltas.push(0.0);
        } else {
            deltas.push((ys[i + 1] - ys[i]) / dx);
        }
    }

    // Step 2: Initialize slopes as average of adjacent secants
    let mut slopes = vec![0.0; n];
    slopes[0] = deltas[0];
    slopes[n - 1] = deltas[n - 2];
    for i in 1..n - 1 {
        if deltas[i - 1].signum() != deltas[i].signum() {
            slopes[i] = 0.0;
        } else {
            slopes[i] = (deltas[i - 1] + deltas[i]) / 2.0;
        }
    }

    // Step 3: Enforce monotonicity (Fritsch-Carlson conditions)
    for i in 0..n - 1 {
        if deltas[i].abs() < 1e-10 {
            slopes[i] = 0.0;
            slopes[i + 1] = 0.0;
        } else {
            let alpha = slopes[i] / deltas[i];
            let beta = slopes[i + 1] / deltas[i];
            let sum_sq = alpha * alpha + beta * beta;
            if sum_sq > 9.0 {
                let tau = 3.0 / sum_sq.sqrt();
                slopes[i] = tau * alpha * deltas[i];
                slopes[i + 1] = tau * beta * deltas[i];
            }
        }
    }

    slopes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_curve_is_passthrough() {
        let settings = CrsSettings::default();
        let rgb = [0.3, 0.5, 0.8];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.3).abs() < 1e-10);
        assert!((out[1] - 0.5).abs() < 1e-10);
        assert!((out[2] - 0.8).abs() < 1e-10);
    }

    #[test]
    fn s_curve_increases_contrast() {
        let mut settings = CrsSettings::default();
        // Classic S-curve: darken shadows, brighten highlights
        settings.tone_curve_pv2012 = vec![
            ToneCurvePoint { x: 0.0, y: 0.0 },
            ToneCurvePoint { x: 64.0, y: 48.0 },   // darken shadows
            ToneCurvePoint { x: 192.0, y: 208.0 },  // brighten highlights
            ToneCurvePoint { x: 255.0, y: 255.0 },
        ];
        settings.tone_curve_pv2012_red = vec![
            ToneCurvePoint { x: 0.0, y: 0.0 },
            ToneCurvePoint { x: 255.0, y: 255.0 },
        ];
        settings.tone_curve_pv2012_green = settings.tone_curve_pv2012_red.clone();
        settings.tone_curve_pv2012_blue = settings.tone_curve_pv2012_red.clone();

        let shadow = apply([0.25, 0.25, 0.25], &settings);
        let highlight = apply([0.75, 0.75, 0.75], &settings);

        assert!(shadow[0] < 0.25, "S-curve should darken shadows");
        assert!(highlight[0] > 0.75, "S-curve should brighten highlights");
    }

    #[test]
    fn per_channel_curve() {
        let mut settings = CrsSettings::default();
        // Boost red channel only
        settings.tone_curve_pv2012_red = vec![
            ToneCurvePoint { x: 0.0, y: 0.0 },
            ToneCurvePoint { x: 128.0, y: 180.0 },
            ToneCurvePoint { x: 255.0, y: 255.0 },
        ];

        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        assert!(out[0] > out[1], "Red channel should be boosted");
    }

    #[test]
    fn endpoints_are_preserved() {
        let settings = CrsSettings::default();
        let black = apply([0.0, 0.0, 0.0], &settings);
        let white = apply([1.0, 1.0, 1.0], &settings);
        assert!((black[0]).abs() < 1e-10);
        assert!((white[0] - 1.0).abs() < 1e-10);
    }
}
