"""Genera SourceAssets/ExtractorSilicio/pantalla_glifos.png: texto ilegible de terminal.

Glifos inventados de 5x7 en renglones de largo variable, con una barra de estado arriba.
Blanco sobre negro (el color lo pone el material). Se repite en vertical para el desplazamiento.
python Scripts/make_screen_glyphs.py
"""
import random
import struct
import zlib
from pathlib import Path

SIZE = 512
CELL_W, CELL_H, SCALE = 6, 10, 2  # celda de glifo en pixeles de textura (x SCALE)
random.seed(7)
img = [[0] * SIZE for _ in range(SIZE)]


def put(x, y, v):
    for dy in range(SCALE):
        for dx in range(SCALE):
            px, py = x * SCALE + dx, y * SCALE + dy
            if 0 <= px < SIZE and 0 <= py < SIZE:
                img[py][px] = max(img[py][px], v)


glyphs = []
for _ in range(48):
    g = [[random.random() < 0.42 for _ in range(5)] for _ in range(7)]
    g[random.randrange(7)] = [True] * 5 if random.random() < 0.3 else g[0]
    glyphs.append(g)

cols, rows = SIZE // (CELL_W * SCALE), SIZE // (CELL_H * SCALE)
for row in range(rows):
    if row == 0:  # barra de estado llena
        for x in range(SIZE // SCALE):
            for y in range(1, 9):
                put(x, y, 150)
        continue
    x, length = 1 + random.randrange(3), random.randint(6, cols - 3)
    bright = 255 if random.random() < 0.25 else 170
    col = 0
    while col < length:
        if random.random() < 0.16 and col > 0:
            col += 1
            continue
        g = random.choice(glyphs)
        for gy in range(7):
            for gx in range(5):
                if g[gy][gx]:
                    put((x + col) * CELL_W + gx, row * CELL_H + gy + 1, bright)
        col += 1

raw = b"".join(b"\x00" + bytes(v for v in r) for r in img)
out = Path(__file__).resolve().parent.parent / "SourceAssets/ExtractorSilicio/pantalla_glifos.png"
chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
out.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
print(out)
