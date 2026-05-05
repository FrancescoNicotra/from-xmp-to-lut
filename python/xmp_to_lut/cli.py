"""CLI entry point for xmp-to-lut.

Subcommands:
  convert  -- Parse an XMP preset and generate a .cube 3D LUT file.
  inspect  -- Parse an XMP preset and print the extracted settings.
  batch    -- Convert all .xmp files in a directory to .cube files.
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

import click

from xmp_to_lut.model import CrsSettings, ToneCurvePoint
from xmp_to_lut.parser import XmpParseError, parse_xmp


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
        settings = parse_xmp(xmp_file)
    except XmpParseError as exc:
        raise click.ClickException(str(exc)) from exc

    _print_settings(settings)


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o", "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Output directory for .cube files. Defaults to the input directory.",
)
@click.option("--size", type=int, default=64, show_default=True, help="LUT grid size (N×N×N).")
def batch(input_dir: Path, output_dir: Path | None, size: int) -> None:
    """Convert all .xmp files in a directory to .cube files."""
    from xmp_to_lut import to_rust_settings
    from xmp_to_lut._core import convert as rust_convert

    if output_dir is None:
        output_dir = input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    xmp_files = sorted(input_dir.glob("*.xmp"))
    if not xmp_files:
        raise click.ClickException(f"No .xmp files found in {input_dir}")

    ok = 0
    failed = 0
    for xmp_path in xmp_files:
        cube_path = output_dir / xmp_path.with_suffix(".cube").name
        title = xmp_path.stem

        try:
            settings = parse_xmp(xmp_path)
            rs = to_rust_settings(settings)
            rust_convert(rs, str(cube_path), title, size)
            click.echo(f"  OK  {xmp_path.name} -> {cube_path.name}")
            ok += 1
        except (XmpParseError, Exception) as exc:
            click.echo(f"  FAIL  {xmp_path.name}: {exc}", err=True)
            failed += 1

    click.echo(f"\nDone: {ok} converted, {failed} failed out of {len(xmp_files)} files.")
    if failed:
        sys.exit(1)


def _print_settings(settings: CrsSettings) -> None:
    """Pretty-print a CrsSettings dataclass."""
    defaults = CrsSettings()
    modified: list[str] = []
    default_lines: list[str] = []

    for f in fields(settings):
        value = getattr(settings, f.name)
        default = getattr(defaults, f.name)

        if _is_curve_field(f.name):
            formatted = _format_curve(value)
            default_formatted = _format_curve(default)
            line = f"  {f.name}: {formatted}"
            if formatted != default_formatted:
                modified.append(line)
            else:
                default_lines.append(line)
        else:
            line = f"  {f.name}: {value}"
            if value != default:
                modified.append(line)
            else:
                default_lines.append(line)

    if modified:
        click.echo("Modified settings:")
        for line in modified:
            click.echo(line)

    if default_lines:
        click.echo("\nDefault (unchanged) settings:")
        for line in default_lines:
            click.echo(line)


def _is_curve_field(name: str) -> bool:
    return name.startswith("tone_curve_pv2012")


def _format_curve(points: list[ToneCurvePoint]) -> str:
    return "[" + ", ".join(f"({p.x:.0f}, {p.y:.0f})" for p in points) + "]"
