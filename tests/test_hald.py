"""Tests for HALD identity image generation and reading."""

import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from xmp_to_lut.hald import (
    generate_hald_identity,
    hald_level_for_lut_size,
    read_hald_lut,
    save_hald_identity,
)


class TestGenerateHaldIdentity:
    def test_shape_level_2(self):
        arr = generate_hald_identity(level=2, bit_depth=8)
        # level 2: LUT 4×4×4, image 8×8
        assert arr.shape == (8, 8, 3)
        assert arr.dtype == np.uint8

    def test_shape_level_4(self):
        arr = generate_hald_identity(level=4, bit_depth=8)
        # level 4: LUT 16×16×16, image 64×64
        assert arr.shape == (64, 64, 3)

    def test_shape_level_8_16bit(self):
        arr = generate_hald_identity(level=8, bit_depth=16)
        # level 8: LUT 64×64×64, image 512×512
        assert arr.shape == (512, 512, 3)
        assert arr.dtype == np.uint16

    def test_first_pixel_is_black(self):
        arr = generate_hald_identity(level=4, bit_depth=8)
        np.testing.assert_array_equal(arr[0, 0], [0, 0, 0])

    def test_last_pixel_is_white(self):
        arr = generate_hald_identity(level=4, bit_depth=8)
        np.testing.assert_array_equal(arr[-1, -1], [255, 255, 255])

    def test_last_pixel_is_white_16bit(self):
        arr = generate_hald_identity(level=4, bit_depth=16)
        np.testing.assert_array_equal(arr[-1, -1], [65535, 65535, 65535])

    def test_r_changes_fastest(self):
        """First row of pixels should sweep R while G=0, B=0."""
        arr = generate_hald_identity(level=2, bit_depth=8)
        # level 2: LUT size=4, img=8×8
        # First 4 pixels: R=0,1,2,3 (mapped to 0..255), G=0, B=0
        flat = arr.reshape(-1, 3)
        for i in range(4):
            expected_r = round(i * 255 / 3)
            assert flat[i, 0] == expected_r, f"pixel {i}: R={flat[i, 0]}, expected {expected_r}"
            assert flat[i, 1] == 0
            assert flat[i, 2] == 0

    def test_total_unique_colors(self):
        arr = generate_hald_identity(level=2, bit_depth=8)
        flat = arr.reshape(-1, 3)
        unique = set(map(tuple, flat.tolist()))
        # 4^3 = 64 unique colors
        assert len(unique) == 64

    def test_invalid_level(self):
        with pytest.raises(ValueError, match="at least 2"):
            generate_hald_identity(level=1)

    def test_invalid_bit_depth(self):
        with pytest.raises(ValueError, match="bit_depth"):
            generate_hald_identity(level=4, bit_depth=12)


class TestSaveAndReadHald:
    def test_roundtrip_8bit(self):
        """Save an 8-bit HALD and read it back: values should match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "hald.png"
            save_hald_identity(path, level=2, bit_depth=8)
            assert path.exists()

            entries = read_hald_lut(path, level=2)
            assert len(entries) == 64  # 4^3

            # First entry should be black
            assert entries[0] == pytest.approx((0.0, 0.0, 0.0), abs=1e-3)
            # Last entry should be white
            assert entries[-1] == pytest.approx((1.0, 1.0, 1.0), abs=1e-3)

    def test_roundtrip_16bit(self):
        """Save a 16-bit HALD and read it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "hald16.png"
            save_hald_identity(path, level=2, bit_depth=16)
            assert path.exists()
            assert path.stat().st_size > 0

    def test_wrong_dimensions_raises(self):
        """Reading a non-HALD image with wrong dimensions should raise."""
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wrong.png"
            img = Image.new("RGB", (100, 100), color=(128, 128, 128))
            img.save(path)

            with pytest.raises(ValueError, match="Expected"):
                read_hald_lut(path, level=4)


class TestHaldLevelForLutSize:
    def test_level_8(self):
        assert hald_level_for_lut_size(64) == 8

    def test_level_4(self):
        assert hald_level_for_lut_size(16) == 4

    def test_non_square_raises(self):
        with pytest.raises(ValueError, match="not a perfect square"):
            hald_level_for_lut_size(33)
