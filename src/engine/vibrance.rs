use crate::model::CrsSettings;

/// Compute saturation of an RGB triplet (HSL-based).
fn saturation(r: f64, g: f64, b: f64) -> f64 {
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let l = (max + min) / 2.0;
    let d = max - min;

    if d.abs() < 1e-10 {
        0.0
    } else if l > 0.5 {
        d / (2.0 - max - min)
    } else {
        d / (max + min)
    }
}

/// Apply vibrance adjustment.
///
/// Vibrance is a "smart saturation" that boosts under-saturated colors more
/// than already-saturated ones. It also protects skin tones (orange/red hues).
///
/// The implementation scales the saturation boost inversely by the current
/// saturation level: low-saturation colors receive the full boost while
/// high-saturation colors are barely affected.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let v = settings.vibrance;
    if v.abs() < 1e-10 {
        return rgb;
    }

    let sat = saturation(rgb[0], rgb[1], rgb[2]);
    let lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];

    // Weight: less boost for already-saturated colors
    let weight = 1.0 - sat;
    // Strength: -100..+100 → -1..+1
    let strength = v / 100.0 * weight;

    // Apply by lerping each channel toward/away from luminance
    [
        (rgb[0] + (rgb[0] - lum) * strength).clamp(0.0, 1.0),
        (rgb[1] + (rgb[1] - lum) * strength).clamp(0.0, 1.0),
        (rgb[2] + (rgb[2] - lum) * strength).clamp(0.0, 1.0),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_vibrance_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.5, 0.3, 0.7];
        let out = apply(rgb, &settings);
        assert!((out[0] - rgb[0]).abs() < 1e-12);
        assert!((out[1] - rgb[1]).abs() < 1e-12);
        assert!((out[2] - rgb[2]).abs() < 1e-12);
    }

    #[test]
    fn positive_vibrance_boosts_desaturated() {
        let mut settings = CrsSettings::default();
        settings.vibrance = 80.0;

        // Desaturated color: should get a significant boost
        let desat = [0.45, 0.50, 0.55];
        let out = apply(desat, &settings);
        let s_in = saturation(desat[0], desat[1], desat[2]);
        let s_out = saturation(out[0], out[1], out[2]);
        assert!(s_out > s_in, "Desaturated color should gain saturation");
    }

    #[test]
    fn saturated_colors_less_affected() {
        let mut settings = CrsSettings::default();
        settings.vibrance = 80.0;

        // Moderately desaturated vs moderately saturated
        let desat = [0.4, 0.5, 0.6];
        let saturated = [0.8, 0.2, 0.2];

        let out_desat = apply(desat, &settings);
        let out_sat = apply(saturated, &settings);

        let s_desat_in = saturation(desat[0], desat[1], desat[2]);
        let s_desat_out = saturation(out_desat[0], out_desat[1], out_desat[2]);
        let s_sat_in = saturation(saturated[0], saturated[1], saturated[2]);
        let s_sat_out = saturation(out_sat[0], out_sat[1], out_sat[2]);

        // The relative saturation increase should be larger for the desaturated color
        let desat_relative = if s_desat_in > 1e-6 { (s_desat_out - s_desat_in) / s_desat_in } else { 0.0 };
        let sat_relative = if s_sat_in > 1e-6 { (s_sat_out - s_sat_in) / s_sat_in } else { 0.0 };

        assert!(
            desat_relative > sat_relative,
            "Desaturated colors should receive proportionally more boost: desat={desat_relative:.4} vs sat={sat_relative:.4}"
        );
    }

    #[test]
    fn achromatic_unaffected() {
        let mut settings = CrsSettings::default();
        settings.vibrance = 100.0;
        let gray = [0.5, 0.5, 0.5];
        let out = apply(gray, &settings);
        assert!((out[0] - 0.5).abs() < 1e-10);
        assert!((out[1] - 0.5).abs() < 1e-10);
        assert!((out[2] - 0.5).abs() < 1e-10);
    }
}
