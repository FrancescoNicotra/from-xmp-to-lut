"""Tests for the CLI (click subcommands)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from xmp_to_lut.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_XMP = FIXTURES / "sample_preset.xmp"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


class TestConvert:
    """Tests for the ``convert`` subcommand."""

    def test_convert_default_output(self, runner: CliRunner, tmp_path: Path) -> None:
        xmp_copy = tmp_path / "preset.xmp"
        xmp_copy.write_text(SAMPLE_XMP.read_text())

        result = runner.invoke(main, ["convert", str(xmp_copy)])

        assert result.exit_code == 0, result.output
        cube_file = tmp_path / "preset.cube"
        assert cube_file.exists()
        content = cube_file.read_text()
        assert "LUT_3D_SIZE 64" in content
        assert 'TITLE "preset"' in content

    def test_convert_explicit_output(self, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "my_lut.cube"
        result = runner.invoke(main, ["convert", str(SAMPLE_XMP), "-o", str(out)])

        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_convert_custom_size(self, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "small.cube"
        result = runner.invoke(main, ["convert", str(SAMPLE_XMP), "-o", str(out), "--size", "17"])

        assert result.exit_code == 0, result.output
        content = out.read_text()
        assert "LUT_3D_SIZE 17" in content
        assert "17³" in result.output

    def test_convert_custom_title(self, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "titled.cube"
        result = runner.invoke(
            main, ["convert", str(SAMPLE_XMP), "-o", str(out), "--title", "My Preset"]
        )

        assert result.exit_code == 0, result.output
        content = out.read_text()
        assert 'TITLE "My Preset"' in content

    def test_convert_nonexistent_file(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["convert", "/nonexistent/file.xmp"])
        assert result.exit_code != 0

    def test_convert_invalid_xmp(self, runner: CliRunner, tmp_path: Path) -> None:
        bad_xmp = tmp_path / "bad.xmp"
        bad_xmp.write_text("this is not XML")
        result = runner.invoke(main, ["convert", str(bad_xmp)])
        assert result.exit_code != 0
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


class TestInspect:
    """Tests for the ``inspect`` subcommand."""

    def test_inspect_shows_modified(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["inspect", str(SAMPLE_XMP)])
        assert result.exit_code == 0, result.output
        assert "Summary:" in result.output
        assert "Modified fields:" in result.output
        assert "exposure_2012: 0.5" in result.output

    def test_inspect_shows_defaults(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["inspect", str(SAMPLE_XMP)])
        assert result.exit_code == 0
        assert "Unchanged fields:" in result.output

    def test_inspect_shows_temperature(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["inspect", str(SAMPLE_XMP)])
        assert result.exit_code == 0
        assert "temperature: 5500" in result.output

    def test_inspect_warnings(self, runner: CliRunner, tmp_path: Path) -> None:
        warn_xmp = tmp_path / "warn.xmp"
        xml = SAMPLE_XMP.read_text()
        xml = xml.replace(
            "crs:ProcessVersion=\"11.0\"",
            "crs:ProcessVersion=\"11.0\" crs:UnsupportedFoo=\"1\"",
        )
        warn_xmp.write_text(xml)

        result = runner.invoke(main, ["inspect", str(warn_xmp)])

        assert result.exit_code == 0, result.output
        assert "Warnings:" in result.output
        assert "Unsupported crs: attributes: UnsupportedFoo" in result.output

    def test_inspect_nonexistent_file(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["inspect", "/nonexistent/file.xmp"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


class TestBatch:
    """Tests for the ``batch`` subcommand."""

    def test_batch_converts_all(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "presets"
        src.mkdir()
        out = tmp_path / "luts"

        for name in ("a.xmp", "b.xmp"):
            (src / name).write_text(SAMPLE_XMP.read_text())

        result = runner.invoke(main, ["batch", str(src), "-o", str(out)])

        assert result.exit_code == 0, result.output
        assert (out / "a.cube").exists()
        assert (out / "b.cube").exists()
        assert "2 converted" in result.output
        assert "Failures: parse=0" in result.output

    def test_batch_default_output_dir(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "test.xmp").write_text(SAMPLE_XMP.read_text())
        result = runner.invoke(main, ["batch", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert (tmp_path / "test.cube").exists()

    def test_batch_empty_dir(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(main, ["batch", str(tmp_path)])
        assert result.exit_code != 0
        assert "No .xmp files" in result.output

    def test_batch_reports_failures(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "mixed"
        src.mkdir()
        (src / "good.xmp").write_text(SAMPLE_XMP.read_text())
        (src / "bad.xmp").write_text("not xml at all")

        result = runner.invoke(main, ["batch", str(src)])

        assert result.exit_code == 1
        assert "1 converted" in result.output
        assert "1 failed" in result.output
        assert "Failures: parse=1" in result.output

    def test_batch_custom_size(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "x.xmp").write_text(SAMPLE_XMP.read_text())
        out = tmp_path / "out"
        result = runner.invoke(main, ["batch", str(tmp_path), "-o", str(out), "--size", "17"])

        assert result.exit_code == 0, result.output
        content = (out / "x.cube").read_text()
        assert "LUT_3D_SIZE 17" in content


# ---------------------------------------------------------------------------
# calibrate
# ---------------------------------------------------------------------------


def _write_identity_cube(path: Path, lut_size: int) -> None:
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
    path.write_text("\n".join(lines) + "\n")


class TestCalibrate:
    """Tests for the ``calibrate`` subcommand."""

    def test_calibrate_report_only(self, runner: CliRunner, tmp_path: Path) -> None:
        from xmp_to_lut.hald import save_hald_identity

        cube_path = tmp_path / "simulated.cube"
        _write_identity_cube(cube_path, lut_size=4)

        hald_path = tmp_path / "reference.png"
        save_hald_identity(hald_path, level=2, bit_depth=8)

        result = runner.invoke(
            main, ["calibrate", str(cube_path), str(hald_path), "--level", "2"]
        )

        assert result.exit_code == 0, result.output
        assert "Calibration Report" in result.output
        assert "RMSE" in result.output
        assert "Written" not in result.output

    def test_calibrate_writes_output(self, runner: CliRunner, tmp_path: Path) -> None:
        from xmp_to_lut.hald import save_hald_identity

        cube_path = tmp_path / "simulated.cube"
        _write_identity_cube(cube_path, lut_size=4)

        hald_path = tmp_path / "reference.png"
        save_hald_identity(hald_path, level=2, bit_depth=8)

        output_path = tmp_path / "corrected.cube"
        result = runner.invoke(
            main,
            [
                "calibrate",
                str(cube_path),
                str(hald_path),
                "--level",
                "2",
                "-o",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output
        assert output_path.exists()
        assert "Written" in result.output


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


class TestMainGroup:
    """Tests for the top-level CLI group."""

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "convert" in result.output
        assert "inspect" in result.output
        assert "calibrate" in result.output
        assert "batch" in result.output

    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Usage" in result.output
