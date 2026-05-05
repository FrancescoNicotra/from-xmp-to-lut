use crate::model::CrsSettings;

/// Apply split toning: tint highlights and shadows with separate hues.
///
/// - **Shadow hue/saturation**: applied to dark areas (luminance < 0.5)
/// - **Highlight hue/saturation**: applied to bright areas (luminance > 0.5)
/// - **Balance** (-100..+100): shifts the crossover point between shadow and highlight zones
///
/// The tint is blended in using the luminance as a mask, with the hue applied
/// in HSL space at the specified saturation intensity.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let sh_sat = settings.split_toning_shadow_saturation;
    let hl_sat = settings.split_toning_highlight_saturation;

    if sh_sat.abs() < 1e-10 && hl_sat.abs() < 1e-10 {
        return rgb;
    }

    let lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];

    // Balance shifts the crossover point: 0 = 0.5, -100 = 0.25, +100 = 0.75
    let crossover = 0.5 + settings.split_toning_balance / 200.0;

    // Shadow weight: 1.0 at black, 0.0 at crossover
    let shadow_w = if lum < crossover {
        1.0 - lum / crossover
    } else {
        0.0
    };

    // Highlight weight: 0.0 at crossover, 1.0 at white
    let highlight_w = if lum > crossover {
        (lum - crossover) / (1.0 - crossover + 1e-10)
    } else {
        0.0
    };

    let mut r = rgb[0];
    let mut g = rgb[1];
    let mut b = rgb[2];

    // Apply shadow tint
    if sh_sat > 1e-10 && shadow_w > 1e-10 {
        let (tr, tg, tb) = hue_to_rgb(settings.split_toning_shadow_hue);
        let intensity = (sh_sat / 100.0) * shadow_w;
        r = lerp(r, tr * lum_match(lum), intensity);
        g = lerp(g, tg * lum_match(lum), intensity);
        b = lerp(b, tb * lum_match(lum), intensity);
    }

    // Apply highlight tint
    if hl_sat > 1e-10 && highlight_w > 1e-10 {
        let (tr, tg, tb) = hue_to_rgb(settings.split_toning_highlight_hue);
        let intensity = (hl_sat / 100.0) * highlight_w;
        r = lerp(r, tr * lum_match(lum), intensity);
        g = lerp(g, tg * lum_match(lum), intensity);
        b = lerp(b, tb * lum_match(lum), intensity);
    }

    [r.clamp(0.0, 1.0), g.clamp(0.0, 1.0), b.clamp(0.0, 1.0)]
}

/// Convert a hue angle (0..360) to a unit-brightness RGB color.
fn hue_to_rgb(hue: f64) -> (f64, f64, f64) {
    let h = (hue % 360.0) / 60.0;
    let sector = h.floor() as i32;
    let f = h - h.floor();

    match sector % 6 {
        0 => (1.0, f, 0.0),
        1 => (1.0 - f, 1.0, 0.0),
        2 => (0.0, 1.0, f),
        3 => (0.0, 1.0 - f, 1.0),
        4 => (f, 0.0, 1.0),
        _ => (1.0, 0.0, 1.0 - f),
    }
}

/// Scale factor to match original luminance when blending tint.
fn lum_match(lum: f64) -> f64 {
    // Prevent extreme brightening/darkening; target roughly 2x original luminance
    // for a fully-saturated tint color, then the lerp below handles intensity.
    (lum * 2.0).max(0.05)
}

fn lerp(a: f64, b: f64, t: f64) -> f64 {
    a + (b - a) * t
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_saturation_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.5, 0.3, 0.7];
        let out = apply(rgb, &settings);
        assert!((out[0] - rgb[0]).abs() < 1e-12);
        assert!((out[1] - rgb[1]).abs() < 1e-12);
        assert!((out[2] - rgb[2]).abs() < 1e-12);
    }

    #[test]
    fn shadow_tint_affects_darks() {
        let mut settings = CrsSettings::default();
        settings.split_toning_shadow_hue = 30.0; // Orange tint
        settings.split_toning_shadow_saturation = 80.0;

        let dark = [0.1, 0.1, 0.1];
        let out = apply(dark, &settings);
        // Dark pixels should shift toward orange (red should increase relative to blue)
        assert!(out[0] > dark[0] || out[2] < dark[2]);
    }

    #[test]
    fn highlight_tint_affects_brights() {
        let mut settings = CrsSettings::default();
        settings.split_toning_highlight_hue = 210.0; // Blue tint
        settings.split_toning_highlight_saturation = 80.0;

        let bright = [0.8, 0.8, 0.8];
        let out = apply(bright, &settings);
        // Bright pixels should shift toward blue
        assert!(out[2] > out[0] || out[2] > bright[2]);
    }
}
