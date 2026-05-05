"""Tests for the XMP parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from xmp_to_lut.model import CrsSettings, ToneCurvePoint
from xmp_to_lut.parser import XmpParseError, parse_xmp

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_XMP = FIXTURES / "sample_preset.xmp"


# ---------------------------------------------------------------------------
# Happy-path: parse sample fixture
# ---------------------------------------------------------------------------


class TestParseFixture:
    """Parse the sample_preset.xmp fixture and verify all extracted values."""

    @pytest.fixture(autouse=True)
    def parsed(self) -> None:
        self.settings = parse_xmp(SAMPLE_XMP)

    def test_returns_crs_settings(self) -> None:
        assert isinstance(self.settings, CrsSettings)

    def test_process_version(self) -> None:
        assert self.settings.process_version == "11.0"

    # -- White Balance --

    def test_temperature(self) -> None:
        assert self.settings.temperature == 5500.0

    def test_tint(self) -> None:
        assert self.settings.tint == 10.0

    # -- Basic Adjustments --

    def test_exposure(self) -> None:
        assert self.settings.exposure_2012 == 0.50

    def test_contrast(self) -> None:
        assert self.settings.contrast_2012 == 25.0

    def test_highlights(self) -> None:
        assert self.settings.highlights_2012 == -30.0

    def test_shadows(self) -> None:
        assert self.settings.shadows_2012 == 40.0

    def test_whites(self) -> None:
        assert self.settings.whites_2012 == 15.0

    def test_blacks(self) -> None:
        assert self.settings.blacks_2012 == -10.0

    def test_clarity(self) -> None:
        assert self.settings.clarity_2012 == 20.0

    # -- Color --

    def test_saturation(self) -> None:
        assert self.settings.saturation == 5.0

    def test_vibrance(self) -> None:
        assert self.settings.vibrance == 15.0

    # -- HSL Hue --

    def test_hue_adjustment_red(self) -> None:
        assert self.settings.hue_adjustment_red == 10.0

    def test_hue_adjustment_orange(self) -> None:
        assert self.settings.hue_adjustment_orange == 5.0

    def test_hue_adjustment_green(self) -> None:
        assert self.settings.hue_adjustment_green == -5.0

    def test_hue_adjustment_blue(self) -> None:
        assert self.settings.hue_adjustment_blue == 8.0

    def test_hue_adjustment_magenta(self) -> None:
        assert self.settings.hue_adjustment_magenta == -3.0

    # -- HSL Saturation --

    def test_saturation_adjustment_red(self) -> None:
        assert self.settings.saturation_adjustment_red == 12.0

    def test_saturation_adjustment_green(self) -> None:
        assert self.settings.saturation_adjustment_green == -10.0

    def test_saturation_adjustment_blue(self) -> None:
        assert self.settings.saturation_adjustment_blue == 15.0

    # -- HSL Luminance --

    def test_luminance_adjustment_orange(self) -> None:
        assert self.settings.luminance_adjustment_orange == 10.0

    def test_luminance_adjustment_aqua(self) -> None:
        assert self.settings.luminance_adjustment_aqua == -5.0

    def test_luminance_adjustment_blue(self) -> None:
        assert self.settings.luminance_adjustment_blue == -10.0

    # -- Split Toning --

    def test_split_toning_shadow_hue(self) -> None:
        assert self.settings.split_toning_shadow_hue == 220.0

    def test_split_toning_shadow_saturation(self) -> None:
        assert self.settings.split_toning_shadow_saturation == 15.0

    def test_split_toning_highlight_hue(self) -> None:
        assert self.settings.split_toning_highlight_hue == 40.0

    def test_split_toning_highlight_saturation(self) -> None:
        assert self.settings.split_toning_highlight_saturation == 25.0

    def test_split_toning_balance(self) -> None:
        assert self.settings.split_toning_balance == -20.0

    # -- Tone Curves --

    def test_composite_curve_length(self) -> None:
        assert len(self.settings.tone_curve_pv2012) == 5

    def test_composite_curve_first_point(self) -> None:
        p = self.settings.tone_curve_pv2012[0]
        assert (p.x, p.y) == (0.0, 0.0)

    def test_composite_curve_midpoint(self) -> None:
        p = self.settings.tone_curve_pv2012[2]
        assert (p.x, p.y) == (128.0, 135.0)

    def test_composite_curve_last_point(self) -> None:
        p = self.settings.tone_curve_pv2012[-1]
        assert (p.x, p.y) == (255.0, 255.0)

    def test_red_curve_is_linear(self) -> None:
        curve = self.settings.tone_curve_pv2012_red
        assert len(curve) == 2
        assert (curve[0].x, curve[0].y) == (0.0, 0.0)
        assert (curve[1].x, curve[1].y) == (255.0, 255.0)

    def test_blue_curve_offset(self) -> None:
        curve = self.settings.tone_curve_pv2012_blue
        assert len(curve) == 2
        assert (curve[0].x, curve[0].y) == (0.0, 5.0)
        assert (curve[1].x, curve[1].y) == (255.0, 250.0)


# ---------------------------------------------------------------------------
# Parsing from raw XML string
# ---------------------------------------------------------------------------


class TestParseFromString:
    def test_minimal_xmp_string(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
              xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
              crs:Exposure2012="-1.25"
              crs:Saturation="+50" />
          </rdf:RDF>
        </x:xmpmeta>
        """
        settings = parse_xmp(xml)
        assert settings.exposure_2012 == -1.25
        assert settings.saturation == 50.0

    def test_missing_properties_keep_defaults(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
              xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
              crs:Exposure2012="+1.00" />
          </rdf:RDF>
        </x:xmpmeta>
        """
        settings = parse_xmp(xml)
        assert settings.exposure_2012 == 1.0
        # Everything else stays at default
        assert settings.contrast_2012 == 0.0
        assert settings.temperature == 6500.0
        assert settings.saturation == 0.0
        assert len(settings.tone_curve_pv2012) == 2  # default linear


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_malformed_xml(self) -> None:
        with pytest.raises(XmpParseError, match="Malformed XML"):
            parse_xmp("<not valid xml")

    def test_missing_rdf_description(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
          </rdf:RDF>
        </x:xmpmeta>
        """
        with pytest.raises(XmpParseError, match="No rdf:Description"):
            parse_xmp(xml)

    def test_no_crs_namespace(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
              xmlns:dc="http://purl.org/dc/elements/1.1/"
              dc:title="No CRS here" />
          </rdf:RDF>
        </x:xmpmeta>
        """
        with pytest.raises(XmpParseError, match="No rdf:Description"):
            parse_xmp(xml)

    def test_invalid_numeric_value(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
              xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
              crs:Exposure2012="not_a_number" />
          </rdf:RDF>
        </x:xmpmeta>
        """
        with pytest.raises(XmpParseError, match="Cannot convert"):
            parse_xmp(xml)

    def test_invalid_curve_point(self) -> None:
        xml = """
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about=""
              xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/">
              <crs:ToneCurvePV2012>
                <rdf:Seq>
                  <rdf:li>bad_point</rdf:li>
                </rdf:Seq>
              </crs:ToneCurvePV2012>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
        """
        with pytest.raises(XmpParseError, match="Invalid tone curve point"):
            parse_xmp(xml)

    def test_nonexistent_file(self) -> None:
        with pytest.raises(XmpParseError, match="neither an existing file"):
            parse_xmp("/nonexistent/path/to/file.xmp")
