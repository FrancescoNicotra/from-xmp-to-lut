use pyo3::prelude::*;
use std::path::Path;

pub mod model;
pub mod identity;
pub mod engine;
pub mod cube;

/// Generate a processed .cube LUT from CrsSettings and write it to disk.
///
/// Arguments:
/// - settings: CrsSettings with all XMP parameters
/// - output_path: destination file path for the .cube file
/// - title: optional title string embedded in the .cube header
/// - size: LUT grid size (default 64)
#[pyfunction]
#[pyo3(signature = (settings, output_path, title="XMP-to-LUT", size=64))]
fn convert(
    settings: &model::CrsSettings,
    output_path: &str,
    title: &str,
    size: usize,
) -> PyResult<()> {
    let lut = engine::generate_lut(size, settings);
    cube::write_cube_file(&lut, title, Path::new(output_path))
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
}

/// Generate a .cube LUT string in memory (no file I/O).
#[pyfunction]
#[pyo3(signature = (settings, title="XMP-to-LUT", size=64))]
fn convert_to_string(
    settings: &model::CrsSettings,
    title: &str,
    size: usize,
) -> String {
    let lut = engine::generate_lut(size, settings);
    cube::write_cube_string(&lut, title)
}

/// Python module implemented in Rust via PyO3.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<model::CrsSettings>()?;
    m.add_class::<model::ToneCurvePoint>()?;
    m.add_function(wrap_pyfunction!(convert, m)?)?;
    m.add_function(wrap_pyfunction!(convert_to_string, m)?)?;
    Ok(())
}
