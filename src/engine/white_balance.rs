use nalgebra::Matrix3;

use crate::model::CrsSettings;

/// D50 reference white point (ICC profile connection space).
const D50_X: f64 = 0.96422;
const D50_Y: f64 = 1.00000;
const D50_Z: f64 = 0.82521;

/// Bradford cone response matrix (LMS adaptation).
#[rustfmt::skip]
const BRADFORD: Matrix3<f64> = Matrix3::new(
     0.8951,  0.2664, -0.1614,
    -0.7502,  1.7135,  0.0367,
     0.0389, -0.0685,  1.0296,
);

/// sRGB to XYZ (D65) matrix.
#[rustfmt::skip]
const SRGB_TO_XYZ: Matrix3<f64> = Matrix3::new(
    0.4124564, 0.3575761, 0.1804375,
    0.2126729, 0.7151522, 0.0721750,
    0.0193339, 0.1191920, 0.9503041,
);

/// XYZ (D65) to sRGB matrix.
#[rustfmt::skip]
const XYZ_TO_SRGB: Matrix3<f64> = Matrix3::new(
     3.2404542, -1.5371385, -0.4985314,
    -0.9692660,  1.8760108,  0.0415560,
     0.0556434, -0.2040259,  1.0572252,
);

/// Convert correlated color temperature (CCT) and tint to CIE xy chromaticity.
///
/// Uses Hernandez-Andres approximation for CCT → xy, then adjusts
/// for the tint axis (perpendicular to the Planckian locus).
fn cct_tint_to_xy(temp: f64, tint: f64) -> (f64, f64) {
    // Hernandez-Andres CCT → CIE x
    let t = temp;
    let t2 = t * t;
    let t3 = t2 * t;
    let x = if t <= 4000.0 {
        -0.2661239e9 / t3 - 0.2343589e6 / t2 + 0.8776956e3 / t + 0.179910
    } else {
        -3.0258469e9 / t3 + 2.1070379e6 / t2 + 0.2226347e3 / t + 0.240390
    };

    // CIE x → y (Hernandez-Andres)
    let x2 = x * x;
    let x3 = x2 * x;
    let y = if t <= 2222.0 {
        -1.1063814 * x3 - 1.34811020 * x2 + 2.18555832 * x - 0.20219683
    } else if t <= 4000.0 {
        -0.9549476 * x3 - 1.37418593 * x2 + 2.09137015 * x - 0.16748867
    } else {
        3.0817580 * x3 - 5.87338670 * x2 + 3.75112997 * x - 0.37001483
    };

    // Tint offset: shift perpendicular to the Planckian locus in the green-magenta direction.
    // Normalized so tint=0 → no shift, tint range roughly -150..+150.
    let tint_shift = tint / 150.0 * 0.05;
    (x, y + tint_shift)
}

/// Convert CIE xy to XYZ with Y=1.
fn xy_to_xyz(x: f64, y: f64) -> nalgebra::Vector3<f64> {
    if y.abs() < 1e-10 {
        return nalgebra::Vector3::new(0.0, 1.0, 0.0);
    }
    nalgebra::Vector3::new(x / y, 1.0, (1.0 - x - y) / y)
}

/// Compute the Bradford chromatic adaptation matrix from source white to D50.
fn bradford_adaptation(src_xyz: &nalgebra::Vector3<f64>) -> Matrix3<f64> {
    let dst_xyz = nalgebra::Vector3::new(D50_X, D50_Y, D50_Z);

    let bradford_inv = BRADFORD
        .try_inverse()
        .expect("Bradford matrix is invertible");

    let src_lms = BRADFORD * src_xyz;
    let dst_lms = BRADFORD * dst_xyz;

    let scale = Matrix3::new(
        dst_lms[0] / src_lms[0], 0.0, 0.0,
        0.0, dst_lms[1] / src_lms[1], 0.0,
        0.0, 0.0, dst_lms[2] / src_lms[2],
    );

    bradford_inv * scale * BRADFORD
}

/// Apply white balance correction to an RGB triplet.
///
/// The transform chain: sRGB → XYZ → Bradford adapt → XYZ → sRGB.
pub fn apply(rgb: [f64; 3], settings: &CrsSettings) -> [f64; 3] {
    // Default is 6500K / 0 tint — skip if no change
    if (settings.temperature - 6500.0).abs() < 0.5 && settings.tint.abs() < 0.5 {
        return rgb;
    }

    let (src_x, src_y) = cct_tint_to_xy(settings.temperature, settings.tint);
    let src_wp = xy_to_xyz(src_x, src_y);
    let adapt = bradford_adaptation(&src_wp);

    let xyz_mat = SRGB_TO_XYZ;
    let rgb_mat = XYZ_TO_SRGB;
    let combined = rgb_mat * adapt * xyz_mat;

    let v = nalgebra::Vector3::new(rgb[0], rgb[1], rgb[2]);
    let result = combined * v;

    [result[0], result[1], result[2]]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn neutral_at_default_temp() {
        let settings = CrsSettings::default();
        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        assert!((out[0] - 0.5).abs() < 1e-10);
        assert!((out[1] - 0.5).abs() < 1e-10);
        assert!((out[2] - 0.5).abs() < 1e-10);
    }

    #[test]
    fn warm_shift() {
        let mut settings = CrsSettings::default();
        settings.temperature = 3000.0;
        let rgb = [0.5, 0.5, 0.5];
        let out = apply(rgb, &settings);
        // At 3000K source, adaptation warms the image: channels shift
        // The key check is that WB actually changed something
        let changed = (out[0] - 0.5).abs() > 0.01
            || (out[1] - 0.5).abs() > 0.01
            || (out[2] - 0.5).abs() > 0.01;
        assert!(changed, "WB at 3000K should modify gray");
    }
}
