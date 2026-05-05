use crate::model::CrsSettings;

/// Mid-gray in perceptual (gamma-encoded) space, used as the pivot for the contrast curve.
const MID_GRAY: f64 = 0.5;

/// Apply sigmoidal contrast centered at mid-gray.
///
/// The contrast slider (-100..+100) controls the steepness of a sigmoid curve.
/// Positive values increase contrast (steepen the curve around mid-gray),
/// negative values decrease it (flatten the curve).
///
/// The function uses a simple power/sigmoid blend:
/// - Map value to [0,1] centered at MID_GRAY
/// - Apply a gain that increases slope at the center
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let c = settings.contrast_2012;
    if c.abs() < 1e-10 {
        return rgb;
    }

    // Map -100..+100 to a curve steepness parameter.
    // At contrast=100, the slope at mid-gray roughly doubles.
    let strength = c / 100.0;

    [
        apply_contrast_channel(rgb[0], strength),
        apply_contrast_channel(rgb[1], strength),
        apply_contrast_channel(rgb[2], strength),
    ]
}

/// Apply sigmoidal contrast to a single channel value in [0,1].
fn apply_contrast_channel(val: f64, strength: f64) -> f64 {
    // Use a simple S-curve: y = 0.5 + (x - 0.5) * gain_at_center
    // with smooth rolloff at the extremes using a sigmoid function.

    // Contrast factor: maps strength [-1,1] to a curve parameter
    // strength > 0 → more contrast, strength < 0 → less contrast
    let t = (val - MID_GRAY) * 2.0; // Map to [-1, 1]

    // Attempt a sigmoid-like mapping using atan as approximation
    // The slope at center is controlled by `k`
    let k = 1.0 + strength.abs() * 3.0; // k in [1, 4]

    let mapped = if strength >= 0.0 {
        // Increase contrast: steepen the curve
        (k * t).tanh() / k.tanh()
    } else {
        // Decrease contrast: flatten the curve (invert the sigmoid)
        // Use the inverse approach: lerp toward flat
        let flat_factor = strength.abs();
        t * (1.0 - flat_factor) + t.powi(3) * flat_factor * 0.3
    };

    (MID_GRAY + mapped * 0.5).clamp(0.0, 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_contrast_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.3, 0.5, 0.8];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.3).abs() < 1e-12);
        assert!((out[1] - 0.5).abs() < 1e-12);
        assert!((out[2] - 0.8).abs() < 1e-12);
    }

    #[test]
    fn mid_gray_unchanged() {
        let mut settings = CrsSettings::default();
        settings.contrast_2012 = 50.0;
        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.5).abs() < 1e-10);
        assert!((out[1] - 0.5).abs() < 1e-10);
        assert!((out[2] - 0.5).abs() < 1e-10);
    }

    #[test]
    fn positive_contrast_pushes_extremes() {
        let mut settings = CrsSettings::default();
        settings.contrast_2012 = 80.0;

        // Dark value should get darker
        let dark = apply([0.2, 0.2, 0.2], &settings);
        assert!(dark[0] < 0.2);

        // Bright value should get brighter
        let bright = apply([0.8, 0.8, 0.8], &settings);
        assert!(bright[0] > 0.8);
    }

    #[test]
    fn black_and_white_stay_fixed() {
        let mut settings = CrsSettings::default();
        settings.contrast_2012 = 100.0;
        let black = apply([0.0, 0.0, 0.0], &settings);
        let white = apply([1.0, 1.0, 1.0], &settings);
        assert!((black[0]).abs() < 0.05);
        assert!((white[0] - 1.0).abs() < 0.05);
    }
}
