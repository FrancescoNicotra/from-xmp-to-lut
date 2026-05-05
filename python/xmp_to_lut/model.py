"""Pure-Python CrsSettings dataclass.

Used during parsing before the Rust native module is available.
Maps 1:1 to the Rust CrsSettings struct exposed via PyO3.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToneCurvePoint:
    """A single tone curve control point (x, y) in 0..255 range."""

    x: float
    y: float


def _default_linear_curve() -> list[ToneCurvePoint]:
    return [ToneCurvePoint(0.0, 0.0), ToneCurvePoint(255.0, 255.0)]


@dataclass
class CrsSettings:
    """All Camera Raw Settings relevant to LUT generation (Process Version 2012+).

    Field names use snake_case and correspond to XMP ``crs:`` properties.
    Default values represent "no adjustment" (identity transform).
    """

    # -- Process Version --
    process_version: str = "11.0"

    # -- White Balance --
    temperature: float = 6500.0
    tint: float = 0.0

    # -- Basic Adjustments (PV2012) --
    exposure_2012: float = 0.0
    contrast_2012: float = 0.0
    highlights_2012: float = 0.0
    shadows_2012: float = 0.0
    whites_2012: float = 0.0
    blacks_2012: float = 0.0
    clarity_2012: float = 0.0

    # -- Color --
    saturation: float = 0.0
    vibrance: float = 0.0

    # -- Tone Curves --
    tone_curve_pv2012: list[ToneCurvePoint] = field(
        default_factory=_default_linear_curve
    )
    tone_curve_pv2012_red: list[ToneCurvePoint] = field(
        default_factory=_default_linear_curve
    )
    tone_curve_pv2012_green: list[ToneCurvePoint] = field(
        default_factory=_default_linear_curve
    )
    tone_curve_pv2012_blue: list[ToneCurvePoint] = field(
        default_factory=_default_linear_curve
    )

    # -- HSL Hue Adjustments --
    hue_adjustment_red: float = 0.0
    hue_adjustment_orange: float = 0.0
    hue_adjustment_yellow: float = 0.0
    hue_adjustment_green: float = 0.0
    hue_adjustment_aqua: float = 0.0
    hue_adjustment_blue: float = 0.0
    hue_adjustment_purple: float = 0.0
    hue_adjustment_magenta: float = 0.0

    # -- HSL Saturation Adjustments --
    saturation_adjustment_red: float = 0.0
    saturation_adjustment_orange: float = 0.0
    saturation_adjustment_yellow: float = 0.0
    saturation_adjustment_green: float = 0.0
    saturation_adjustment_aqua: float = 0.0
    saturation_adjustment_blue: float = 0.0
    saturation_adjustment_purple: float = 0.0
    saturation_adjustment_magenta: float = 0.0

    # -- HSL Luminance Adjustments --
    luminance_adjustment_red: float = 0.0
    luminance_adjustment_orange: float = 0.0
    luminance_adjustment_yellow: float = 0.0
    luminance_adjustment_green: float = 0.0
    luminance_adjustment_aqua: float = 0.0
    luminance_adjustment_blue: float = 0.0
    luminance_adjustment_purple: float = 0.0
    luminance_adjustment_magenta: float = 0.0

    # -- Split Toning --
    split_toning_shadow_hue: float = 0.0
    split_toning_shadow_saturation: float = 0.0
    split_toning_highlight_hue: float = 0.0
    split_toning_highlight_saturation: float = 0.0
    split_toning_balance: float = 0.0
