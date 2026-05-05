use crate::model::CrsSettings;

/// Apply exposure adjustment as a linear gain in EV stops.
///
/// `pixel *= 2^(exposure_ev)`
///
/// Values are clamped to [0.0, 1.0] after the gain.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    let ev = settings.exposure_2012;
    if ev.abs() < 1e-10 {
        return rgb;
    }

    let gain = 2.0_f64.powf(ev);
    [
        (rgb[0] * gain).clamp(0.0, 1.0),
        (rgb[1] * gain).clamp(0.0, 1.0),
        (rgb[2] * gain).clamp(0.0, 1.0),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zero_exposure_is_identity() {
        let settings = CrsSettings::default();
        let rgb = [0.3, 0.5, 0.8];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.3).abs() < 1e-12);
        assert!((out[1] - 0.5).abs() < 1e-12);
        assert!((out[2] - 0.8).abs() < 1e-12);
    }

    #[test]
    fn one_stop_doubles() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = 1.0;
        let rgb = [0.25, 0.25, 0.25];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.5).abs() < 1e-12);
        assert!((out[1] - 0.5).abs() < 1e-12);
        assert!((out[2] - 0.5).abs() < 1e-12);
    }

    #[test]
    fn clamps_to_one() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = 3.0;
        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        assert!((out[0] - 1.0).abs() < 1e-12);
    }

    #[test]
    fn negative_exposure_darkens() {
        let mut settings = CrsSettings::default();
        settings.exposure_2012 = -1.0;
        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.25).abs() < 1e-12);
    }
}
