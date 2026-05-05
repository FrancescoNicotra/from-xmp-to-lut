"""Tests for the calibration pipeline."""

import tempfile
from pathlib import Path

import pytest

from xmp_to_lut.calibration import (
    CalibrationReport,
    apply_deltas,
    build_report,
    compute_deltas,
    parse_cube_file,
    write_corrected_cube,
)


SAMPLE_CUBE = """\
TITLE "Test"
LUT_3D_SIZE 2
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0

0.000000 0.000000 0.000000
1.000000 0.000000 0.000000
0.000000 1.000000 0.000000
1.000000 1.000000 0.000000
0.000000 0.000000 1.000000
1.000000 0.000000 1.000000
0.000000 1.000000 1.000000
1.000000 1.000000 1.000000
"""


class TestParseCubeFile:
    def test_parse_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cube", delete=False) as f:
            f.write(SAMPLE_CUBE)
            f.flush()
            size, entries = parse_cube_file(f.name)

        assert size == 2
        assert len(entries) == 8
        assert entries[0] == (0.0, 0.0, 0.0)
        assert entries[7] == (1.0, 1.0, 1.0)

    def test_parse_with_comments(self):
        cube_with_comments = "# Comment line\n" + SAMPLE_CUBE
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cube", delete=False) as f:
            f.write(cube_with_comments)
            f.flush()
            size, entries = parse_cube_file(f.name)
        assert size == 2

    def test_missing_size_raises(self):
        bad_cube = "0.0 0.0 0.0\n1.0 1.0 1.0\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cube", delete=False) as f:
            f.write(bad_cube)
            f.flush()
            with pytest.raises(ValueError, match="No LUT_3D_SIZE"):
                parse_cube_file(f.name)


class TestComputeDeltas:
    def test_identical_luts_zero_deltas(self):
        lut = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
        deltas = compute_deltas(lut, lut)
        for d in deltas:
            assert d == (0.0, 0.0, 0.0)

    def test_known_deltas(self):
        simulated = [(0.5, 0.5, 0.5)]
        reference = [(0.6, 0.4, 0.55)]
        deltas = compute_deltas(simulated, reference)
        assert deltas[0] == pytest.approx((0.1, -0.1, 0.05))

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            compute_deltas([(0.0, 0.0, 0.0)], [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)])


class TestApplyDeltas:
    def test_additive_correction(self):
        lut = [(0.5, 0.5, 0.5)]
        deltas = [(0.1, -0.1, 0.0)]
        result = apply_deltas(lut, deltas)
        assert result[0] == pytest.approx((0.6, 0.4, 0.5))

    def test_clamps_to_valid_range(self):
        lut = [(0.9, 0.1, 0.5)]
        deltas = [(0.2, -0.2, 0.0)]
        result = apply_deltas(lut, deltas)
        assert result[0] == (1.0, 0.0, 0.5)


class TestBuildReport:
    def test_perfect_match(self):
        lut = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (1.0, 1.0, 1.0)]
        report = build_report(lut, lut, lut_size=2)
        assert report.mean_abs_error == 0.0
        assert report.max_abs_error == 0.0
        assert report.rmse == 0.0

    def test_known_error(self):
        simulated = [(0.5, 0.5, 0.5)]
        reference = [(0.6, 0.5, 0.5)]
        report = build_report(simulated, reference, lut_size=1)
        assert report.max_delta_r == pytest.approx(0.1)
        assert report.mean_delta_r == pytest.approx(0.1)
        assert report.max_delta_g == 0.0

    def test_summary_contains_key_info(self):
        lut = [(0.5, 0.5, 0.5)]
        report = build_report(lut, lut, lut_size=1)
        summary = report.summary()
        assert "RMSE" in summary
        assert "1 samples" in summary


class TestWriteCorrectedCube:
    def test_full_pipeline(self):
        """Write a .cube identity, create a matching HALD, run calibration."""
        from xmp_to_lut.hald import save_hald_identity

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # HALD level 2 → LUT size = 2² = 4, so we need a 4³ = 64 entry cube
            lut_size = 4
            lines = [
                'TITLE "Identity"',
                f"LUT_3D_SIZE {lut_size}",
                "DOMAIN_MIN 0.0 0.0 0.0",
                "DOMAIN_MAX 1.0 1.0 1.0",
                "",
            ]
            denom = lut_size - 1
            for ib in range(lut_size):
                for ig in range(lut_size):
                    for ir in range(lut_size):
                        r = ir / denom
                        g = ig / denom
                        b = ib / denom
                        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")

            cube_path = tmpdir / "simulated.cube"
            cube_path.write_text("\n".join(lines) + "\n")

            # Generate HALD identity as "processed" reference (= identity)
            hald_path = tmpdir / "reference.png"
            save_hald_identity(hald_path, level=2, bit_depth=8)

            # Calibrate — since both are identity, deltas should be ~zero
            # (small rounding differences from 8-bit quantization)
            output_path = tmpdir / "corrected.cube"
            report = write_corrected_cube(
                cube_path, hald_path, output_path, level=2
            )

            assert output_path.exists()
            assert report.lut_size == 4
            # 8-bit quantization error should be small
            assert report.max_abs_error < 0.01

            # Verify the corrected .cube is parseable
            size, entries = parse_cube_file(output_path)
            assert size == 4
            assert len(entries) == 64
