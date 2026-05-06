"""CLI entry point for xmp-to-lut.

Subcommands:
  convert  -- Parse an XMP preset and generate a .cube 3D LUT file.
  inspect  -- Parse an XMP preset and print the extracted settings.
    calibrate -- Compare a simulated .cube with a processed HALD image.
  batch    -- Convert all .xmp files in a directory to .cube files.
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

import click

from xmp_to_lut.model import CrsSettings, ToneCurvePoint
from xmp_to_lut.parser import XmpParseError, parse_xmp, parse_xmp_with_warnings


@click.group(invoke_without_command=True)
@click.version_option(package_name="xmp-to-lut")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Convert Adobe Camera Raw XMP presets to .cube 3D LUT files."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("xmp_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output .cube file path. Defaults to <input_stem>.cube in the same directory.",
)
@click.option("--size", type=int, default=64, show_default=True, help="LUT grid size (N×N×N).")
@click.option("--title", type=str, default=None, help="Title embedded in the .cube header.")
def convert(xmp_file: Path, output: Path | None, size: int, title: str | None) -> None:
    """Parse an XMP preset and generate a .cube 3D LUT file."""
    from xmp_to_lut import to_rust_settings
    from xmp_to_lut._core import convert as rust_convert

    if output is None:
        output = xmp_file.with_suffix(".cube")
    if title is None:
        title = xmp_file.stem

    try:
        settings = parse_xmp(xmp_file)
    except XmpParseError as exc:
        raise click.ClickException(str(exc)) from exc

    rs = to_rust_settings(settings)

    try:
        rust_convert(rs, str(output), title, size)
    except Exception as exc:
        raise click.ClickException(f"Engine error: {exc}") from exc

    click.echo(f"Written {output}  ({size}³ = {size**3} samples)")


@main.command()
@click.argument("xmp_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def inspect(xmp_file: Path) -> None:
    """Parse an XMP preset and print the extracted settings."""
    try:
        settings, warnings = parse_xmp_with_warnings(xmp_file)
    except XmpParseError as exc:
        raise click.ClickException(str(exc)) from exc

    _print_settings(settings, warnings)


@main.command()
@click.argument(
    "simulated_cube",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "processed_hald",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--level",
    type=int,
    default=8,
    show_default=True,
    help="HALD level used to generate the identity image.",
)
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output .cube file path for the corrected LUT.",
)
@click.option(
    "--title",
    type=str,
    default=None,
    help="Title embedded in the corrected .cube header.",
)
def calibrate(
    simulated_cube: Path,
    processed_hald: Path,
    level: int,
    output: Path | None,
    title: str | None,
) -> None:
    """Compare a simulated .cube against a processed HALD image."""
    from xmp_to_lut.calibration import (
        CalibrationError,
        CalibrationIOError,
        CubeParseError,
        HaldReadError,
        LutSizeMismatchError,
        calibrate as run_calibrate,
        write_corrected_cube,
    )

    try:
        if output is None:
            report = run_calibrate(simulated_cube, processed_hald, level)
        else:
            if title is None:
                title = f"{simulated_cube.stem} (calibrated)"
            report = write_corrected_cube(
                simulated_cube, processed_hald, output, level, title
            )
    except (CubeParseError, HaldReadError, LutSizeMismatchError) as exc:
        raise click.ClickException(str(exc)) from exc
    except CalibrationIOError as exc:
        raise click.ClickException(str(exc)) from exc
    except ImportError as exc:
        raise click.ClickException(str(exc)) from exc
    except CalibrationError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(report.summary())
    if output is not None:
        click.echo(f"Written {output}")


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory for .cube files. Defaults to the input directory.",
)
@click.option("--size", type=int, default=64, show_default=True, help="LUT grid size (N×N×N).")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show warnings and detailed errors for failures.",
)
def batch(input_dir: Path, output_dir: Path | None, size: int, verbose: bool) -> None:
    """Convert all .xmp files in a directory to .cube files."""
    from xmp_to_lut import to_rust_settings
    from xmp_to_lut._core import convert as rust_convert

    if output_dir is None:
        output_dir = input_dir
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise click.ClickException(f"Cannot create output directory: {exc}") from exc

    xmp_files = sorted(input_dir.glob("*.xmp"))
    if not xmp_files:
        raise click.ClickException(f"No .xmp files found in {input_dir}")

    ok = 0
    failed = 0
    failures = {"parse": 0, "engine": 0, "io": 0}
    for xmp_path in xmp_files:
        cube_path = output_dir / xmp_path.with_suffix(".cube").name
        title = xmp_path.stem

        try:
            settings, warnings = parse_xmp_with_warnings(xmp_path)
            rs = to_rust_settings(settings)
            rust_convert(rs, str(cube_path), title, size)
            click.echo(f"  OK  {xmp_path.name} -> {cube_path.name}")
            ok += 1

            if verbose and warnings:
                for warning in warnings:
                    click.echo(f"      WARN: {warning}")
        except XmpParseError as exc:
            failures["parse"] += 1
            failed += 1
            click.echo(f"  FAIL  {xmp_path.name} [parse]", err=True)
            if verbose:
                click.echo(f"        {exc}", err=True)
        except OSError as exc:
            failures["io"] += 1
            failed += 1
            click.echo(f"  FAIL  {xmp_path.name} [io]", err=True)
            if verbose:
                click.echo(f"        {exc}", err=True)
        except Exception as exc:
            failures["engine"] += 1
            failed += 1
            click.echo(f"  FAIL  {xmp_path.name} [engine]", err=True)
            if verbose:
                click.echo(f"        {exc}", err=True)

    click.echo(f"\nDone: {ok} converted, {failed} failed out of {len(xmp_files)} files.")
    click.echo(
        "Failures: "
        f"parse={failures['parse']}, "
        f"engine={failures['engine']}, "
        f"io={failures['io']}"
    )
    if failed:
        sys.exit(1)


def _print_settings(settings: CrsSettings, warnings: list[str]) -> None:
    """Pretty-print a CrsSettings dataclass with grouped sections."""
    defaults = CrsSettings()
    field_info: dict[str, tuple[str, bool]] = {}
    modified_count = 0
    unchanged_count = 0
    non_linear_curves: list[str] = []

    for f in fields(settings):
        value = getattr(settings, f.name)
        default = getattr(defaults, f.name)

        if _is_curve_field(f.name):
            formatted = _format_curve(value)
            is_modified = not _curve_equals(value, default)
            if is_modified and not _is_linear_curve(value):
                non_linear_curves.append(f.name)
        else:
            formatted = f"{value}"
            is_modified = value != default

        field_info[f.name] = (formatted, is_modified)
        if is_modified:
            modified_count += 1
        else:
            unchanged_count += 1

    click.echo("Summary:")
    click.echo(f"  Modified fields: {modified_count}")
    click.echo(f"  Unchanged fields: {unchanged_count}")
    if non_linear_curves:
        click.echo("  Non-linear tone curves: " + ", ".join(non_linear_curves))
    else:
        click.echo("  Non-linear tone curves: none")

    for section, names in _SETTING_SECTIONS:
        click.echo(f"\n{section}:")
        modified_lines: list[str] = []
        unchanged_lines: list[str] = []

        for name in names:
            formatted, is_modified = field_info[name]
            line = f"    {name}: {formatted}"
            if _is_curve_field(name) and name in non_linear_curves:
                line += " (non-linear)"
            if is_modified:
                modified_lines.append(line)
            else:
                unchanged_lines.append(line)

        if modified_lines:
            click.echo("  Modified:")
            for line in modified_lines:
                click.echo(line)

        if unchanged_lines:
            click.echo("  Unchanged:")
            for line in unchanged_lines:
                click.echo(line)

    if warnings:
        click.echo("\nWarnings:")
        for warning in warnings:
            click.echo(f"  {warning}")


def _is_curve_field(name: str) -> bool:
    return name.startswith("tone_curve_pv2012")


def _format_curve(points: list[ToneCurvePoint]) -> str:
    return "[" + ", ".join(f"({p.x:.0f}, {p.y:.0f})" for p in points) + "]"


def _curve_equals(left: list[ToneCurvePoint], right: list[ToneCurvePoint]) -> bool:
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a.x != b.x or a.y != b.y:
            return False
    return True


def _is_linear_curve(points: list[ToneCurvePoint]) -> bool:
    if len(points) != 2:
        return False
    return (
        points[0].x == 0.0
        and points[0].y == 0.0
        and points[1].x == 255.0
        and points[1].y == 255.0
    )


_SETTING_SECTIONS = [
    (
        "Process version",
        [
            "process_version",
        ],
    ),
    (
        "White balance",
        [
            "temperature",
            "tint",
        ],
    ),
    (
        "Basic adjustments",
        [
            "exposure_2012",
            "contrast_2012",
            "highlights_2012",
            "shadows_2012",
            "whites_2012",
            "blacks_2012",
            "clarity_2012",
        ],
    ),
    (
        "Color",
        [
            "saturation",
            "vibrance",
        ],
    ),
    (
        "Tone curves",
        [
            "tone_curve_pv2012",
            "tone_curve_pv2012_red",
            "tone_curve_pv2012_green",
            "tone_curve_pv2012_blue",
        ],
    ),
    (
        "HSL",
        [
            "hue_adjustment_red",
            "hue_adjustment_orange",
            "hue_adjustment_yellow",
            "hue_adjustment_green",
            "hue_adjustment_aqua",
            "hue_adjustment_blue",
            "hue_adjustment_purple",
            "hue_adjustment_magenta",
            "saturation_adjustment_red",
            "saturation_adjustment_orange",
            "saturation_adjustment_yellow",
            "saturation_adjustment_green",
            "saturation_adjustment_aqua",
            "saturation_adjustment_blue",
            "saturation_adjustment_purple",
            "saturation_adjustment_magenta",
            "luminance_adjustment_red",
            "luminance_adjustment_orange",
            "luminance_adjustment_yellow",
            "luminance_adjustment_green",
            "luminance_adjustment_aqua",
            "luminance_adjustment_blue",
            "luminance_adjustment_purple",
            "luminance_adjustment_magenta",
        ],
    ),
    (
        "Split toning",
        [
            "split_toning_shadow_hue",
            "split_toning_shadow_saturation",
            "split_toning_highlight_hue",
            "split_toning_highlight_saturation",
            "split_toning_balance",
        ],
    ),
]
