use rayon::prelude::*;

/// A single RGB sample in the LUT (normalized 0.0..1.0).
#[derive(Clone, Debug)]
pub struct LutSample {
    pub r: f64,
    pub g: f64,
    pub b: f64,
}

/// A 3D LUT stored as a flat Vec of RGB samples.
///
/// The ordering follows the .cube spec: R changes fastest, then G, then B.
/// Index = ir + size * ig + size * size * ib
#[derive(Clone, Debug)]
pub struct Lut3D {
    pub size: usize,
    pub data: Vec<LutSample>,
}

impl Lut3D {
    /// Generate an identity LUT of the given grid size.
    ///
    /// Each sample maps input → output with no transformation:
    /// for indices (ir, ig, ib) in [0, size-1], the RGB value is
    /// (ir/(size-1), ig/(size-1), ib/(size-1)).
    pub fn identity(size: usize) -> Self {
        assert!(size >= 2, "LUT size must be at least 2");
        let total = size * size * size;
        let denom = (size - 1) as f64;

        let data: Vec<LutSample> = (0..total)
            .into_par_iter()
            .map(|idx| {
                let ib = idx / (size * size);
                let ig = (idx / size) % size;
                let ir = idx % size;
                LutSample {
                    r: ir as f64 / denom,
                    g: ig as f64 / denom,
                    b: ib as f64 / denom,
                }
            })
            .collect();

        Self { size, data }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_corners() {
        let lut = Lut3D::identity(4);
        assert_eq!(lut.data.len(), 64);

        // (0,0,0) → black
        let black = &lut.data[0];
        assert!((black.r).abs() < 1e-12);
        assert!((black.g).abs() < 1e-12);
        assert!((black.b).abs() < 1e-12);

        // (3,3,3) → white (index = 3 + 4*3 + 16*3 = 63)
        let white = &lut.data[63];
        assert!((white.r - 1.0).abs() < 1e-12);
        assert!((white.g - 1.0).abs() < 1e-12);
        assert!((white.b - 1.0).abs() < 1e-12);
    }

    #[test]
    fn identity_size_64() {
        let lut = Lut3D::identity(64);
        assert_eq!(lut.data.len(), 64 * 64 * 64);
    }

    #[test]
    fn identity_preserves_values() {
        let lut = Lut3D::identity(4);
        let denom = 3.0_f64;
        for ib in 0..4 {
            for ig in 0..4 {
                for ir in 0..4 {
                    let idx = ir + 4 * ig + 16 * ib;
                    let s = &lut.data[idx];
                    assert!((s.r - ir as f64 / denom).abs() < 1e-12);
                    assert!((s.g - ig as f64 / denom).abs() < 1e-12);
                    assert!((s.b - ib as f64 / denom).abs() < 1e-12);
                }
            }
        }
    }
}
