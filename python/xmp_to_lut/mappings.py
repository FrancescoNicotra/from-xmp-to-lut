"""Mapping between XMP crs: property names and CrsSettings dataclass fields.

XMP properties use PascalCase (e.g. ``Exposure2012``), while the Python/Rust
model uses snake_case (e.g. ``exposure_2012``).

Properties are split into two categories:
- SCALAR_PROPERTIES: simple numeric or string attributes on the rdf:Description element
- SEQUENCE_PROPERTIES: rdf:Seq child elements (tone curves)
"""

# XMP crs: attribute name -> (dataclass field name, type coercion)
SCALAR_PROPERTIES: dict[str, tuple[str, type]] = {
    "ProcessVersion": ("process_version", str),
    "Temperature": ("temperature", float),
    "Tint": ("tint", float),
    "Exposure2012": ("exposure_2012", float),
    "Contrast2012": ("contrast_2012", float),
    "Highlights2012": ("highlights_2012", float),
    "Shadows2012": ("shadows_2012", float),
    "Whites2012": ("whites_2012", float),
    "Blacks2012": ("blacks_2012", float),
    "Clarity2012": ("clarity_2012", float),
    "Saturation": ("saturation", float),
    "Vibrance": ("vibrance", float),
    # HSL Hue
    "HueAdjustmentRed": ("hue_adjustment_red", float),
    "HueAdjustmentOrange": ("hue_adjustment_orange", float),
    "HueAdjustmentYellow": ("hue_adjustment_yellow", float),
    "HueAdjustmentGreen": ("hue_adjustment_green", float),
    "HueAdjustmentAqua": ("hue_adjustment_aqua", float),
    "HueAdjustmentBlue": ("hue_adjustment_blue", float),
    "HueAdjustmentPurple": ("hue_adjustment_purple", float),
    "HueAdjustmentMagenta": ("hue_adjustment_magenta", float),
    # HSL Saturation
    "SaturationAdjustmentRed": ("saturation_adjustment_red", float),
    "SaturationAdjustmentOrange": ("saturation_adjustment_orange", float),
    "SaturationAdjustmentYellow": ("saturation_adjustment_yellow", float),
    "SaturationAdjustmentGreen": ("saturation_adjustment_green", float),
    "SaturationAdjustmentAqua": ("saturation_adjustment_aqua", float),
    "SaturationAdjustmentBlue": ("saturation_adjustment_blue", float),
    "SaturationAdjustmentPurple": ("saturation_adjustment_purple", float),
    "SaturationAdjustmentMagenta": ("saturation_adjustment_magenta", float),
    # HSL Luminance
    "LuminanceAdjustmentRed": ("luminance_adjustment_red", float),
    "LuminanceAdjustmentOrange": ("luminance_adjustment_orange", float),
    "LuminanceAdjustmentYellow": ("luminance_adjustment_yellow", float),
    "LuminanceAdjustmentGreen": ("luminance_adjustment_green", float),
    "LuminanceAdjustmentAqua": ("luminance_adjustment_aqua", float),
    "LuminanceAdjustmentBlue": ("luminance_adjustment_blue", float),
    "LuminanceAdjustmentPurple": ("luminance_adjustment_purple", float),
    "LuminanceAdjustmentMagenta": ("luminance_adjustment_magenta", float),
    # Split Toning
    "SplitToningShadowHue": ("split_toning_shadow_hue", float),
    "SplitToningShadowSaturation": ("split_toning_shadow_saturation", float),
    "SplitToningHighlightHue": ("split_toning_highlight_hue", float),
    "SplitToningHighlightSaturation": ("split_toning_highlight_saturation", float),
    "SplitToningBalance": ("split_toning_balance", float),
}

# XMP crs: child element name -> dataclass field name (all are tone curve sequences)
SEQUENCE_PROPERTIES: dict[str, str] = {
    "ToneCurvePV2012": "tone_curve_pv2012",
    "ToneCurvePV2012Red": "tone_curve_pv2012_red",
    "ToneCurvePV2012Green": "tone_curve_pv2012_green",
    "ToneCurvePV2012Blue": "tone_curve_pv2012_blue",
}
