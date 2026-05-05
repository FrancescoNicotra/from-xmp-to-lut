use crate::model::CrsSettings;

/// Compute luminance from linear RGB (Rec. 709 coefficients).
fn luminance(rgb: &[f64; 3]) -> f64 {
    0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
}

/// Soft zone mask: smooth transition centered at `center` with given `width`.
/// Returns a weight in [0, 1] indicating how strongly the zone affects this luminance.
fn zone_mask(lum: f64, center: f64, width: f64) -> f64 {
    let dist = ((lum - center) / width).abs();
    (1.0 - dist).clamp(0.0, 1.0).powi(2)
}

/// Apply zone-based Highlights, Shadows, Whites, and Blacks adjustments.
///
/// Each slider shifts the luminance in its respective zone:
/// - **Whites** (zone ~0.9): affects the brightest tones
/// - **Highlights** (zone ~0.7): affects upper-mid tones
/// - **Shadows** (zone ~0.3): affects lower-mid tones
/// - **Blacks** (zone ~0.1): affects the darkest tones
///
/// The adjustments are additive and preserve color ratios (relative RGB).
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let h = settings.highlights_2012;
    let s = settings.shadows_2012;
    let w = settings.whites_2012;
    let b = settings.blacks_2012;

    if h.abs() < 1e-10 && s.abs() < 1e-10 && w.abs() < 1e-10 && b.abs() < 1e-10 {
        return rgb;
    }

    let lum = luminance(&rgb);

    // Zone definitions: (center, width, amount)
    // Amounts are normalized from -100..+100 to -0.5..+0.5 range
    let zones = [
        (0.90, 0.30, w / 200.0),  // Whites
        (0.70, 0.35, h / 200.0),  // Highlights
        (0.30, 0.35, s / 200.0),  // Shadows
        (0.10, 0.30, b / 200.0),  // Blacks
    ];

    let mut total_shift = 0.0;
    for &(center, width, amount) in &zones {
        let mask = zone_mask(lum, center, width);
        total_shift += mask * amount;
    }

    if total_shift.abs() < 1e-15 {
        return rgb;
    }

    // Apply luminance shift while preserving color ratios
    if lum < 1e-10 {
        // Near-black: just add the shift uniformly
        let v = total_shift.max(0.0);
        return [
            (rgb[0] + v).clamp(0.0, 1.0),
            (rgb[1] + v).clamp(0.0, 1.0),
            (rgb[2] + v).clamp(0.0, 1.0),
        ];
    }

    let target_lum = (lum + total_shift).clamp(0.0, 1.0);
    let ratio = target_lum / lum;

    [
        (rgb[0] * ratio).clamp(0.0, 1.0),
        (rgb[1] * ratio).clamp(0.0, 1.0),
        (rgb[2] * ratio).clamp(0.0, 1.0),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_adjustments_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.3, 0.5, 0.7];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.3).abs() < 1e-12);
        assert!((out[1] - 0.5).abs() < 1e-12);
        assert!((out[2] - 0.7).abs() < 1e-12);
    }

    #[test]
    fn positive_highlights_brightens_brights() {
        let mut settings = CrsSettings::default();
        settings.highlights_2012 = 80.0;
        let bright = [0.7, 0.7, 0.7];
        let out = apply(bright, &settings);
        assert!(out[0] > 0.7);
    }

    #[test]
    fn negative_shadows_darkens_darks() {
        let mut settings = CrsSettings::default();
        settings.shadows_2012 = -80.0;
        let dark = [0.2, 0.2, 0.2];
        let out = apply(dark, &settings);
        assert!(out[0] < 0.2);
    }

    #[test]
    fn preserves_color_ratio() {
        let mut settings = CrsSettings::default();
        settings.shadows_2012 = 50.0;
        let rgb = [0.2, 0.3, 0.1];
        let out = apply(rgb, &settings);
        // Ratios should be approximately preserved
        let orig_ratio = rgb[0] / rgb[1];
        let new_ratio = out[0] / out[1];
        assert!((orig_ratio - new_ratio).abs() < 0.01);
    }
}
