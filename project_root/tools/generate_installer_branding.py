"""Reproducible high-DPI wizard artwork from the existing original SORTH mark.

No external images, fonts or dependencies; text remains native/localizable Inno UI.
Run from project_root: python -m tools.generate_installer_branding
"""
import argparse
import struct
import zlib
from pathlib import Path

from tools.generate_demo_assets import RECTS, icon_png

ROOT = Path(__file__).resolve().parents[1]


def wizard_png():
    # Exact Inno welcome/completion aspect ratio, at 4x classic logical size.
    width, height = 656, 1256
    mark_size, left, top = 448, 104, 160
    pixels = bytearray()
    for row in range(height):
        pixels.append(0)
        for col in range(width):
            color = '#183153'
            x, y = (col - left + .5) * 64 / mark_size, (row - top + .5) * 64 / mark_size
            for rx, ry, rw, rh, fill in RECTS:
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    color = fill
            pixels.extend(bytes.fromhex(color[1:]) + b'\xff')

    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data)))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(pixels), 9)) + chunk(b'IEND', b''))


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'wizard.png').write_bytes(wizard_png())
    (output / 'mark.png').write_bytes(icon_png(256))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'installer/branding')
    generate(parser.parse_args().output)
