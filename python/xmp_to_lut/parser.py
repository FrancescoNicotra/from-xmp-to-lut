"""XMP sidecar parser for Adobe Camera Raw settings.

Extracts ``crs:`` (Camera Raw Settings) properties from an XMP/XML file
and returns a populated :class:`CrsSettings` dataclass.

Uses :mod:`defusedxml` for safe XML parsing (prevents XXE attacks).
"""

from __future__ import annotations

from pathlib import Path

import defusedxml.ElementTree as ET

from xmp_to_lut.mappings import (
    SCALAR_PROPERTIES,
    SEQUENCE_PROPERTIES,
    SUPPORTED_SCALAR_PROPERTIES,
    SUPPORTED_SEQUENCE_PROPERTIES,
)
from xmp_to_lut.model import CrsSettings, ToneCurvePoint

# XML namespaces used in XMP sidecar files
_NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "crs": "http://ns.adobe.com/camera-raw-settings/1.0/",
}


class XmpParseError(Exception):
    """Raised when the XMP file cannot be parsed or has unexpected structure."""


def parse_xmp(source: str | Path) -> CrsSettings:
    """Parse an XMP sidecar file and return a :class:`CrsSettings` instance.

    Parameters
    ----------
    source:
        Path to the ``.xmp`` file, or a string containing the raw XML.

    Returns
    -------
    CrsSettings
        Populated with values found in the XMP; missing properties keep
        their default values (identity / no adjustment).

    Raises
    ------
    XmpParseError
        If the XML is malformed or the expected RDF structure is missing.
    """
    settings, _warnings = _parse_xmp_details(source)
    return settings


def parse_xmp_with_warnings(source: str | Path) -> tuple[CrsSettings, list[str]]:
    """Parse an XMP sidecar file and return settings plus warning strings."""
    return _parse_xmp_details(source)


def _parse_xmp_details(source: str | Path) -> tuple[CrsSettings, list[str]]:
    xml_string = _read_source(source)

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as exc:
        raise XmpParseError(f"Malformed XML: {exc}") from exc

    description = _find_description(root)
    if description is None:
        raise XmpParseError(
            "No rdf:Description element found in the XMP file. "
            "Expected an XMP structure with x:xmpmeta > rdf:RDF > rdf:Description."
        )

    settings = CrsSettings()
    _extract_scalar_attributes(description, settings)
    _extract_sequence_elements(description, settings)
    warnings = _collect_warnings(description)
    return settings, warnings


def _read_source(source: str | Path) -> str:
    """Return XML string from a file path or raw string."""
    path = Path(source) if not isinstance(source, Path) else source
    if path.exists():
        return path.read_text(encoding="utf-8")
    if isinstance(source, str) and source.lstrip().startswith("<"):
        return source
    raise XmpParseError(
        f"Source is neither an existing file path nor valid XML string: {source!r}"
    )


def _find_description(root: ET.Element) -> ET.Element | None:
    """Locate the first rdf:Description element that carries crs: attributes.

    Handles two common XMP layouts:
    1. ``x:xmpmeta / rdf:RDF / rdf:Description``
    2. ``rdf:RDF / rdf:Description`` (no xmpmeta wrapper)
    """
    crs_ns = _NS["crs"]

    # Try standard path: x:xmpmeta > rdf:RDF > rdf:Description
    for desc in root.iter(f'{{{_NS["rdf"]}}}Description'):
        if _has_crs_content(desc, crs_ns):
            return desc

    return None


def _has_crs_content(element: ET.Element, crs_ns: str) -> bool:
    """Check whether an element has any crs:-namespaced attributes or children."""
    for attr_name in element.attrib:
        if attr_name.startswith(f"{{{crs_ns}}}"):
            return True
    for child in element:
        if child.tag.startswith(f"{{{crs_ns}}}"):
            return True
    return False


def _extract_scalar_attributes(
    description: ET.Element, settings: CrsSettings
) -> None:
    """Read crs: attributes from the rdf:Description element."""
    crs_ns = _NS["crs"]

    for xmp_name, (field_name, coerce) in SCALAR_PROPERTIES.items():
        qualified = f"{{{crs_ns}}}{xmp_name}"
        raw_value = description.get(qualified)
        if raw_value is not None:
            try:
                setattr(settings, field_name, coerce(raw_value))
            except (ValueError, TypeError) as exc:
                raise XmpParseError(
                    f"Cannot convert crs:{xmp_name}={raw_value!r} "
                    f"to {coerce.__name__}: {exc}"
                ) from exc


def _extract_sequence_elements(
    description: ET.Element, settings: CrsSettings
) -> None:
    """Read crs: tone curve sequences from child elements."""
    crs_ns = _NS["crs"]
    rdf_ns = _NS["rdf"]

    for xmp_name, field_name in SEQUENCE_PROPERTIES.items():
        qualified_tag = f"{{{crs_ns}}}{xmp_name}"
        curve_element = description.find(qualified_tag)
        if curve_element is None:
            continue

        seq = curve_element.find(f"{{{rdf_ns}}}Seq")
        if seq is None:
            continue

        points: list[ToneCurvePoint] = []
        for li in seq.findall(f"{{{rdf_ns}}}li"):
            text = (li.text or "").strip()
            if not text:
                continue
            point = _parse_curve_point(text, xmp_name)
            points.append(point)

        if points:
            setattr(settings, field_name, points)


def _parse_curve_point(text: str, context_name: str) -> ToneCurvePoint:
    """Parse a ``"x, y"`` string into a :class:`ToneCurvePoint`."""
    parts = text.split(",")
    if len(parts) != 2:
        raise XmpParseError(
            f"Invalid tone curve point in crs:{context_name}: {text!r}. "
            f"Expected format 'x, y'."
        )
    try:
        x = float(parts[0].strip())
        y = float(parts[1].strip())
    except ValueError as exc:
        raise XmpParseError(
            f"Non-numeric tone curve point in crs:{context_name}: {text!r}"
        ) from exc
    return ToneCurvePoint(x, y)


def _collect_warnings(description: ET.Element) -> list[str]:
    """Return warnings for unsupported crs: properties in the description."""
    crs_ns = _NS["crs"]

    unknown_attrs: list[str] = []
    for attr_name in description.attrib:
        if not attr_name.startswith(f"{{{crs_ns}}}"):
            continue
        local_name = attr_name.split("}", 1)[1]
        if local_name not in SUPPORTED_SCALAR_PROPERTIES:
            unknown_attrs.append(local_name)

    unknown_elements: list[str] = []
    for child in description:
        if not child.tag.startswith(f"{{{crs_ns}}}"):
            continue
        local_name = child.tag.split("}", 1)[1]
        if local_name not in SUPPORTED_SEQUENCE_PROPERTIES:
            unknown_elements.append(local_name)

    warnings: list[str] = []
    if unknown_attrs:
        warnings.append(
            "Unsupported crs: attributes: " + ", ".join(sorted(unknown_attrs))
        )
    if unknown_elements:
        warnings.append(
            "Unsupported crs: elements: " + ", ".join(sorted(unknown_elements))
        )
    return warnings
