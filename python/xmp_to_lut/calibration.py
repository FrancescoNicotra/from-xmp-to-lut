"""Calibration pipeline: compare simulated LUT against Adobe Camera Raw reference.

Workflow:
    1. Generate a HALD identity image with ``hald.save_hald_identity()``
    2. Process it through Adobe Camera Raw (manual step) with the same XMP
    3. Generate the simulated .cube with the math engine
    4. Call ``calibrate()`` to compute correction deltas
    5. Call ``write_corrected_cube()`` to produce a corrected .cube file

The correction is additive: ``corrected[i] = simulated[i] + delta[i]``
where ``delta[i] = reference[i] - simulated[i]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xmp_to_lut.hald import LutEntry


class CalibrationError(Exception):
    """Base error for calibration pipeline failures."""


class CubeParseError(ValueError, CalibrationError):
    """Raised when a .cube file cannot be parsed or read."""


class HaldReadError(ValueError, CalibrationError):
    """Raised when the processed HALD image cannot be read."""


class LutSizeMismatchError(ValueError, CalibrationError):
    """Raised when the LUT size doesn't match the HALD level."""


class CalibrationIOError(OSError, CalibrationError):
    """Raised when writing the corrected .cube file fails."""


@dataclass
class CalibrationReport:
    """Statistics from comparing a simulated LUT against a reference."""

    lut_size: int
    total_samples: int
    mean_delta_r: float
    mean_delta_g: float
    mean_delta_b: float
    max_delta_r: float
    max_delta_g: float
    max_delta_b: float
    mean_abs_error: float
    max_abs_error: float
    rmse: float

    def summary(self) -> str:
        return (
            f"Calibration Report ({self.lut_size}³ LUT, "
            f"{self.total_samples} samples)\n"
            f"  Mean delta  (R, G, B): "
            f"({self.mean_delta_r:+.6f}, {self.mean_delta_g:+.6f}, "
            f"{self.mean_delta_b:+.6f})\n"
            f"  Max  delta  (R, G, B): "
            f"({self.max_delta_r:+.6f}, {self.max_delta_g:+.6f}, "
            f"{self.max_delta_b:+.6f})\n"
            f"  Mean absolute error:   {self.mean_abs_error:.6f}\n"
            f"  Max  absolute error:   {self.max_abs_error:.6f}\n"
            f"  RMSE:                  {self.rmse:.6f}"
        )


def parse_cube_file(path: str | Path) -> tuple[int, list[LutEntry]]:
    """Parse a .cube file and return (lut_size, entries).

    Only ``LUT_3D_SIZE`` cubes are supported.  Returns entries in the
    same order as the file (R fastest, G, B slowest).
    """
    entries: list[LutEntry] = []
    lut_size = 0

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TITLE"):
                continue
            if line.startswith("DOMAIN_MIN") or line.startswith("DOMAIN_MAX"):
                continue
            if line.startswith("LUT_3D_SIZE"):
                lut_size = int(line.split()[1])
                continue

            parts = line.split()
            if len(parts) == 3:
                try:
                    r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                    entries.append((r, g, b))
                except ValueError:
                    continue

    if lut_size == 0:
        raise ValueError(f"No LUT_3D_SIZE found in {path}")

    expected = lut_size ** 3
    if len(entries) != expected:
        raise ValueError(
            f"Expected {expected} entries for size {lut_size}, "
            f"got {len(entries)}"
        )

    return lut_size, entries


def compute_deltas(
    simulated: list[LutEntry],
    reference: list[LutEntry],
) -> list[LutEntry]:
    """Compute per-entry correction deltas: reference - simulated.

    Both lists must have the same length and ordering.
    """
    if len(simulated) != len(reference):
        raise ValueError(
            f"Length mismatch: simulated={len(simulated)}, "
            f"reference={len(reference)}"
        )

    return [
        (ref[0] - sim[0], ref[1] - sim[1], ref[2] - sim[2])
        for sim, ref in zip(simulated, reference)
    ]


def apply_deltas(
    lut: list[LutEntry],
    deltas: list[LutEntry],
) -> list[LutEntry]:
    """Apply additive correction deltas to a LUT, clamping to [0, 1]."""
    if len(lut) != len(deltas):
        raise ValueError(
            f"Length mismatch: lut={len(lut)}, deltas={len(deltas)}"
        )

    return [
        (
            max(0.0, min(1.0, entry[0] + delta[0])),
            max(0.0, min(1.0, entry[1] + delta[1])),
            max(0.0, min(1.0, entry[2] + delta[2])),
        )
        for entry, delta in zip(lut, deltas)
    ]


def build_report(
    simulated: list[LutEntry],
    reference: list[LutEntry],
    lut_size: int,
) -> CalibrationReport:
    """Compare simulated vs reference LUT and build a report."""
    deltas = compute_deltas(simulated, reference)
    n = len(deltas)

    sum_dr = sum_dg = sum_db = 0.0
    max_dr = max_dg = max_db = 0.0
    sum_abs = 0.0
    max_abs = 0.0
    sum_sq = 0.0

    for dr, dg, db in deltas:
        sum_dr += dr
        sum_dg += dg
        sum_db += db

        adr, adg, adb = abs(dr), abs(dg), abs(db)
        max_dr = max(max_dr, adr)
        max_dg = max(max_dg, adg)
        max_db = max(max_db, adb)

        # Per-sample absolute error = Euclidean distance / sqrt(3)
        # We use the simpler mean of absolute channel differences
        sample_abs = (adr + adg + adb) / 3.0
        sum_abs += sample_abs
        max_abs = max(max_abs, max(adr, adg, adb))

        sum_sq += dr * dr + dg * dg + db * db

    return CalibrationReport(
        lut_size=lut_size,
        total_samples=n,
        mean_delta_r=sum_dr / n,
        mean_delta_g=sum_dg / n,
        mean_delta_b=sum_db / n,
        max_delta_r=max_dr,
        max_delta_g=max_dg,
        max_delta_b=max_db,
        mean_abs_error=sum_abs / n,
        max_abs_error=max_abs,
        rmse=(sum_sq / (n * 3)) ** 0.5,
    )


def write_corrected_cube(
    simulated_cube_path: str | Path,
    processed_hald_path: str | Path,
    output_path: str | Path,
    level: int = 8,
    title: str = "XMP-to-LUT (calibrated)",
) -> CalibrationReport:
    """Full calibration pipeline: compare, correct, and write a new .cube.

    Args:
        simulated_cube_path: Path to the .cube generated by the math engine.
        processed_hald_path: Path to the HALD image processed by Adobe ACR.
        output_path: Destination for the corrected .cube file.
        level: HALD level (must match the identity image used).
        title: Title for the corrected .cube header.

    Returns:
        A CalibrationReport with comparison statistics.
    """
    from xmp_to_lut.hald import read_hald_lut

    try:
        lut_size, simulated = parse_cube_file(simulated_cube_path)
    except Exception as exc:
        raise CubeParseError(f"Failed to parse .cube file: {exc}") from exc

    try:
        reference = read_hald_lut(processed_hald_path, level)
    except Exception as exc:
        raise HaldReadError(f"Failed to read HALD image: {exc}") from exc

    expected_lut_size = level * level
    if lut_size != expected_lut_size:
        raise LutSizeMismatchError(
            f"LUT size mismatch: .cube has size {lut_size}, "
            f"but HALD level {level} implies size {expected_lut_size}"
        )

    report = build_report(simulated, reference, lut_size)
    deltas = compute_deltas(simulated, reference)
    corrected = apply_deltas(simulated, deltas)

    try:
        _write_cube_entries(corrected, lut_size, title, output_path)
    except Exception as exc:
        raise CalibrationIOError(
            f"Failed to write corrected .cube file: {exc}"
        ) from exc
    return report


def _write_cube_entries(
    entries: list[LutEntry],
    lut_size: int,
    title: str,
    output_path: str | Path,
) -> None:
    """Write LUT entries to a .cube file."""
    lines = [
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {lut_size}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
        "",
    ]
    for r, g, b in entries:
        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
    lines.append("")

    Path(output_path).write_text("\n".join(lines))


def calibrate(
    simulated_cube_path: str | Path,
    processed_hald_path: str | Path,
    level: int = 8,
) -> CalibrationReport:
    """Compare a simulated .cube against a processed HALD (no output written).

    Use this to inspect the fidelity gap before deciding whether to apply
    corrections.
    """
    from xmp_to_lut.hald import read_hald_lut

    try:
        lut_size, simulated = parse_cube_file(simulated_cube_path)
    except Exception as exc:
        raise CubeParseError(f"Failed to parse .cube file: {exc}") from exc

    try:
        reference = read_hald_lut(processed_hald_path, level)
    except Exception as exc:
        raise HaldReadError(f"Failed to read HALD image: {exc}") from exc

    expected_lut_size = level * level
    if lut_size != expected_lut_size:
        raise LutSizeMismatchError(
            f"LUT size mismatch: .cube has size {lut_size}, "
            f"but HALD level {level} implies size {expected_lut_size}"
        )

    return build_report(simulated, reference, lut_size)
