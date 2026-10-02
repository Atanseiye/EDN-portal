"""Guard against partial PNGs that browsers render as a clipped logo."""

import hashlib
import struct
import unittest
import zlib
from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "web"


class BrandAssetTests(unittest.TestCase):
    def test_logo_is_the_exact_uploaded_file(self):
        # ChatGPT Image Oct 2, 2026, 12_35_23 AM.png; no image transformation.
        self.assertEqual(
            hashlib.sha256((WEB / "ednai-logo.png").read_bytes()).hexdigest(),
            "469da548bc4bfd9de811a2e562f87f5136b5e28f2310a83c182c15a484cc76a6",
        )

    def test_png_contains_every_scanline_and_valid_checksums(self):
        data = (WEB / "ednai-logo.png").read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        offset, compressed, ended = 8, bytearray(), False
        while offset < len(data):
            length = struct.unpack_from(">I", data, offset)[0]
            tag = data[offset + 4 : offset + 8]
            payload = data[offset + 8 : offset + 8 + length]
            checksum = struct.unpack_from(">I", data, offset + 8 + length)[0]
            self.assertEqual(zlib.crc32(tag + payload), checksum, tag)
            if tag == b"IHDR":
                self.assertEqual(struct.unpack(">IIBBBBB", payload), (2048, 682, 8, 6, 0, 0, 0))
            elif tag == b"IDAT":
                compressed.extend(payload)
            elif tag == b"IEND":
                ended = True
            offset += length + 12
        self.assertTrue(ended)
        self.assertEqual(offset, len(data))
        decoder = zlib.decompressobj()
        scanlines = decoder.decompress(compressed) + decoder.flush()
        self.assertTrue(decoder.eof)
        self.assertEqual(len(scanlines), 682 * (2048 * 4 + 1))

    def test_every_public_header_uses_the_same_versioned_asset(self):
        for name in ("index", "developer", "challenge", "guide", "guide-en", "guide-yo", "guide-ha", "guide-ig"):
            with self.subTest(page=name):
                html = (WEB / f"{name}.html").read_text()
                self.assertIn('src="/assets/ednai-logo.png?v=20261002-original" alt="EDNAi" width="2048" height="682"', html)


if __name__ == "__main__":
    unittest.main()
