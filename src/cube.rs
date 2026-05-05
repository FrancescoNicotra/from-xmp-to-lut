use std::fmt::Write as FmtWrite;
use std::fs;
use std::io;
use std::path::Path;

use crate::identity::Lut3D;

/// Write a 3D LUT to a string in Adobe .cube format (spec v1.0).
///
/// Format:
/// - Header lines: TITLE, LUT_3D_SIZE, DOMAIN_MIN, DOMAIN_MAX
/// - Data lines: one RGB triplet per line, 6 decimal places, space-separated
/// - Ordering: R changes fastest, then G, then B
pub fn write_cube_string(lut: &Lut3D, title: &str) -> String {
    let total = lut.size * lut.size * lut.size;
    // Pre-allocate: ~30 chars per line + header
    let mut buf = String::with_capacity(total * 30 + 200);

    writeln!(buf, "TITLE \"{}\"", title).unwrap();
    writeln!(buf, "LUT_3D_SIZE {}", lut.size).unwrap();
    writeln!(buf, "DOMAIN_MIN 0.0 0.0 0.0").unwrap();
    writeln!(buf, "DOMAIN_MAX 1.0 1.0 1.0").unwrap();
    writeln!(buf).unwrap();

    for sample in &lut.data {
        writeln!(buf, "{:.6} {:.6} {:.6}", sample.r, sample.g, sample.b).unwrap();
    }

    buf
}

/// Write a 3D LUT to a .cube file on disk.
pub fn write_cube_file(lut: &Lut3D, title: &str, path: &Path) -> io::Result<()> {
    let content = write_cube_string(lut, title);
    fs::write(path, content)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cube_header_format() {
        let lut = Lut3D::identity(2);
        let output = write_cube_string(&lut, "Test LUT");
        let lines: Vec<&str> = output.lines().collect();

        assert_eq!(lines[0], "TITLE \"Test LUT\"");
        assert_eq!(lines[1], "LUT_3D_SIZE 2");
        assert_eq!(lines[2], "DOMAIN_MIN 0.0 0.0 0.0");
        assert_eq!(lines[3], "DOMAIN_MAX 1.0 1.0 1.0");
        assert_eq!(lines[4], ""); // blank separator
    }

    #[test]
    fn cube_data_line_count() {
        let lut = Lut3D::identity(4);
        let output = write_cube_string(&lut, "Test");
        let lines: Vec<&str> = output.lines().collect();
        // 5 header lines (TITLE, SIZE, DOMAIN_MIN, DOMAIN_MAX, blank) + 64 data lines
        assert_eq!(lines.len(), 5 + 64);
    }

    #[test]
    fn cube_identity_first_and_last_sample() {
        let lut = Lut3D::identity(4);
        let output = write_cube_string(&lut, "Identity");
        let lines: Vec<&str> = output.lines().collect();

        // First data line: (0,0,0) → 0.000000 0.000000 0.000000
        assert_eq!(lines[5], "0.000000 0.000000 0.000000");
        // Last data line: (3,3,3) → 1.000000 1.000000 1.000000
        assert_eq!(lines[5 + 63], "1.000000 1.000000 1.000000");
    }

    #[test]
    fn cube_six_decimal_places() {
        let lut = Lut3D::identity(4);
        let output = write_cube_string(&lut, "Precision");
        let lines: Vec<&str> = output.lines().collect();

        // Sample at (1,0,0): r=1/3, g=0, b=0
        assert_eq!(lines[5 + 1], "0.333333 0.000000 0.000000");
    }

    #[test]
    fn cube_r_changes_fastest() {
        let lut = Lut3D::identity(3);
        let output = write_cube_string(&lut, "Order");
        let lines: Vec<&str> = output.lines().collect();

        // b=0, g=0: r sweeps 0, 0.5, 1.0
        assert_eq!(lines[5], "0.000000 0.000000 0.000000");
        assert_eq!(lines[6], "0.500000 0.000000 0.000000");
        assert_eq!(lines[7], "1.000000 0.000000 0.000000");
        // b=0, g=1: r sweeps again
        assert_eq!(lines[8], "0.000000 0.500000 0.000000");
        assert_eq!(lines[9], "0.500000 0.500000 0.000000");
        assert_eq!(lines[10], "1.000000 0.500000 0.000000");
    }

    #[test]
    fn cube_write_file_roundtrip() {
        let lut = Lut3D::identity(2);
        let dir = std::env::temp_dir();
        let path = dir.join("test_lut.cube");

        write_cube_file(&lut, "Roundtrip", &path).unwrap();

        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.starts_with("TITLE \"Roundtrip\""));
        assert!(content.contains("LUT_3D_SIZE 2"));

        std::fs::remove_file(&path).ok();
    }
}
