pub mod white_balance;
pub mod exposure;
pub mod contrast;
pub mod highlights_shadows;
pub mod tone_curve;
pub mod hsl;
pub mod vibrance;
pub mod split_toning;
pub mod saturation;

use rayon::prelude::*;

use crate::identity::Lut3D;
use crate::model::CrsSettings;

/// Apply the full transformation pipeline to a single RGB triplet.
///
/// The order follows Adobe Camera Raw's processing chain:
/// 1. White Balance (Bradford chromatic adaptation)
/// 2. Exposure (linear gain in EV stops)
/// 3. Contrast (sigmoidal curve at mid-gray)
/// 4. Highlights / Shadows / Whites / Blacks (zone-based)
/// 5. Tone Curve (monotone cubic spline)
/// 6. HSL Adjustments (per-range hue/sat/lum)
/// 7. Vibrance (saturation-aware boost)
/// 8. Split Toning (highlight/shadow hue tint)
/// 9. Saturation (global)
pub fn apply_pipeline(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let rgb = white_balance::apply(rgb, settings);
    let rgb = exposure::apply(rgb, settings);
    let rgb = contrast::apply(rgb, settings);
    let rgb = highlights_shadows::apply(rgb, settings);
    let rgb = tone_curve::apply(rgb, settings);
    let rgb = hsl::apply(rgb, settings);
    let rgb = vibrance::apply(rgb, settings);
    let rgb = split_toning::apply(rgb, settings);
    saturation::apply(rgb, settings)
}

/// Process an entire 3D LUT by applying the pipeline to every sample point.
///
/// Uses `rayon` for parallel iteration across all N^3 samples.
pub fn process_lut(lut: &mut Lut3D, settings: &CrsSettings) {
    lut.data.par_iter_mut().for_each(|sample| {
        let rgb = [sample.r, sample.g, sample.b];
        let result = apply_pipeline(rgb, settings);
        sample.r = result[0];
        sample.g = result[1];
        sample.b = result[2];
    });
}

/// Generate a processed LUT: create an identity LUT and apply all transforms.
pub fn generate_lut(size: usize, settings: &CrsSettings) -> Lut3D {
    let mut lut = Lut3D::identity(size);
    process_lut(&mut lut, settings);
    lut
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_settings_produce_identity() {
        let settings = CrsSettings::default();
        let lut = generate_lut(8, &settings);

        let denom = 7.0_f64;
        for ib in 0..8 {
            for ig in 0..8 {
                for ir in 0..8 {
                    let idx = ir + 8 * ig + 64 * ib;
                    let s = &lut.data[idx];
                    let expected_r = ir as f64 / denom;
                    let expected_g = ig as f64 / denom;
                    let expected_b = ib as f64 / denom;
                    assert!(
                        (s.r - expected_r).abs() < 1e-10,
                        "R mismatch at ({},{},{}): {} vs {}",
                        ir, ig, ib, s.r, expected_r
                    );
                    assert!(
                        (s.g - expected_g).abs() < 1e-10,
                        "G mismatch at ({},{},{})",
                        ir, ig, ib
                    );
                    assert!(
                        (s.b - expected_b).abs() < 1e-10,
                        "B mismatch at ({},{},{})",
                        ir, ig, ib
                    );
                }
            }
        }
    }

    #[test]
    fn exposure_transforms_lut() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = 1.0; // +1 EV

        let lut = generate_lut(4, &settings);
        // Mid-gray sample: (2,2,2) in a 4x4x4 grid → 2/3 ≈ 0.667
        let idx = 2 + 4 * 2 + 16 * 2;
        let s = &lut.data[idx];
        let expected = (2.0_f64 / 3.0 * 2.0).min(1.0);
        assert!(
            (s.r - expected).abs() < 1e-10,
            "Expected {} got {}",
            expected,
            s.r
        );
    }

    #[test]
    fn pipeline_clamps_output() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = 5.0; // Extreme exposure

        let lut = generate_lut(4, &settings);
        for s in &lut.data {
            assert!(s.r >= 0.0 && s.r <= 1.0);
            assert!(s.g >= 0.0 && s.g <= 1.0);
            assert!(s.b >= 0.0 && s.b <= 1.0);
        }
    }

    #[test]
    fn full_pipeline_with_multiple_settings() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = 0.5;
        settings.contrast_2012 = 30.0;
        settings.saturation = 20.0;
        settings.vibrance = 40.0;

        let lut = generate_lut(8, &settings);
        // Just verify it doesn't panic and produces valid output
        for s in &lut.data {
            assert!(s.r >= 0.0 && s.r <= 1.0, "R out of range: {}", s.r);
            assert!(s.g >= 0.0 && s.g <= 1.0, "G out of range: {}", s.g);
            assert!(s.b >= 0.0 && s.b <= 1.0, "B out of range: {}", s.b);
        }
    }
}
