use pyo3::prelude::*;

/// A single tone curve control point (x, y) in 0..255 range.
#[pyclass]
#[derive(Clone, Debug, Default)]
pub struct ToneCurvePoint {
    #[pyo3(get, set)]
    pub x: f64,
    #[pyo3(get, set)]
    pub y: f64,
}

#[pymethods]
impl ToneCurvePoint {
    #[new]
    fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }
}

/// All Camera Raw Settings relevant to LUT generation (Process Version 2012+).
///
/// Field names match the XMP `crs:` property names, converted to snake_case.
/// Default values represent "no adjustment" (identity transform).
#[pyclass]
#[derive(Clone, Debug)]
pub struct CrsSettings {
    // -- Process Version --
    #[pyo3(get, set)]
    pub process_version: String,

    // -- White Balance --
    #[pyo3(get, set)]
    pub temperature: f64,
    #[pyo3(get, set)]
    pub tint: f64,

    // -- Basic Adjustments (PV2012) --
    #[pyo3(get, set)]
    pub exposure_2012: f64,
    #[pyo3(get, set)]
    pub contrast_2012: f64,
    #[pyo3(get, set)]
    pub highlights_2012: f64,
    #[pyo3(get, set)]
    pub shadows_2012: f64,
    #[pyo3(get, set)]
    pub whites_2012: f64,
    #[pyo3(get, set)]
    pub blacks_2012: f64,
    #[pyo3(get, set)]
    pub clarity_2012: f64,

    // -- Color --
    #[pyo3(get, set)]
    pub saturation: f64,
    #[pyo3(get, set)]
    pub vibrance: f64,

    // -- Tone Curves (Vec of ToneCurvePoint) --
    #[pyo3(get, set)]
    pub tone_curve_pv2012: Vec<ToneCurvePoint>,
    #[pyo3(get, set)]
    pub tone_curve_pv2012_red: Vec<ToneCurvePoint>,
    #[pyo3(get, set)]
    pub tone_curve_pv2012_green: Vec<ToneCurvePoint>,
    #[pyo3(get, set)]
    pub tone_curve_pv2012_blue: Vec<ToneCurvePoint>,

    // -- HSL Adjustments (8 color ranges) --
    #[pyo3(get, set)]
    pub hue_adjustment_red: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_orange: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_yellow: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_green: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_aqua: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_blue: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_purple: f64,
    #[pyo3(get, set)]
    pub hue_adjustment_magenta: f64,

    #[pyo3(get, set)]
    pub saturation_adjustment_red: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_orange: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_yellow: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_green: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_aqua: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_blue: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_purple: f64,
    #[pyo3(get, set)]
    pub saturation_adjustment_magenta: f64,

    #[pyo3(get, set)]
    pub luminance_adjustment_red: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_orange: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_yellow: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_green: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_aqua: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_blue: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_purple: f64,
    #[pyo3(get, set)]
    pub luminance_adjustment_magenta: f64,

    // -- Split Toning --
    #[pyo3(get, set)]
    pub split_toning_shadow_hue: f64,
    #[pyo3(get, set)]
    pub split_toning_shadow_saturation: f64,
    #[pyo3(get, set)]
    pub split_toning_highlight_hue: f64,
    #[pyo3(get, set)]
    pub split_toning_highlight_saturation: f64,
    #[pyo3(get, set)]
    pub split_toning_balance: f64,
}

impl Default for CrsSettings {
    fn default() -> Self {
        let linear_curve = vec![
            ToneCurvePoint { x: 0.0, y: 0.0 },
            ToneCurvePoint { x: 255.0, y: 255.0 },
        ];
        Self {
            process_version: "11.0".to_string(),
            temperature: 6500.0,
            tint: 0.0,
            exposure_2012: 0.0,
            contrast_2012: 0.0,
            highlights_2012: 0.0,
            shadows_2012: 0.0,
            whites_2012: 0.0,
            blacks_2012: 0.0,
            clarity_2012: 0.0,
            saturation: 0.0,
            vibrance: 0.0,
            tone_curve_pv2012: linear_curve.clone(),
            tone_curve_pv2012_red: linear_curve.clone(),
            tone_curve_pv2012_green: linear_curve.clone(),
            tone_curve_pv2012_blue: linear_curve,
            hue_adjustment_red: 0.0,
            hue_adjustment_orange: 0.0,
            hue_adjustment_yellow: 0.0,
            hue_adjustment_green: 0.0,
            hue_adjustment_aqua: 0.0,
            hue_adjustment_blue: 0.0,
            hue_adjustment_purple: 0.0,
            hue_adjustment_magenta: 0.0,
            saturation_adjustment_red: 0.0,
            saturation_adjustment_orange: 0.0,
            saturation_adjustment_yellow: 0.0,
            saturation_adjustment_green: 0.0,
            saturation_adjustment_aqua: 0.0,
            saturation_adjustment_blue: 0.0,
            saturation_adjustment_purple: 0.0,
            saturation_adjustment_magenta: 0.0,
            luminance_adjustment_red: 0.0,
            luminance_adjustment_orange: 0.0,
            luminance_adjustment_yellow: 0.0,
            luminance_adjustment_green: 0.0,
            luminance_adjustment_aqua: 0.0,
            luminance_adjustment_blue: 0.0,
            luminance_adjustment_purple: 0.0,
            luminance_adjustment_magenta: 0.0,
            split_toning_shadow_hue: 0.0,
            split_toning_shadow_saturation: 0.0,
            split_toning_highlight_hue: 0.0,
            split_toning_highlight_saturation: 0.0,
            split_toning_balance: 0.0,
        }
    }
}

#[pymethods]
impl CrsSettings {
    #[new]
    fn new() -> Self {
        Self::default()
    }
}
