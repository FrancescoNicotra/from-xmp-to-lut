"""XMP-to-LUT: Convert Adobe Camera Raw XMP presets to .cube 3D LUT files."""

from xmp_to_lut.model import CrsSettings
from xmp_to_lut.parser import parse_xmp

__all__ = ["CrsSettings", "parse_xmp", "to_rust_settings"]


def to_rust_settings(py_settings: CrsSettings) -> object:
    """Convert a Python CrsSettings dataclass to the Rust _core.CrsSettings.

    The Rust engine requires its own PyO3-backed CrsSettings type.
    This copies all fields from the Python dataclass into the Rust struct.
    """
    from xmp_to_lut._core import CrsSettings as RustCrsSettings
    from xmp_to_lut._core import ToneCurvePoint as RustTCP

    rs = RustCrsSettings()

    rs.process_version = py_settings.process_version
    rs.temperature = py_settings.temperature
    rs.tint = py_settings.tint
    rs.exposure_2012 = py_settings.exposure_2012
    rs.contrast_2012 = py_settings.contrast_2012
    rs.highlights_2012 = py_settings.highlights_2012
    rs.shadows_2012 = py_settings.shadows_2012
    rs.whites_2012 = py_settings.whites_2012
    rs.blacks_2012 = py_settings.blacks_2012
    rs.clarity_2012 = py_settings.clarity_2012
    rs.saturation = py_settings.saturation
    rs.vibrance = py_settings.vibrance

    def convert_curve(points: list) -> list:
        return [RustTCP(p.x, p.y) for p in points]

    rs.tone_curve_pv2012 = convert_curve(py_settings.tone_curve_pv2012)
    rs.tone_curve_pv2012_red = convert_curve(py_settings.tone_curve_pv2012_red)
    rs.tone_curve_pv2012_green = convert_curve(py_settings.tone_curve_pv2012_green)
    rs.tone_curve_pv2012_blue = convert_curve(py_settings.tone_curve_pv2012_blue)

    for color in (
        "red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta",
    ):
        for axis in ("hue_adjustment", "saturation_adjustment", "luminance_adjustment"):
            field = f"{axis}_{color}"
            setattr(rs, field, getattr(py_settings, field))

    rs.split_toning_shadow_hue = py_settings.split_toning_shadow_hue
    rs.split_toning_shadow_saturation = py_settings.split_toning_shadow_saturation
    rs.split_toning_highlight_hue = py_settings.split_toning_highlight_hue
    rs.split_toning_highlight_saturation = py_settings.split_toning_highlight_saturation
    rs.split_toning_balance = py_settings.split_toning_balance

    return rs
