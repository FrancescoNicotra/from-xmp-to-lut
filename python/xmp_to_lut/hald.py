"""HALD identity image generation and reading for LUT calibration.

A HALD image of level L encodes a 3D LUT with L² entries per axis as a
2D image of L³ × L³ pixels.  For example, level 8 produces a 512×512
image representing a 64×64×64 LUT — exactly matching the default LUT
size of this project.

Pixel ordering matches the .cube spec: R changes fastest, then G, then B.
For linear index *i* (left-to-right, top-to-bottom):
    R = i % L²
    G = (i // L²) % L²
    B = i // L⁴

Workflow:
    1. ``save_hald_identity(...)`` → generates a 16-bit PNG identity image
    2. User processes the PNG through Adobe Camera Raw with an XMP preset
    3. ``read_hald_lut(...)`` → reads the processed image back as LUT data
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

LutEntry = tuple[float, float, float]


def _require_numpy():
    try:
        import numpy  # noqa: F401
        return numpy
    except ImportError as exc:
        raise ImportError(
            "Calibration features require numpy. "
            "Install with: pip install 'xmp-to-lut[calibration]'"
        ) from exc


def _require_pillow():
    try:
        from PIL import Image  # noqa: F401
        return Image
    except ImportError as exc:
        raise ImportError(
            "Calibration features require Pillow. "
            "Install with: pip install 'xmp-to-lut[calibration]'"
        ) from exc


def generate_hald_identity(level: int = 8, bit_depth: int = 16):
    """Generate a HALD identity image as a numpy array.

    Args:
        level: HALD level. The LUT will have ``level²`` entries per axis
               and the image will be ``level³ × level³`` pixels.
               Level 8 → 64³ LUT, 512×512 image (recommended).
        bit_depth: 8 or 16. 16-bit is recommended for calibration
                   precision.

    Returns:
        numpy uint8 or uint16 array of shape ``(level³, level³, 3)``.
    """
    np = _require_numpy()

    if level < 2:
        raise ValueError("HALD level must be at least 2")
    if bit_depth not in (8, 16):
        raise ValueError("bit_depth must be 8 or 16")

    lut_size = level * level
    img_size = level ** 3
    total = img_size * img_size

    max_val = (1 << bit_depth) - 1
    dtype = np.uint8 if bit_depth == 8 else np.uint16
    denom = lut_size - 1

    indices = np.arange(total, dtype=np.int64)
    ir = indices % lut_size
    ig = (indices // lut_size) % lut_size
    ib = indices // (lut_size * lut_size)

    r = np.round(ir * max_val / denom).astype(dtype)
    g = np.round(ig * max_val / denom).astype(dtype)
    b = np.round(ib * max_val / denom).astype(dtype)

    return np.stack([r, g, b], axis=-1).reshape(img_size, img_size, 3)


def _write_png_16bit(arr, output_path: str) -> None:
    """Write a 16-bit RGB PNG using raw PNG encoding (no Pillow needed).

    Pillow's 16-bit multi-channel support is unreliable across versions,
    so we write the PNG manually using zlib for the DEFLATE compression.
    """
    h, w, _ = arr.shape
    np = _require_numpy()
    arr = arr.astype(np.uint16)

    # PNG signature
    signature = b"\x89PNG\r\n\x1a\n"

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    # IHDR: width, height, bit_depth=16, color_type=2 (RGB)
    ihdr_data = struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # IDAT: pixel data with filter byte (0 = None) per row
    raw_rows = bytearray()
    for y in range(h):
        raw_rows.append(0)  # filter: None
        for x in range(w):
            # Big-endian 16-bit per channel
            raw_rows.extend(struct.pack(">HHH", int(arr[y, x, 0]),
                                        int(arr[y, x, 1]),
                                        int(arr[y, x, 2])))
    compressed = zlib.compress(bytes(raw_rows), 9)
    idat = _chunk(b"IDAT", compressed)

    iend = _chunk(b"IEND", b"")

    with open(output_path, "wb") as f:
        f.write(signature + ihdr + idat + iend)


def save_hald_identity(
    output_path: str | Path,
    level: int = 8,
    bit_depth: int = 16,
) -> None:
    """Generate and save a HALD identity image as PNG.

    Args:
        output_path: Destination file path (.png).
        level: HALD level (default 8 → 512×512 for 64³ LUT).
        bit_depth: 8 or 16 (default 16 for calibration precision).
    """
    arr = generate_hald_identity(level, bit_depth)

    if bit_depth == 16:
        _write_png_16bit(arr, str(output_path))
    else:
        Image = _require_pillow()
        img = Image.fromarray(arr, mode="RGB")
        img.save(str(output_path), format="PNG")


def read_hald_lut(
    image_path: str | Path,
    level: int = 8,
) -> list[LutEntry]:
    """Read a processed HALD image and extract LUT entries.

    The returned list has ``level⁶`` entries (= lut_size³) in .cube
    ordering (R changes fastest, then G, then B).

    Args:
        image_path: Path to the processed HALD PNG/TIFF.
        level: HALD level used when generating the identity image.

    Returns:
        List of (r, g, b) tuples with values normalized to [0.0, 1.0].
    """
    np = _require_numpy()
    Image = _require_pillow()

    img = Image.open(str(image_path))
    arr = np.array(img, dtype=np.float64)

    img_size = level ** 3
    if arr.shape[0] != img_size or arr.shape[1] != img_size:
        raise ValueError(
            f"Expected {img_size}×{img_size} image for HALD level {level}, "
            f"got {arr.shape[1]}×{arr.shape[0]}"
        )

    # Ensure 3 channels (strip alpha if present)
    if arr.ndim == 3 and arr.shape[2] == 4:
        arr = arr[:, :, :3]
    elif arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)

    # Determine max value from original image dtype/mode
    orig_arr = np.array(img)
    if orig_arr.dtype == np.uint16:
        max_val = 65535.0
    elif orig_arr.dtype == np.uint8:
        max_val = 255.0
    else:
        max_val = float(orig_arr.max()) if orig_arr.max() > 0 else 1.0

    flat = arr.reshape(-1, 3) / max_val

    return [(float(row[0]), float(row[1]), float(row[2])) for row in flat]


def hald_level_for_lut_size(lut_size: int) -> int:
    """Return the HALD level needed for a given LUT grid size.

    The HALD level L satisfies ``L² = lut_size``, so ``lut_size``
    must be a perfect square.
    """
    import math
    level = int(math.isqrt(lut_size))
    if level * level != lut_size:
        raise ValueError(
            f"LUT size {lut_size} is not a perfect square; "
            f"cannot determine HALD level"
        )
    return level
