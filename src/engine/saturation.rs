use crate::model::CrsSettings;

/// Apply global saturation adjustment.
///
/// Saturation (-100..+100) controls how much color vs gray is in the image.
/// - At 0: no change (identity)
/// - At +100: maximum saturation boost
/// - At -100: fully desaturated (grayscale)
///
/// Implementation: lerp each channel toward/away from the Rec.709 luminance.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let s = settings.saturation;
    if s.abs() < 1e-10 {
        return rgb;
    }

    let lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
    // Map -100..+100 to a factor: 0.0 (grayscale) to 2.0 (double saturation)
    let factor = 1.0 + s / 100.0;

    [
        (lum + (rgb[0] - lum) * factor).clamp(0.0, 1.0),
        (lum + (rgb[1] - lum) * factor).clamp(0.0, 1.0),
        (lum + (rgb[2] - lum) * factor).clamp(0.0, 1.0),
    ]
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
    fn minus_100_is_grayscale() {
        let mut settings = CrsSettings::default();
        settings.saturation = -100.0;
        let rgb = [0.8, 0.2, 0.5];
        let out = apply(rgb, &settings);
        // All channels should equal luminance
        let lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
        assert!((out[0] - lum).abs() < 1e-10);
        assert!((out[1] - lum).abs() < 1e-10);
        assert!((out[2] - lum).abs() < 1e-10);
    }

    #[test]
    fn positive_saturation_increases_color() {
        let mut settings = CrsSettings::default();
        settings.saturation = 50.0;
        let rgb = [0.7, 0.3, 0.3];
        let out = apply(rgb, &settings);
        // Red channel is above luminance, so it should go further above
        assert!(out[0] > rgb[0]);
        // Green is below luminance, should go further below
        assert!(out[1] < rgb[1]);
    }

    #[test]
    fn achromatic_unaffected() {
        let mut settings = CrsSettings::default();
        settings.saturation = 100.0;
        let gray = [0.5, 0.5, 0.5];
        let out = apply(gray, &settings);
        assert!((out[0] - 0.5).abs() < 1e-10);
        assert!((out[1] - 0.5).abs() < 1e-10);
        assert!((out[2] - 0.5).abs() < 1e-10);
    }
}
